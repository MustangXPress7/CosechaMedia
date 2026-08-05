"""Acceso a dispositivos por red (FTP) para ingesta por WiFi.

Backend que implementa la misma interfaz de sesión que WPD en ``app.core.mtp``
(``storages()``, ``_resolve()``, ``_enum_children()`` y ``download()``) para
reutilizar todo el staging incremental: manifest ``.sync_manifest.json``,
caché local por hash de ``device_id`` y auto-sync.

La identidad de un dispositivo FTP es ``ftp:<id_perfil>``, clave estable de la
tabla ``ftp_profiles``. La caché local se guarda igual que con MTP en
``data/device_cache/<sha1(device_id)>/<carpeta>``.

Requisitos del servidor (las apps de servidor FTP de móviles lo cumplen):
- Modo pasivo.
- ``MLSD`` (RFC 3659) cuando esté disponible; si no, se usa ``NLST`` + ``SIZE``
  + ``MDTM``.
"""
import ftplib
import os
import socket
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

from app.core.db import db
from app.core.mtp import (
    DeviceInfo,
    MtpBackend,
    MtpError,
    RemoteFile,
    _load_manifest,
    _stage_session,
    device_cache_dir,
)

FTP_PREFIX = "ftp:"


@dataclass
class FtpProfile:
    name: str
    host: str
    port: int = 21
    username: str = ""
    password: str = ""
    base_folder: str = ""
    passive: bool = True
    timeout: int = 15

    @classmethod
    def from_db(cls, row: dict) -> "FtpProfile":
        return cls(
            name=row.get("name") or "",
            host=row.get("host") or "",
            port=int(row.get("port") or 21),
            username=row.get("username") or "",
            password=row.get("password") or "",
            base_folder=row.get("base_folder") or "",
            passive=bool(row.get("passive", 1)),
            timeout=int(row.get("timeout") or 15),
        )

    def display_name(self) -> str:
        return self.name or f"{self.username or 'anonimo'}@{self.host}:{self.port}"


def device_key(profile_id: int) -> str:
    """device_id estable para un perfil FTP (usado en sesiones y caché)."""
    return f"{FTP_PREFIX}{int(profile_id)}"


def profile_id_from_device_key(device_id: str) -> Optional[int]:
    if isinstance(device_id, str) and device_id.startswith(FTP_PREFIX):
        try:
            return int(device_id[len(FTP_PREFIX):])
        except (TypeError, ValueError):
            return None
    return None


