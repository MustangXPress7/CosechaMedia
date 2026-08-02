"""Actualizaciones automaticas via GitHub Releases.

El updater consulta la API de GitHub (releases/latest), selecciona el asset de
la plataforma actual, lo descarga y verifica su SHA-256 contra el sidecar
`.sha256` publicado en el mismo release, y finalmente sustituye el binario en
uso tras cerrar la app (helper que espera a que salga el proceso y reemplaza).
"""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from typing import Callable, Optional

from PySide6.QtCore import QCoreApplication

from app.core.translator import tr

REPO = "MustangXPress7/CosechaMedia"
API_URL = "https://api.github.com/repos/{0}".format(REPO)
RELEASES_URL = API_URL + "/releases"
HTML_URL = "https://github.com/{0}".format(REPO)

_CHUNK = 1 << 16
_TIMEOUT = 20


class UpdateError(Exception):
    """Error de la logica de actualizaciones."""


def _user_agent() -> str:
    version = QCoreApplication.applicationVersion() or "dev"
    return "CosechaMedia-Updater/{0}".format(version)


def _parse_version(text: str) -> tuple:
    text = text.strip().lstrip("vV")
    nums = []
    for part in text.split("."):
        digits = ""
        for ch in part:
            if ch.isdigit():
                digits += ch
            else:
                break
        if not digits:
            break
        nums.append(int(digits))
    nums = (nums + [0, 0, 0])[:3]
    return tuple(nums)


def compare_versions(a: str, b: str) -> int:
    """Devuelve 1 si a > b, -1 si a < b y 0 si son iguales."""
    va, vb = _parse_version(a), _parse_version(b)
    return (va > vb) - (va < vb)


def _http_json(url: str, timeout: int = _TIMEOUT):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": _user_agent(), "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def latest_release() -> dict:
    return _http_json(RELEASES_URL + "/latest")


def _platform_keywords() -> tuple:
    if sys.platform == "win32":
        return ("windows",)
    if sys.platform == "darwin":
        return ("macos",)
    return ("linux",)


def select_platform_asset(release: dict) -> Optional[dict]:
    """Selecciona el asset del release correspondiente a la plataforma actual."""
    assets = release.get("assets") or []
    keywords = _platform_keywords()
    candidates = [
        a for a in assets if any(k in (a.get("name") or "").lower() for k in keywords)
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda a: a.get("size") or 0, reverse=True)
    return candidates[0]


def check_for_updates() -> dict:
    release = latest_release()
    tag = (release.get("tag_name") or "").strip()
    if not tag:
        raise UpdateError(tr("El repositorio aún no ha publicado versiones."))
    current = QCoreApplication.applicationVersion() or "0.0.0"
    return {
        "release": release,
        "latest_version": tag,
        "current_version": current,
        "update_available": compare_versions(tag, current) > 0,
        "asset": select_platform_asset(release),
        "html_url": release.get("html_url") or HTML_URL,
    }


def download_file(url: str, dest_path: str, progress_cb: Callable = None) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": _user_agent()})
    tmp = dest_path + ".part"
    os.makedirs(os.path.dirname(os.path.abspath(tmp)), exist_ok=True)
    with urllib.request.urlopen(req, timeout=60) as resp:
        total = int(resp.headers.get("Content-Length") or 0)
        done = 0
        with open(tmp, "wb") as f:
            while True:
                chunk = resp.read(_CHUNK)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if progress_cb and total:
                    progress_cb(done, total)
    if progress_cb and not total:
        progress_cb(done, done)
    os.replace(tmp, dest_path)
    return dest_path


def sha256sum(file_path: str) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_sha256(file_path: str, expected: str) -> bool:
    return sha256sum(file_path).lower() == expected.strip().lower()


def fetch_sha256(asset: dict) -> str:
    url = (asset.get("browser_download_url") or "") + ".sha256"
    req = urllib.request.Request(url, headers={"User-Agent": _user_agent()})
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        content = resp.read().decode("utf-8", errors="replace").strip()
    parts = content.split()
    return parts[0] if parts else ""


def verify_download(file_path: str, asset: dict) -> bool:
    try:
        expected = fetch_sha256(asset)
    except Exception:
        raise UpdateError(tr("No se pudo obtener la suma SHA-256 del paquete."))
    if not expected:
        raise UpdateError(tr("No se pudo obtener la suma SHA-256 del paquete."))
    if not verify_sha256(file_path, expected):
        raise UpdateError(tr("La descarga no coincide con la suma SHA-256. Inténtalo de nuevo."))
    return True


def application_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.getcwd()


def download_path_for(asset: dict) -> str:
    if getattr(sys, "frozen", False):
        base = application_dir()
    else:
        base = os.path.join(os.path.expanduser("~"), ".cosechamedia_updates")
        os.makedirs(base, exist_ok=True)
    if sys.platform == "win32":
        return os.path.join(base, "CosechaMedia.new.exe")
    if sys.platform == "darwin":
        return os.path.join(base, "CosechaMedia.new.app.zip")
    return os.path.join(base, "CosechaMedia.new")


