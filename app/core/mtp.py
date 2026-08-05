"""Acceso a dispositivos MTP (teléfonos, cámaras) en Windows vía Windows Portable Devices (WPD).

Backend desacoplado (``MtpBackend``) para poder testear el staging con un
``FakeBackend`` sin hardware. El backend real (``WpdBackend``) usa comtypes
sobre las typelibs ``portabledeviceapi.dll`` / ``portabledevicetypes.dll``.

Notas de implementación verificadas con dispositivo real:
- Es obligatorio fijar ``WPD_CLIENT_NAME`` al abrir el dispositivo; sin él,
  algunos stacks Android no exponen los storages.
- COM debe inicializarse en el hilo que lo usa: cada operación de primer nivel
  hace ``CoInitialize()`` / ``CoUninitialize()`` pareados.
- Las conexiones MTP pueden quedarse "colgadas" (0x80070081 al leer datos);
  reconectar el cable las restablece. El staging reintenta una vez reabriendo
  el dispositivo.
- Hay que tolerar storages/objetos que fallan al enumerar (p. ej. una SD no
  insertada): se saltan y se reportan por el callback de errores.
"""
import hashlib
import json
import os
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, List, Optional

from app.core.db import db


class MtpError(Exception):
    """Error de acceso al dispositivo MTP."""


@dataclass
class DeviceInfo:
    device_id: str
    name: str
    description: str = ""
    serial: str = ""


@dataclass
class RemoteFile:
    rel_path: str  # ruta relativa (siempre con "/") a la raíz del contenido mostrado
    name: str
    size: int
    date_modified: Optional[datetime]
    is_dir: bool
    object_id: str = ""


# --------------------------------------------------------------------------
# Interfaz del backend
# --------------------------------------------------------------------------

class MtpBackend:
    """Interfaz de acceso a dispositivos MTP.

    Implementar ``list_devices`` y ``_open_session`` (una sesión con
    ``children()``, ``storages()``, ``_resolve()``, ``_enum_children()`` y
    ``download()``). ``walk``/``stage`` se derivan de la sesión.
    """

    def list_devices(self) -> List[DeviceInfo]:
        raise NotImplementedError

    def _open_session(self, device_id: str):
        raise NotImplementedError

    def list_children(self, device_id: str, folder_path: str) -> List[RemoteFile]:
        """Hijos de ``folder_path``. ``''`` = storages raíz."""
        with self._open_session(device_id) as sess:
            return sess.children(folder_path)

    def walk(self, device_id: str, folder_path: str,
             on_error: Optional[Callable[[str], None]] = None) -> List[RemoteFile]:
        """Todos los archivos (no carpetas) bajo ``folder_path``, recursivo."""
        with self._open_session(device_id) as sess:
            content = sess._resolve(folder_path) if folder_path else None
            if folder_path and content is None:
                return []
            return _walk_session(sess, content, folder_path, on_error)

    def download(self, device_id: str, remote_file: RemoteFile, dest_path: str) -> None:
        with self._open_session(device_id) as sess:
            sess.download(remote_file, dest_path)

    def stage(self, device_id: str, device_folder: str,
              on_progress: Optional[Callable[[str, int, int], None]] = None,
              on_error: Optional[Callable[[str], None]] = None,
              cancel: Optional[Callable[[], bool]] = None) -> Dict[str, int]:
        """Staging incremental (walk + descargas) con una única sesión,
        intercalando enumeración y descarga por carpeta."""
        cache_dir = device_cache_dir(device_id, device_folder)
        os.makedirs(cache_dir, exist_ok=True)
        manifest = _load_manifest(cache_dir)
        sess = self._open_session(device_id)
        try:
            return _stage_session(sess, device_folder, cache_dir, manifest,
                                  sess.download, on_progress, on_error, cancel)
        finally:
            try:
                sess.close()
            except Exception:
                pass


# --------------------------------------------------------------------------
# Helpers de caché
# --------------------------------------------------------------------------

def _sanitize_component(name: str) -> str:
    out = []
    for ch in name:
        if ch in '<>:"/\\|?*':
            out.append("_")
        else:
            out.append(ch)
    return "".join(out).strip() or "storage"


