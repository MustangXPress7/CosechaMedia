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


def create_folder_structure(project_root: str, camera_name: str, shoot_date: str, 
                          order_type: str = "camera_first", folder_name: str = "Footage"):
    base_path = os.path.join(project_root, folder_name)
    
    if order_type == "camera_first":
        if shoot_date:
            path = os.path.join(base_path, camera_name, shoot_date)
        else:
            path = os.path.join(base_path, camera_name)
    elif order_type == "date_first":
        if shoot_date:
            path = os.path.join(base_path, shoot_date, camera_name)
        else:
            path = os.path.join(base_path, camera_name)
    elif order_type == "camera_only":
        path = os.path.join(base_path, camera_name)
    elif order_type == "flat":
        path = base_path
    else:
        if shoot_date:
            path = os.path.join(base_path, camera_name, shoot_date)
        else:
            path = os.path.join(base_path, camera_name)
        
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

def get_mounted_drives():
    if sys.platform == "win32":
        import string
        from ctypes import windll
        
        drives = []
        bitmask = windll.kernel32.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                drive_path = f"{letter}:\\"
                try:
                    drive_type = windll.kernel32.GetDriveTypeW(drive_path)
                    if drive_type == 2:
                        drives.append({
                            "path": drive_path,
                            "type": "removable",
                            "label": get_drive_label(drive_path)
                        })
                except:
                    pass
            bitmask >>= 1
        return drives
    else:
        return []

def get_drive_label(drive_path: str) -> str:
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        buffer = ctypes.create_unicode_buffer(256)
        kernel32.GetVolumeInformationW(drive_path, buffer, 256, None, None, None, None, 0)
        return buffer.value
    except:
        return ""

def is_removable_drive(path: str) -> bool:
    """Devuelve True si la ruta apunta a una unidad extraíble (DRIVE_REMOVABLE)."""
    if sys.platform != "win32":
        return False
    if len(path) >= 2 and path[1] == ":":
        drive = path[:2] + "\\"
    else:
        drive = os.path.splitdrive(path)[0] + "\\"
    try:
        import ctypes
        return ctypes.windll.kernel32.GetDriveTypeW(drive) == 2
    except:
        return False