def download_asset(asset: dict, dest_path: str, progress_cb: Callable = None) -> str:
    return download_file(asset.get("browser_download_url"), dest_path, progress_cb)


def _mac_app_bundle() -> Optional[str]:
    parts = os.path.abspath(sys.executable).split(os.sep)
    for i, part in enumerate(parts):
        if part.endswith(".app"):
            return os.sep.join(parts[: i + 1])
    return None


def _write_script(app_dir: str, name: str, content: str) -> str:
    path = os.path.join(app_dir, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    if sys.platform != "win32":
        os.chmod(path, 0o755)
    return path


def _spawn_helper(args, cwd):
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
    subprocess.Popen(args, cwd=cwd, shell=False, creationflags=flags)


_WINDOWS_HELPER = """@echo off
set "APP=%~dp0CosechaMedia.exe"
set "NEW=%~dp0CosechaMedia.new.exe"
set "LOG=%~dp0update_log.txt"
:loop
tasklist /FI "IMAGENAME eq CosechaMedia.exe" 2>nul | find /I "CosechaMedia.exe" >nul
if not errorlevel 1 (
    ping 127.0.0.1 -n 2 >nul 2>&1
    goto loop
)
echo [%date% %time%] Replacing %NEW% by %APP% >>"%LOG%" 2>&1
move /Y "%NEW%" "%APP%" >>"%LOG%" 2>&1
if exist "%APP%" start "" "%APP%"
del "%~f0"
"""

_MAC_HELPER = """#!/bin/bash
APP="$1"
NEW="$2"
SCRIPT="$3"
while pgrep -f "CosechaMedia$" >/dev/null 2>&1; do
  sleep 1
done
rm -rf "$APP"
mv "$NEW" "$APP"
open "$APP"
rm -f "$SCRIPT"
"""

_LINUX_HELPER = """#!/bin/bash
APP="$1"
NEW="$2"
SCRIPT="$3"
while pgrep -f "CosechaMedia$" >/dev/null 2>&1; do
  sleep 1
done
chmod +x "$NEW"
mv -f "$NEW" "$APP"
nohup "$APP" >/dev/null 2>&1 &
rm -f "$SCRIPT"
"""


def _install_windows(downloaded: str) -> bool:
    app_dir = application_dir()
    new_exe = os.path.join(app_dir, "CosechaMedia.new.exe")
    if os.path.abspath(downloaded) != os.path.abspath(new_exe):
        os.replace(downloaded, new_exe)
    script = _write_script(app_dir, "update.cmd", _WINDOWS_HELPER)
    _spawn_helper(["cmd", "/c", script], app_dir)
    return True


def _install_linux(downloaded: str) -> bool:
    app_dir = application_dir()
    new_bin = os.path.join(app_dir, "CosechaMedia.new")
    if os.path.abspath(downloaded) != os.path.abspath(new_bin):
        os.replace(downloaded, new_bin)
    os.chmod(new_bin, 0o755)
    script = _write_script(app_dir, "update.sh", _LINUX_HELPER)
    _spawn_helper(["bash", script, os.path.abspath(sys.executable), new_bin, script], app_dir)
    return True


def _extract_app_zip(zip_path: str, dest_dir: str) -> Optional[str]:
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest_dir)
        for name in zf.namelist():
            top = name.split("/", 1)[0]
            if top.endswith(".app"):
                return os.path.join(dest_dir, top)
    return None


def _install_macos(downloaded: str) -> bool:
    current_app = _mac_app_bundle()
    if not current_app:
        raise UpdateError(tr("No se encontró la aplicación CosechaMedia en este sistema."))
    if not os.access(current_app, os.W_OK):
        raise UpdateError(
            tr("La ubicación actual de la aplicación no es escribible. "
               "Mueve CosechaMedia.app a /Applications y vuelve a intentarlo.")
        )
    extract_dir = tempfile.mkdtemp(prefix="cosechamedia_update_")
    new_app = _extract_app_zip(downloaded, extract_dir)
    if not new_app:
        raise UpdateError(tr("El paquete de actualización no contiene una aplicación válida."))
    script = _write_script(extract_dir, "update.sh", _MAC_HELPER)
    _spawn_helper(["bash", script, current_app, new_app, script], extract_dir)
    return True


def install_update(asset: dict, downloaded_path: str) -> bool:
    """Sustituye el binario en uso tras cerrar la app y lo relanza."""
    if not getattr(sys, "frozen", False):
        raise UpdateError(tr("La actualización solo puede instalarse desde la aplicación empaquetada."))
    if sys.platform == "win32":
        return _install_windows(downloaded_path)
    if sys.platform == "darwin":
        return _install_macos(downloaded_path)
    return _install_linux(downloaded_path)
