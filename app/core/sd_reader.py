import os
import json
from typing import Dict, Optional, List
from datetime import datetime

from app.core.metadata_engine import metadata_engine

class SDReader:
    CARD_BRANDS = {
        "SanDisk": ["SD", "SDHC", "SDXC", "SDUC"],
        "Sony": ["SF-G", "SF-M", "SF-E", "SF-D"],
        "Samsung": ["EVO", "PRO", "PRO Plus", "EVO Select"],
        "Kingston": ["Canvas", "Canvas Go!", "Canvas Select"],
        "Lexar": ["Professional", "Gold", "Silver", "Bronze"],
        "Transcend": ["700S", "633U", "300S"],
        "PNY": ["Elite", "ProElite", "XLR8"],
        "Delkin": ["Devices", "Power", "V60", "V90"],
        "ProGrade": ["Cobalt", "Gold", "Silver"],
        "Angelbird": ["AV PRO", "ATOMOS"]
    }
    
    def __init__(self):
        self.card_info = {}
    
    def detect_card_info(self, sd_path: str) -> Dict:
        info = {
            "serial": None,
            "brand": None,
            "model": None,
            "capacity_gb": None,
            "file_system": None,
            "total_space": 0,
            "used_space": 0,
            "free_space": 0,
            "is_valid": False,
            "errors": []
        }
        
        if not os.path.exists(sd_path):
            info["errors"].append("Path does not exist")
            return info
        
        try:
            info["is_valid"] = True
            
            import shutil
            usage = shutil.disk_usage(sd_path)
            info["total_space"] = usage.total
            info["free_space"] = usage.free
            info["used_space"] = usage.used
            info["capacity_gb"] = round(usage.total / (1024**3), 2)
            
            info["file_system"] = self._detect_filesystem(sd_path)
            
            self._detect_brand_from_files(sd_path, info)
            
        except Exception as e:
            info["errors"].append(f"Error detecting card: {str(e)}")
        
        return info
    
    def _detect_filesystem(self, path: str) -> str:
        try:
            if os.name == 'nt':
                import ctypes
                drive = os.path.splitdrive(path)[0] + "\\"
                fs = ctypes.create_string_buffer(256)
                ctypes.windll.kernel32.GetVolumeInformationW(drive, None, 0, None, None, None, fs, 256)
                return fs.value.decode()
            else:
                stat = os.statvfs(path)
                return str(stat.f_fsid)
        except:
            return "Unknown"

    def get_volume_serial(self, path: str):
        """Devuelve el serial del volumen (Windows) o None si no se puede obtener."""
        try:
            if os.name == 'nt':
                import ctypes
                drive = os.path.splitdrive(path)[0] + "\\"
                serial = ctypes.c_ulong()
                ctypes.windll.kernel32.GetVolumeInformationW(
                    drive, None, 0, ctypes.byref(serial), None, None, None, 0
                )
                return f"{serial.value:08x}"
        except Exception:
            pass
        return None
    
    def _detect_brand_from_files(self, sd_path: str, info: Dict):
        private_path = os.path.join(sd_path, "PRIVATE")
        if os.path.exists(private_path):
            try:
                for item in os.listdir(private_path):
                    item_upper = item.upper()
                    if "SAN" in item_upper:
                        info["brand"] = "SanDisk"
                    elif "SONY" in item_upper:
                        info["brand"] = "Sony"
                    elif "SAMSUNG" in item_upper:
                        info["brand"] = "Samsung"
            except:
                pass
        
        info_txt = os.path.join(sd_path, "INFO")
        if os.path.exists(info_txt):
            try:
                with open(info_txt, 'r', errors='ignore') as f:
                    content = f.read(1024)
                    for brand in self.CARD_BRANDS.keys():
                        if brand.lower() in content.lower():
                            info["brand"] = brand
                            break
            except:
                pass
        
        dcim_path = os.path.join(sd_path, "DCIM")
        if not os.path.exists(dcim_path) or info["serial"]:
            return
        
        try:
            folders = sorted([
                d for d in os.listdir(dcim_path) 
                if os.path.isdir(os.path.join(dcim_path, d))
            ])[:3]
        except:
            return
        
        video_exts = ('.mp4', '.mov', '.avi', '.mts', '.m2ts')
        
        for folder in folders:
            folder_path = os.path.join(dcim_path, folder)
            try:
                files = [
                    f for f in os.listdir(folder_path)
                    if f.upper().endswith(video_exts) and os.path.isfile(os.path.join(folder_path, f))
                ][:2]
            except:
                continue
            
            for file in files:
                file_path = os.path.join(folder_path, file)
                self._extract_card_from_video(file_path, info)
                if info["serial"]:
                    return
    
    def _extract_card_from_video(self, file_path: str, info: Dict):
        """Extrae marca/modelo/serie de un clip reutilizando el motor de
        metadatos (que cachea la llamada a ffprobe)."""
        try:
            meta = metadata_engine.get_video_metadata(file_path)
            if not meta:
                return

            if not info["brand"] and meta.get("camera_make"):
                make = str(meta["camera_make"]).upper()
                for brand in self.CARD_BRANDS.keys():
                    if brand.upper() in make:
                        info["brand"] = brand
                        break

            if not info["model"] and meta.get("camera_model"):
                model = str(meta["camera_model"]).strip()
                if model and model.lower() not in ("unknown", "n/a", "none"):
                    info["model"] = model

            if not info["serial"] and meta.get("serial"):
                info["serial"] = str(meta["serial"])
        except Exception:
            pass
    
    def get_card_summary(self, sd_path: str) -> str:
        info = self.detect_card_info(sd_path)
        
        lines = []
        if info["brand"]:
            lines.append(f"Brand: {info['brand']}")
        if info["model"]:
            lines.append(f"Model: {info['model']}")
        if info["serial"]:
            lines.append(f"Serial: {info['serial']}")
        if info["capacity_gb"]:
            lines.append(f"Capacity: {info['capacity_gb']} GB")
        if info["file_system"]:
            lines.append(f"File System: {info['file_system']}")
        
        if info["total_space"] > 0:
            used_pct = (info["used_space"] / info["total_space"]) * 100
            lines.append(f"Used: {used_pct:.1f}%")
        
        return "\n".join(lines) if lines else "No card information detected"

sd_reader = SDReader()