def device_cache_root() -> str:
    """Carpeta base de la caché local de dispositivos (data/device_cache)."""
    return os.path.join(os.path.dirname(db.db_path), "device_cache")


def device_cache_dir(device_id: str, device_folder: str) -> str:
    """Carpeta de staging para un (dispositivo, carpeta). Determinista."""
    digest = hashlib.sha1(device_id.encode("utf-8", "replace")).hexdigest()
    components = [_sanitize_component(p) for p in device_folder.split("/") if p]
    folder = os.path.join(*components) if components else ""
    return os.path.join(device_cache_root(), digest, folder)


# --------------------------------------------------------------------------
# Backend real WPD
# --------------------------------------------------------------------------

WPD_OBJECT_NAME_PID = 4
WPD_OBJECT_ORIGINAL_NAME_PID = 12
WPD_OBJECT_CONTENT_TYPE_PID = 7
WPD_OBJECT_SIZE_PID = 11
WPD_OBJECT_DATE_MODIFIED_PID = 19

WPD_OBJECTS_FMTID = "{EF6B490D-5CD8-437A-AFFC-DA8B60EE4A3C}"
WPD_DEVICE_SERIAL_FMTID = "{26D4979A-E643-4626-9E2B-736DC0C92FDC}"
WPD_CLIENT_FMTID = "{204D9F0C-2292-4080-9F42-40664E70F859}"
WPD_RESOURCE_DEFAULT_FMTID = "{E81E79BE-34F0-41BF-B53F-F1A06AE87842}"

GUID_CONTENT_STORAGE = "{23F05BBC-15DE-4C2A-A55B-A9AF5CE412EF}"
GUID_CONTENT_GENERIC_STORAGE = "{99ED0160-17FF-4C44-9D98-1D7A6F941921}"
GUID_CONTENT_DIRECTORY = "{27E2E392-A111-48E0-AB0C-E17705A05F85}"

_load_lock = threading.Lock()
_types_loaded = False


def _ensure_types():
    global _types_loaded
    if _types_loaded:
        return
    with _load_lock:
        if _types_loaded:
            return
        import comtypes.client
        comtypes.client.GetModule("portabledeviceapi.dll")
        comtypes.client.GetModule("portabledevicetypes.dll")
        _types_loaded = True


def _pkey(fmtid: str, pid: int):
    import comtypes
    import comtypes.gen.PortableDeviceApiLib as port
    k = comtypes.pointer(port._tagpropertykey())
    k.contents.fmtid = comtypes.GUID(fmtid)
    k.contents.pid = pid
    return k