def _utc_to_local(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone().replace(tzinfo=None)


# --------------------------------------------------------------------------
# Descubrimiento en la red local
# --------------------------------------------------------------------------

def local_ip() -> Optional[str]:
    """Dirección IPv4 de la interfaz que sale a Internet (ruta por defecto)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()


def local_subnet_ips() -> List[str]:
    """Las 254 direcciones de la subred /24 local, excluyendo la propia."""
    ip = local_ip()
    if not ip:
        return []
    parts = ip.split(".")
    if len(parts) != 4:
        return []
    return [f"{parts[0]}.{parts[1]}.{parts[2]}.{i}" for i in range(1, 255)]


def probe_ftp_banner(host: str, port: int, timeout: float = 0.5) -> Optional[str]:
    """Abre una conexión TCP y lee el banner del servidor FTP (o None)."""
    try:
        with socket.create_connection((host, int(port)), timeout=timeout) as sock:
            sock.settimeout(timeout)
            banner = sock.recv(256).decode("utf-8", "replace").strip()
        return banner or None
    except OSError:
        return None


def scan_network_ftp(timeout: float = 0.5, ports: tuple = (21, 2221),
                     on_progress: Optional[Callable[[int, int], None]] = None,
                     cancel: Optional[Callable[[], bool]] = None,
                     hosts: Optional[List[str]] = None) -> List[dict]:
    """Busca servidores FTP en la subred local en paralelo.

    Devuelve una lista de dicts ``{"host", "port", "banner"}`` ordenada por
    IP. ``ports``: los puertos a probar por host (el primero que responda
    gana). ``hosts`` permite fijar qué direcciones escanear (pruebas).
    """
    if hosts is None:
        hosts = local_subnet_ips()
    results: List[dict] = []
    if not hosts:
        return results
    lock = threading.Lock()
    total = len(hosts)

    def probe(host: str):
        for port in ports:
            banner = probe_ftp_banner(host, port, timeout)
            if banner:
                with lock:
                    results.append({"host": host, "port": int(port), "banner": banner})
                return

    with ThreadPoolExecutor(max_workers=64) as ex:
        futs = [ex.submit(probe, h) for h in hosts]
        for i, fut in enumerate(futs):
            if cancel and cancel():
                break
            fut.result()
            if on_progress:
                on_progress(i + 1, total)
    results.sort(key=lambda r: (tuple(int(p) for p in r["host"].split(".")), r["port"]))
    return results


class FtpSession:
    """Sesión FTP abierta (context manager). Interfaz compatible con la sesión MTP."""

    def __init__(self, profile: FtpProfile):
        self._profile = profile
        self._base = "/".join(
            p for p in (profile.base_folder or "").replace("\\", "/").split("/") if p
        )
        self._conn: Optional[ftplib.FTP] = None
        self.closed = False
        try:
            conn = ftplib.FTP()
            conn.connect(profile.host, int(profile.port or 21),
                         timeout=int(profile.timeout or 15))
            conn.set_pasv(bool(profile.passive))
            if profile.username:
                conn.login(profile.username, profile.password or "")
            else:
                conn.login()
            self._conn = conn
        except Exception:
            self.close()
            raise

    def close(self):
        self.closed = True
        conn = self._conn
        self._conn = None
        if conn is not None:
            try:
                conn.quit()
            except Exception:
                try:
                    conn.close()
                except Exception:
                    pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    # -- rutas -----------------------------------------------------------

    def _to_remote(self, rel_path: str) -> str:
        """Ruta remota absoluta para una ruta relativa a la carpeta base."""
        parts = [p for p in (rel_path or "").replace("\\", "/").split("/") if p]
        all_parts = ([self._base] if self._base else []) + parts
        return "/" + "/".join(all_parts) if all_parts else "/"

    # -- enumeración -------------------------------------------------------

    def _parse_mtime(self, value) -> Optional[datetime]:
        if not value:
            return None
        try:
            dt = datetime.strptime(str(value).strip()[:14], "%Y%m%d%H%M%S")
        except (TypeError, ValueError):
            return None
        return _utc_to_local(dt)

    def _mlsd(self, remote_path: str) -> List[RemoteFile]:
        conn = self._conn
        if conn is None:
            raise ftplib.error_temp("conexion cerrada")
        out: List[RemoteFile] = []
        for name, facts in conn.mlsd(remote_path, facts=["type", "size", "modify"]):
            if name in (".", ".."):
                continue
            ftype = (facts.get("type") or "").lower()
            is_dir = ftype in ("dir", "pdir", "cdir")
            size = 0
            if not is_dir:
                try:
                    size = int(facts.get("size") or 0)
                except (TypeError, ValueError):
                    size = 0
            out.append(RemoteFile(
                rel_path=name,
                name=name,
                size=size,
                date_modified=self._parse_mtime(facts.get("modify")),
                is_dir=is_dir,
                object_id=(remote_path.rstrip("/") + "/" + name) if remote_path != "/" else "/" + name,
            ))
        return out

    def _list_fallback(self, remote_path: str) -> List[RemoteFile]:
        """NLST + SIZE + MDTM (para servidores sin MLSD)."""
        conn = self._conn
        if conn is None:
            raise ftplib.error_temp("conexion cerrada")
        names = conn.nlst(remote_path)
        prefix = remote_path.rstrip("/") + "/" if remote_path != "/" else "/"
        out: List[RemoteFile] = []
        for raw in names:
            if raw in (".", ".."):
                continue
            name = raw[len(prefix):] if raw.startswith(prefix) else raw
            name = name.replace("\\", "/").split("/")[-1]
            if not name:
                continue
            full = (remote_path.rstrip("/") + "/" + name) if remote_path != "/" else "/" + name
            size = 0
            is_dir = False
            try:
                size = int(conn.size(full))
            except Exception:
                is_dir = True
            out.append(RemoteFile(
                rel_path=name,
                name=name,
                size=size,
                date_modified=self._mdtm(full),
                is_dir=is_dir,
                object_id=full,
            ))
        return out

    def _mdtm(self, full_path: str) -> Optional[datetime]:
        try:
            resp = self._conn.sendcmd("MDTM " + full_path)
        except Exception:
            return None
        if resp.startswith("213"):
            return self._parse_mtime(resp[3:].strip())
        return None

    def _list_dir(self, remote_path: str) -> List[RemoteFile]:
        try:
            return self._mlsd(remote_path)
        except (ftplib.error_perm, ftplib.error_temp, OSError):
            return self._list_fallback(remote_path)

    # -- interfaz de sesión MTP -------------------------------------------

    def storages(self) -> List[RemoteFile]:
        return [e for e in self._list_dir(self._to_remote("")) if e.is_dir]

    def _resolve(self, folder_path: str) -> Optional[RemoteFile]:
        parts = [p for p in (folder_path or "").replace("\\", "/").split("/") if p]
        if not parts:
            return None
        if len(parts) == 1:
            candidates = [e for e in self._list_dir(self._to_remote(""))
                          if e.name == parts[0] and e.is_dir]
        else:
            parent = self._resolve("/".join(parts[:-1]))
            if parent is None:
                return None
            candidates = [e for e in self._list_dir(parent.object_id)
                          if e.name == parts[-1] and e.is_dir]
        return candidates[0] if candidates else None

    def _enum_children(self, object_id: str) -> List[RemoteFile]:
        return self._list_dir(object_id)

    def children(self, folder_path: str) -> List[RemoteFile]:
        if not folder_path:
            return self.storages()
        content = self._resolve(folder_path)
        if content is None:
            return []
        return self._list_dir(content.object_id)

    def download(self, remote_file: RemoteFile, dest_path: str) -> None:
        conn = self._conn
        if conn is None:
            raise ftplib.error_temp("conexion cerrada")
        with open(dest_path, "wb") as fh:
            conn.retrbinary("RETR " + remote_file.object_id, fh.write, blocksize=262144)


class FtpBackend(MtpBackend):
    """Backend FTP que sigue la interfaz MtpBackend (staging incremental reutilizado)."""

    def list_devices(self) -> List[DeviceInfo]:
        return [
            DeviceInfo(device_key(p["id"]), p.get("name") or p.get("host") or "")
            for p in db.list_ftp_profiles()
        ]

    def _open_session(self, device_id: str,
                      passive: Optional[bool] = None) -> FtpSession:
        pid = profile_id_from_device_key(device_id)
        if pid is None:
            raise MtpError(f"perfil FTP invalido: {device_id}")
        row = db.get_ftp_profile(pid)
        if row is None:
            raise MtpError(f"perfil FTP no encontrado: {device_id}")
        profile = FtpProfile.from_db(row)
        if passive is not None:
            profile.passive = bool(passive)
        return FtpSession(profile)

    def _flip_passive(self, device_id: str) -> None:
        """Cambia el modo pasivo guardado del perfil (para perseguir el modo
        que sí funciona con ese servidor)."""
        pid = profile_id_from_device_key(device_id)
        if pid is None:
            return
        row = db.get_ftp_profile(pid)
        if row is None:
            return
        db.update_ftp_profile(pid, passive=not bool(row.get("passive", 1)))

    def list_children(self, device_id: str, folder_path: str) -> List[RemoteFile]:
        """Lista los hijos de ``folder_path``. Si la primera conexión falla en
        el modo pasivo configurado (p. ej. ``425 Can't open passive
        connection``), cambia al modo opuesto y reintenta una vez; el perfil
        guardado se actualiza al modo que funciona."""
        last_error: Optional[Exception] = None
        for attempt in range(2):
            try:
                with self._open_session(device_id) as sess:
                    return sess.children(folder_path)
            except (ftplib.error_temp, OSError) as e:
                last_error = e
                if attempt == 0:
                    self._flip_passive(device_id)
                    continue
        raise last_error if last_error is not None else MtpError(
            f"no se pudo leer el dispositivo: {device_id}")

    def is_reachable(self, device_id: str, timeout: float = 3.0) -> bool:
        """Comprueba con una conexión corta si el servidor está disponible,
        probando el modo pasivo configurado y, si falla, el opuesto."""
        pid = profile_id_from_device_key(device_id)
        if pid is None:
            return False
        row = db.get_ftp_profile(pid)
        if row is None:
            return False
        profile = FtpProfile.from_db(row)
        profile.timeout = timeout
        for passive in (bool(profile.passive), not bool(profile.passive)):
            profile.passive = passive
            sess = None
            try:
                sess = FtpSession(profile)
                sess._list_dir(sess._to_remote(""))
                return True
            except Exception:
                continue
            finally:
                if sess is not None:
                    try:
                        sess.close()
                    except Exception:
                        pass
        return False

    def stage(self, device_id: str, device_folder: str,
              on_progress: Optional[Callable[[str, int, int], None]] = None,
              on_error: Optional[Callable[[str], None]] = None,
              cancel: Optional[Callable[[], bool]] = None) -> Dict[str, int]:
        """Staging incremental. Si una descarga o enumeración falla por pérdida
        de conexión, reabre la sesión una vez y reintenta; si vuelve a fallar,
        cambia de modo pasivo/activo y guarda el modo que funciona."""
        cache_dir = device_cache_dir(device_id, device_folder)
        os.makedirs(cache_dir, exist_ok=True)
        manifest = _load_manifest(cache_dir)
        holder = {"sess": self._open_session(device_id),
                  "reopened": False, "flipped": False}

        def _reopen(with_flip: bool = False) -> None:
            if with_flip and not holder["flipped"]:
                holder["flipped"] = True
                self._flip_passive(device_id)
            holder["reopened"] = True
            try:
                holder["sess"].close()
            except Exception:
                pass
            holder["sess"] = self._open_session(device_id)

        def _call(method: str, *args):
            while True:
                try:
                    return getattr(holder["sess"], method)(*args)
                except (ftplib.error_temp, OSError):
                    if not holder["reopened"]:
                        _reopen()
                        continue
                    if not holder["flipped"]:
                        _reopen(with_flip=True)
                        continue
                    raise

        def _download(rf: RemoteFile, dest: str) -> None:
            while True:
                try:
                    holder["sess"].download(rf, dest)
                    return
                except (ftplib.error_temp, OSError):
                    if not holder["reopened"]:
                        _reopen()
                        continue
                    if not holder["flipped"]:
                        _reopen(with_flip=True)
                        continue
                    raise

        proxy = _SessionProxy(_call)
        try:
            return _stage_session(proxy, device_folder, cache_dir, manifest,
                                  _download, on_progress, on_error, cancel)
        finally:
            try:
                holder["sess"].close()
            except Exception:
                pass


class _SessionProxy:
    """Delega las llamadas de enumeración de ``_stage_session`` a la sesión
    FTP vigente (puede reabrirse a mitad de staging)."""

    def __init__(self, call):
        self._call = call

    def _resolve(self, path):
        return self._call("_resolve", path)

    def storages(self):
        return self._call("storages")

    def _enum_children(self, object_id):
        return self._call("_enum_children", object_id)


def stage_device_folder(
    backend: FtpBackend,
    device_id: str,
    device_folder: str,
    on_progress: Optional[Callable[[str, int, int], None]] = None,
    on_error: Optional[Callable[[str], None]] = None,
    cancel: Optional[Callable[[], bool]] = None,
) -> Dict[str, int]:
    """Copia incremental (solo archivos nuevos/cambiados) de la carpeta remota
    a la caché local. Devuelve {"staged", "skipped", "errors"}."""
    return backend.stage(device_id, device_folder, on_progress=on_progress,
                         on_error=on_error, cancel=cancel)
