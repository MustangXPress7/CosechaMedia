import os
import sys
import hashlib
from typing import Optional

def resource_path(relative_path: str) -> str:
    """Resuelve una ruta de asset tanto en desarrollo como empaquetado
    (PyInstaller onefile extrae los datas a sys._MEIPASS)."""
    if getattr(sys, "frozen", False):
        base_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        return os.path.join(base_dir, relative_path)
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), relative_path)


def create_folder_structure(project_root: str, dispositivo_name: str, shoot_date: str, 
                          order_type: str = "camera_first", folder_name: str = "Footage"):
    base_path = os.path.join(project_root, folder_name)
    
    if order_type == "camera_first":
        if shoot_date:
            path = os.path.join(base_path, dispositivo_name, shoot_date)
        else:
            path = os.path.join(base_path, dispositivo_name)
    elif order_type == "date_first":
        if shoot_date:
            path = os.path.join(base_path, shoot_date, dispositivo_name)
        else:
            path = os.path.join(base_path, dispositivo_name)
    elif order_type == "camera_only":
        path = os.path.join(base_path, dispositivo_name)
    elif order_type == "flat":
        path = base_path
    else:
        if shoot_date:
            path = os.path.join(base_path, dispositivo_name, shoot_date)
        else:
            path = os.path.join(base_path, dispositivo_name)
        
    os.makedirs(path, exist_ok=True)
    return path

def calculate_md5(file_path: str, chunk_size: int = 8192) -> str:
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        print(f"Error calculating MD5 for {file_path}: {e}")
        return ""

def _windows_mounted_drives():
    import string
    from ctypes import windll

    drives = []
    bitmask = windll.kernel32.GetLogicalDrives()
    for letter in string.ascii_uppercase:
        if bitmask & 1:
            drive_path = f"{letter}:\\"
            try:
                if is_removable_drive(drive_path):
                    label = get_drive_label(drive_path)
                    if _is_false_positive_drive(label, drive_path):
                        continue
                    drives.append({
                        "path": drive_path,
                        "type": "removable",
                        "label": label
                    })
            except Exception:
                pass
        bitmask >>= 1
    return drives


def _is_false_positive_drive(label, path):
    """Filtra unidades que GetDriveType=REMOVABLE pero son discos fijos.

    Algunos SSD/NVMe reportan DRIVE_REMOVABLE pero son discos del sistema.
    Se descartan si: etiqueta vacía + tiene carpetas de sistema (Windows, Program Files)
    o etiqueta coincide con patrones de sistema conocidos.
    """
    import os
    _SYSTEM_LABELS = {'windows', 'system reserved', 'recovery', 'boot', 'efi system partition'}
    if label and label.lower() in _SYSTEM_LABELS:
        return True
    if not label:
        # Sin etiqueta: verificar si tiene carpetas típicas de sistema
        _SYSTEM_DIRS = {'windows', 'program files', 'program files (x86)', '$recycle.bin'}
        try:
            entries = {e.lower() for e in os.listdir(path)}
            if entries & _SYSTEM_DIRS:
                return True
        except OSError:
            pass
    return False


def _mac_mounted_drives():
    drives = []
    try:
        for name in sorted(os.listdir("/Volumes")):
            path = os.path.join("/Volumes", name)
            if os.path.ismount(path) and not name.startswith("."):
                drives.append({
                    "path": path,
                    "type": "removable",
                    "label": name,
                })
    except OSError:
        pass
    return drives


def _linux_mounted_drives():
    drives = []
    prefixes = ("/media/", "/run/media/", "/mnt/")
    try:
        with open("/proc/mounts", "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                parts = line.split()
                if len(parts) < 2 or not parts[1].startswith(prefixes):
                    continue
                mount = parts[1].replace("\\040", " ")
                path = mount if mount.endswith(os.sep) else mount + os.sep
                drives.append({
                    "path": path,
                    "type": "removable",
                    "label": get_drive_label(path),
                })
    except OSError:
        pass
    return drives


def get_mounted_drives():
    """Unidades extraíbles montadas (Windows: letras; macOS: /Volumes; Linux: /media, /run/media, /mnt)."""
    if sys.platform == "win32":
        return _windows_mounted_drives()
    if sys.platform == "darwin":
        return _mac_mounted_drives()
    return _linux_mounted_drives()

def get_drive_label(drive_path: str) -> str:
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            buffer = ctypes.create_unicode_buffer(256)
            kernel32.GetVolumeInformationW(drive_path, buffer, 256, None, None, None, None, 0)
            return buffer.value
        except Exception:
            return ""
    base = os.path.basename(drive_path.rstrip("\\/"))
    return base if base not in ("", "/") else ""

def is_removable_drive(path: str) -> bool:
    """Devuelve True si la ruta apunta a una unidad extraíble.

    Windows: DRIVE_REMOVABLE (GetDriveTypeW == 2). El flag FILE_REMOVABLE_MEDIA
    NO se exige: muchos lectores de tarjeta y pendrives (p. ej. LUMIX) no lo
    reportan aunque tengan un medio válido, y exigirlo haría que "Detectar"
    ocultara unidades legítimas. El descarte de discos de sistema que reportan
    type 2 por error lo hace `_is_false_positive_drive`. macOS: montada bajo
    /Volumes. Linux: bajo /media, /run/media o /mnt (heurística).
    """
    if sys.platform == "win32":
        if len(path) >= 2 and path[1] == ":":
            drive = path[:2] + "\\"
        else:
            drive = os.path.splitdrive(path)[0] + "\\"
        try:
            import ctypes
            return ctypes.windll.kernel32.GetDriveTypeW(drive) == 2
        except Exception:
            return False
    if not path:
        return False
    norm = path.replace("\\", "/")
    if sys.platform == "darwin":
        return norm == "/Volumes" or norm.startswith("/Volumes/")
    return norm.startswith("/media/") or norm.startswith("/run/media/") or norm.startswith("/mnt/")


def is_true_removable_drive(path: str) -> bool:
    """Removible descartando falsos positivos de disco de sistema.

    Aplica el filtro de `_is_false_positive_drive` (SSD/NVMe que reportan
    GetDriveType=REMOVABLE con etiqueta vacía + carpetas de sistema). Es el
    criterio que usa `get_mounted_drives()` para listar unidades.
    """
    return is_removable_drive(path) and not _is_false_positive_drive(get_drive_label(path), path)