class _WpdSession:
    """Sesión abierta a un dispositivo (context manager). COM ya inicializado."""

    def __init__(self, pnp_id: str):
        _ensure_types()
        import ctypes
        import comtypes
        import comtypes.client
        import comtypes.gen.PortableDeviceApiLib as port
        import comtypes.gen.PortableDeviceTypesLib as types
        self._port = port
        self._types = types
        self._ctypes = ctypes
        comtypes.CoInitialize()
        self._com_initialized = True
        try:
            ci = comtypes.client.CreateObject(
                types.PortableDeviceValues,
                clsctx=comtypes.CLSCTX_INPROC_SERVER,
                interface=port.IPortableDeviceValues,
            )
            ci.SetStringValue(_pkey(WPD_CLIENT_FMTID, 2), "CosechaMedia")
            self._device = comtypes.client.CreateObject(
                port.PortableDevice,
                clsctx=comtypes.CLSCTX_INPROC_SERVER,
                interface=port.IPortableDevice,
            )
            self._device.Open(pnp_id, ci)
            self._content = self._device.Content()
            self._properties = self._content.Properties()
            self.name = self._friendly_name(pnp_id)
            self.serial = self._device_serial()
            self.devicename = f"{self.name}_{self.name}_{self.serial}"
        except Exception:
            self.close()
            raise

    def close(self):
        if getattr(self, "_com_initialized", False):
            self._com_initialized = False
            self._device = None
            try:
                self._ctypes.CoUninitialize()
            except Exception:
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    # -- lectura de metadatos --------------------------------------------

    def _friendly_name(self, pnp_id: str) -> str:
        ctypes = self._ctypes
        DM = _manager()
        nlen = ctypes.pointer(ctypes.c_ulong(0))
        DM.GetDeviceFriendlyName(pnp_id, ctypes.POINTER(ctypes.c_ushort)(), nlen)
        buf = ctypes.create_unicode_buffer(nlen.contents.value)
        DM.GetDeviceFriendlyName(pnp_id, ctypes.cast(buf, ctypes.POINTER(ctypes.c_ushort)), nlen)
        return buf.value or pnp_id

    def _device_serial(self) -> str:
        return self._read_prop("DEVICE", WPD_DEVICE_SERIAL_FMTID, 9)

    def _key_collection(self):
        import comtypes.client
        import comtypes.gen.PortableDeviceTypesLib as types
        if getattr(self, "_keys", None) is None:
            keys = comtypes.client.CreateObject(
                types.PortableDeviceKeyCollection,
                clsctx=comtypes.CLSCTX_INPROC_SERVER,
                interface=self._port.IPortableDeviceKeyCollection,
            )
            for fmtid, pid in (
                (WPD_OBJECTS_FMTID, WPD_OBJECT_NAME_PID),
                (WPD_OBJECTS_FMTID, WPD_OBJECT_ORIGINAL_NAME_PID),
                (WPD_OBJECTS_FMTID, WPD_OBJECT_CONTENT_TYPE_PID),
                (WPD_OBJECTS_FMTID, WPD_OBJECT_SIZE_PID),
                (WPD_OBJECTS_FMTID, WPD_OBJECT_DATE_MODIFIED_PID),
                (WPD_DEVICE_SERIAL_FMTID, 9),
            ):
                keys.Add(_pkey(fmtid, pid))
            self._keys = keys
        return self._keys

    def _read_prop(self, object_id: str, fmtid: str, pid: int):
        """Lee una propiedad por getter tipado (GetStringValue/GetGuidValue/...)."""
        key = _pkey(fmtid, pid)
        try:
            values = self._properties.GetValues(object_id, self._key_collection())
        except Exception:
            return None
        try:
            if pid in (WPD_OBJECT_NAME_PID, WPD_OBJECT_ORIGINAL_NAME_PID):
                return values.GetStringValue(key)
            if pid == WPD_OBJECT_CONTENT_TYPE_PID:
                return str(values.GetGuidValue(key))
            if pid == WPD_OBJECT_SIZE_PID:
                return int(values.GetUnsignedLargeIntegerValue(key))
            if pid == WPD_OBJECT_DATE_MODIFIED_PID:
                return _value_to_filetime(values.GetValue(key))
            if fmtid == WPD_DEVICE_SERIAL_FMTID:
                return str(values.GetStringValue(key))
        except Exception:
            return None
        return None

    def _list_object_ids(self, parent_object_id: str) -> List[str]:
        ctypes = self._ctypes
        en = self._content.EnumObjects(
            ctypes.c_ulong(0),
            ctypes.c_wchar_p(parent_object_id),
            ctypes.POINTER(self._port.IPortableDeviceValues)(),
        )
        ids: List[str] = []
        while True:
            num_fetched = ctypes.pointer(ctypes.c_ulong(0))
            arr = en.Next(1, num_fetched)
            if num_fetched.contents.value == 0:
                break
            oid = arr[0]
            if oid is not None:
                ids.append(str(oid))
        return ids

    def _enum_children(self, parent_object_id: str) -> List[RemoteFile]:
        out: List[RemoteFile] = []
        try:
            for oid in self._list_object_ids(parent_object_id):
                name = self._read_prop(oid, WPD_OBJECTS_FMTID, WPD_OBJECT_ORIGINAL_NAME_PID) or \
                    self._read_prop(oid, WPD_OBJECTS_FMTID, WPD_OBJECT_NAME_PID) or oid
                ctype_guid = self._read_prop(oid, WPD_OBJECTS_FMTID, WPD_OBJECT_CONTENT_TYPE_PID)
                ctype = str(ctype_guid) if ctype_guid else ""
                is_dir = ctype.upper() in (
                    GUID_CONTENT_DIRECTORY.upper(),
                    GUID_CONTENT_STORAGE.upper(),
                    GUID_CONTENT_GENERIC_STORAGE.upper(),
                )
                size = 0
                if not is_dir:
                    try:
                        size = int(self._read_prop(oid, WPD_OBJECTS_FMTID, WPD_OBJECT_SIZE_PID) or 0)
                    except (TypeError, ValueError):
                        size = 0
                mtime = self._read_prop(oid, WPD_OBJECTS_FMTID, WPD_OBJECT_DATE_MODIFIED_PID)
                out.append(RemoteFile(
                    rel_path=str(name),
                    name=str(name),
                    size=size,
                    date_modified=_value_to_filetime(mtime),
                    is_dir=is_dir,
                    object_id=oid,
                ))
        except Exception:
            pass
        return out

    # -- recorridos -------------------------------------------------------

    def storages(self) -> List[RemoteFile]:
        return self._enum_children("DEVICE")

    def children(self, folder_path: str) -> List[RemoteFile]:
        if not folder_path:
            return self.storages()
        content = self._resolve(folder_path)
        if content is None:
            return []
        children = self._enum_children(content.object_id)
        prefix = folder_path.rstrip("/")
        for c in children:
            rel = c.rel_path
            if prefix:
                rel = rel.split(prefix + "/", 1)[-1]
            c.rel_path = rel
        return children

    def _resolve(self, folder_path: str) -> Optional[RemoteFile]:
        parts = [p for p in folder_path.split("/") if p]
        if not parts:
            return None
        current: Optional[RemoteFile] = None
        for part in parts:
            if current is None:
                matches = [s for s in self.storages() if s.name == part]
            else:
                matches = [c for c in self._enum_children(current.object_id) if c.name == part]
            if not matches:
                return None
            current = matches[0]
        return current

    def download(self, remote_file: RemoteFile, dest_path: str) -> None:
        import ctypes
        resources = self._content.Transfer()
        stgm = ctypes.c_uint(0)
        size_ptr = ctypes.pointer(ctypes.c_ulong(0))
        size_ptr, q_filestream = resources.GetStream(
            ctypes.c_wchar_p(remote_file.object_id),
            _pkey(WPD_RESOURCE_DEFAULT_FMTID, 0),
            stgm,
            size_ptr,
        )
        blocksize = max(int(size_ptr.contents.value), 1)
        filestream = q_filestream.value
        with open(dest_path, "wb") as fh:
            while True:
                buf, length = filestream.RemoteRead(blocksize)
                if length == 0:
                    break
                fh.write(bytearray(buf[:length]))


def _value_to_filetime(value):
    """Convierte el PROPVARIANT FILETIME de WPD (GetValue) a datetime."""
    if value is None:
        return None
    try:
        import datetime as _dt
        inner = getattr(value, "__MIDL____MIDL_itf_PortableDeviceApi_0001_00000001", None)
        if inner is None:
            return None
        filetime = float(inner.date)
        if not filetime or filetime < 1:
            return None
        filedate = abs(int(filetime))
        days_since_1970 = filedate - (_dt.datetime(1970, 1, 1) - _dt.datetime(1899, 12, 30)).days
        hours = (filetime - int(filetime)) * 24
        minutes = (hours - int(hours)) * 60
        seconds = (minutes - int(minutes)) * 60
        milliseconds = round((seconds - int(seconds)) * 1000)
        return _dt.datetime(1970, 1, 1) + _dt.timedelta(
            days=days_since_1970,
            hours=int(hours),
            minutes=int(minutes),
            seconds=int(seconds),
            milliseconds=milliseconds,
        )
    except Exception:
        return None


def _manager():
    import ctypes
    import comtypes
    import comtypes.client
    import comtypes.gen.PortableDeviceApiLib as port
    _ensure_types()
    global _DEVICE_MANAGER
    if _DEVICE_MANAGER is None:
        _DEVICE_MANAGER = comtypes.client.CreateObject(
            port.PortableDeviceManager,
            clsctx=comtypes.CLSCTX_INPROC_SERVER,
            interface=port.IPortableDeviceManager,
        )
    return _DEVICE_MANAGER


_DEVICE_MANAGER = None


class WpdBackend(MtpBackend):
    """Backend MTP vía Windows Portable Devices."""

    def list_devices(self) -> List[DeviceInfo]:
        import ctypes
        import comtypes
        _ensure_types()
        comtypes.CoInitialize()
        try:
            DM = _manager()
            count = ctypes.pointer(ctypes.c_ulong(0))
            DM.GetDevices(ctypes.POINTER(ctypes.c_wchar_p)(), count)
            if count.contents.value == 0:
                return []
            ids = (ctypes.c_wchar_p * count.contents.value)()
            DM.GetDevices(ctypes.cast(ids, ctypes.POINTER(ctypes.c_wchar_p)), count)
            devices: List[DeviceInfo] = []
            for cur in ids:
                if not cur:
                    continue
                nlen = ctypes.pointer(ctypes.c_ulong(0))
                try:
                    DM.GetDeviceFriendlyName(cur, ctypes.POINTER(ctypes.c_ushort)(), nlen)
                    buf = ctypes.create_unicode_buffer(nlen.contents.value)
                    DM.GetDeviceFriendlyName(cur, ctypes.cast(buf, ctypes.POINTER(ctypes.c_ushort)), nlen)
                    name = buf.value
                except Exception:
                    name = str(cur)
                devices.append(DeviceInfo(device_id=str(cur), name=name or str(cur)))
            return devices
        finally:
            try:
                comtypes.CoUninitialize()
            except Exception:
                pass

    def _open_session(self, device_id: str) -> _WpdSession:
        _ensure_types()
        return _WpdSession(device_id)

    def stage(self, device_id: str, device_folder: str,
              on_progress: Optional[Callable[[str, int, int], None]] = None,
              on_error: Optional[Callable[[str], None]] = None,
              cancel: Optional[Callable[[], bool]] = None) -> Dict[str, int]:
        """Staging con una única sesión WPD, intercalando enumeración y
        descarga por carpeta (enumerar miles de objetos antes de la primera
        transferencia degrada el responder MTP, 0x80070081). Si una descarga
        falla por dispositivo inaccesible, reabre la sesión una vez y reintenta."""
        import comtypes
        cache_dir = device_cache_dir(device_id, device_folder)
        os.makedirs(cache_dir, exist_ok=True)
        manifest = _load_manifest(cache_dir)
        sess = self._open_session(device_id)
        reopened = False

        def _download(rf: RemoteFile, dest: str):
            nonlocal sess, reopened
            try:
                sess.download(rf, dest)
            except comtypes.COMError as e:
                if reopened or getattr(e, "hresult", None) != 0x80070081:
                    raise
                reopened = True
                try:
                    sess.close()
                except Exception:
                    pass
                sess = self._open_session(device_id)
                sess.download(rf, dest)

        try:
            return _stage_session(sess, device_folder, cache_dir, manifest,
                                  _download, on_progress, on_error, cancel)
        finally:
            try:
                sess.close()
            except Exception:
                pass


def _walk_session(sess, root_content, base_path, on_error) -> List[RemoteFile]:
    files: List[RemoteFile] = []
    stack = [root_content] if root_content is not None else sess.storages()
    visited = set()
    prefix = base_path.rstrip("/").replace("\\", "/")
    while stack:
        cur = stack.pop(0)
        if cur is None or cur.object_id in visited:
            continue
        visited.add(cur.object_id)
        try:
            children = sess._enum_children(cur.object_id)
        except Exception as e:
            if on_error:
                on_error(str(e))
            continue
        dirs = []
        for child in children:
            if child.is_dir:
                dirs.append(child)
            else:
                rel = child.rel_path
                files.append(RemoteFile(
                    rel_path=rel,
                    name=child.name,
                    size=child.size,
                    date_modified=child.date_modified,
                    is_dir=False,
                    object_id=child.object_id,
                ))
        stack.extend(dirs)
    norm = []
    for f in files:
        rel = f.rel_path
        if prefix and rel.startswith(prefix):
            rel = rel[len(prefix):].lstrip("/")
        norm.append(RemoteFile(
            rel_path=rel,
            name=f.name,
            size=f.size,
            date_modified=f.date_modified,
            is_dir=False,
            object_id=f.object_id,
        ))
    return norm


# --------------------------------------------------------------------------
# Staging incremental (caché local)
# --------------------------------------------------------------------------

MANIFEST_NAME = ".sync_manifest.json"


def _load_manifest(cache_dir: str) -> Dict[str, dict]:
    path = os.path.join(cache_dir, MANIFEST_NAME)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data.get("files", {})
        except Exception:
            pass
    return {}


def _save_manifest(cache_dir: str, manifest: Dict[str, dict]) -> None:
    path = os.path.join(cache_dir, MANIFEST_NAME)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"files": manifest}, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def _stage_session(sess, device_folder, cache_dir, manifest, download_fn,
                   on_progress, on_error, cancel) -> Dict[str, int]:
    """Recorre el árbol del dispositivo intercalando enumeración y descarga
    por carpeta y actualiza el manifest. ``sess`` debe exponer ``storages()``,
    ``_resolve(path)`` y ``_enum_children(oid)``; ``download_fn(rf, dest)``
    descarga un archivo."""
    result = {"staged": 0, "skipped": 0, "errors": 0, "total": 0}
    queue: List[str] = [device_folder.rstrip("/")] if device_folder else [""]
    base_prefix = device_folder.rstrip("/")
    seen: Dict[str, bool] = {}
    while queue:
        if cancel and cancel():
            break
        path = queue.pop(0)
        content = sess._resolve(path) if path else None
        try:
            children = sess.storages() if content is None else sess._enum_children(content.object_id)
        except Exception as e:
            if on_error:
                on_error(f"{path or '/':s}: {e}")
            continue
        for child in children:
            raw = child.rel_path if not path else path + "/" + child.rel_path
            full = raw[len(base_prefix) + 1:] if base_prefix and raw.startswith(base_prefix + "/") else raw
            seen[full] = True
            if child.is_dir:
                queue.append(raw)
                continue
            result["total"] += 1
            _stage_one(cache_dir, manifest, full, child, download_fn,
                       result, on_progress, on_error)
    for key in list(manifest):
        if key not in seen:
            stale = os.path.join(cache_dir, *[p for p in key.split("/") if p])
            if os.path.exists(stale):
                try:
                    os.remove(stale)
                except OSError:
                    pass
            del manifest[key]
    _save_manifest(cache_dir, manifest)
    return result


def _stage_one(cache_dir, manifest, full, rf, download_fn,
               result, on_progress, on_error) -> None:
    dest = os.path.join(cache_dir, *[p for p in full.split("/") if p])
    prev = manifest.get(full)
    size = int(rf.size or 0)
    mtime = rf.date_modified.strftime("%Y%m%d%H%M%S") if rf.date_modified else ""
    if prev and prev.get("size") == size and prev.get("mtime") == mtime and os.path.exists(dest):
        result["skipped"] += 1
        manifest[full] = {"size": size, "mtime": mtime}
        return
    try:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        tmp = dest + ".part"
        if os.path.exists(tmp):
            os.remove(tmp)
        download_fn(rf, tmp)
        os.replace(tmp, dest)
        manifest[full] = {"size": size, "mtime": mtime}
        result["staged"] += 1
    except Exception as e:
        result["errors"] += 1
        if on_error:
            on_error(f"{full}: {e}")
    if on_progress and result["total"] > 0:
        on_progress(rf.name, result["staged"] + result["skipped"] + result["errors"], result["total"])


def stage_device_folder(
    backend: MtpBackend,
    device_id: str,
    device_folder: str,
    on_progress: Optional[Callable[[str, int, int], None]] = None,
    on_error: Optional[Callable[[str], None]] = None,
    cancel: Optional[Callable[[], bool]] = None,
) -> Dict[str, int]:
    """Copia incremental (solo archivos nuevos/cambiados) de la carpeta del
    dispositivo a la caché local. Devuelve {"staged", "skipped", "errors"}.

    ``device_folder`` es relativo al dispositivo (p. ej. ``"DCIM"`` o
    ``"Almacenamiento interno compartido/DCIM"``).
    """
    return backend.stage(device_id, device_folder, on_progress=on_progress,
                         on_error=on_error, cancel=cancel)
