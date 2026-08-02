import subprocess
import json
import os
from typing import Optional, Dict, List
import sys

from app.core.db import db

VIDEO_EXTENSIONS = ['.mp4', '.mov', '.avi', '.mkv', '.mxf', '.mts', '.m2ts', '.ts', '.mpg', '.mpeg']
AUDIO_EXTENSIONS = ['.wav', '.mp3', '.aac', '.flac', '.ogg', '.m4a']
IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif', '.webp']
RAW_EXTENSIONS = ['.cr2', '.cr3', '.nef', '.arw', '.dng', '.raf', '.orf', '.rw2', '.pef', '.srw']
BUILTIN_EXTENSIONS = set(VIDEO_EXTENSIONS + AUDIO_EXTENSIONS + IMAGE_EXTENSIONS + RAW_EXTENSIONS)

class MetadataEngine:
    _MAX_CACHE = 2000

    def __init__(self):
        self.ffprobe_path = "ffprobe"
        self._setup_ffmpeg_silence()
        self._cache = {}
        self._recognized_extensions = None
    
    def _setup_ffmpeg_silence(self):
        if sys.platform == "win32":
            self.startupinfo = subprocess.STARTUPINFO()
            self.startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            self.startupinfo.wShowWindow = subprocess.SW_HIDE
        else:
            self.startupinfo = None
    
    def get_video_metadata(self, file_path: str) -> Dict:
        try:
            mtime = os.path.getmtime(file_path)
            if file_path in self._cache:
                cached_mtime, cached_meta = self._cache[file_path]
                if cached_mtime == mtime:
                    return cached_meta.copy()
        except OSError:
            pass

        cmd = [
            self.ffprobe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            file_path
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                startupinfo=self.startupinfo,
                timeout=10
            )
            data = json.loads(result.stdout)

            metadata = {
                "camera_model": "Unknown",
                "camera_make": "Unknown",
                "creation_date": None,
                "duration": 0,
                "bitrate": 0,
                "format": "",
                "width": 0,
                "height": 0,
                "fps": 0,
                "codec": "",
                "audio_codec": "",
                "file_size": os.path.getsize(file_path),
                "is_video": False,
                "is_audio": False,
                "is_image": False
            }

            if "format" in data:
                fmt = data["format"]
                metadata["format"] = fmt.get("format_name", "Unknown")
                metadata["creation_date"] = fmt.get("tags", {}).get("creation_time")
                metadata["duration"] = float(fmt.get("duration", 0))
                metadata["bitrate"] = int(fmt.get("bitrate", 0))

                format_tags = fmt.get("tags", {})
                if not metadata["creation_date"]:
                    metadata["creation_date"] = format_tags.get("date")
                if not metadata["creation_date"]:
                    metadata["creation_date"] = format_tags.get("com.apple.quicktime.creationdate")
                if not metadata["creation_date"]:
                    metadata["creation_date"] = format_tags.get("com.apple.quicktime.creationDate")

                if metadata["camera_model"] == "Unknown":
                    fmt_make = format_tags.get("make") or ""
                    fmt_model = format_tags.get("model") or ""
                    if fmt_model and fmt_model.lower() != "unknown":
                        metadata["camera_model"] = fmt_model
                    elif fmt_make and fmt_make.lower() != "unknown":
                        metadata["camera_model"] = fmt_make
                if metadata["camera_make"] == "Unknown":
                    fmt_make = format_tags.get("make") or ""
                    if fmt_make and fmt_make.lower() != "unknown":
                        metadata["camera_make"] = fmt_make

            for stream in data.get("streams", []):
                codec_type = stream.get("codec_type", "")

                if codec_type == "video":
                    metadata["is_video"] = True
                    metadata["width"] = int(stream.get("width", 0))
                    metadata["height"] = int(stream.get("height", 0))
                    metadata["codec"] = stream.get("codec_name", "")

                    fps_str = stream.get("r_frame_rate", "0/1")
                    if "/" in fps_str:
                        num, den = fps_str.split("/")
                        if int(den) > 0:
                            metadata["fps"] = round(int(num) / int(den), 2)

                    tags = stream.get("tags", {})
                    st_make = (tags.get("make") or "").strip()
                    st_model = (tags.get("model") or tags.get("handler_name") or "").strip()
                    st_model = "" if st_model.lower() in ("unknown", "n/a", "none", "") else st_model
                    st_make = "" if st_make.lower() in ("unknown", "n/a", "none", "") else st_make

                    if st_model:
                        metadata["camera_model"] = st_model
                    elif st_make and metadata["camera_model"] == "Unknown":
                        metadata["camera_model"] = st_make

                    if st_make:
                        metadata["camera_make"] = st_make

                elif codec_type == "audio":
                    metadata["is_audio"] = True
                    metadata["audio_codec"] = stream.get("codec_name", "")

            ext = os.path.splitext(file_path)[1].lower()
            image_extensions = ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif', '.webp']
            raw_extensions = ['.cr2', '.cr3', '.nef', '.arw', '.dng', '.raf', '.orf', '.rw2', '.pef', '.srw']

            if ext in image_extensions or ext in raw_extensions:
                metadata["is_image"] = True
                metadata["is_video"] = False
                camera_from_ext = self._camera_from_extension(ext)
                if metadata["camera_model"] == "Unknown" and camera_from_ext:
                    metadata["camera_model"] = camera_from_ext

            try:
                self._cache[file_path] = (mtime, metadata.copy())
                if len(self._cache) > self._MAX_CACHE:
                    for k in list(self._cache)[: self._MAX_CACHE // 2]:
                        self._cache.pop(k, None)
            except:
                pass

            return metadata

        except subprocess.TimeoutExpired:
            return {"camera_model": "Unknown", "camera_make": "Unknown", "creation_date": None,
                    "duration": 0, "bitrate": 0, "format": "", "width": 0, "height": 0,
                    "fps": 0, "codec": "", "audio_codec": "", "file_size": 0,
                    "is_video": False, "is_audio": False, "is_image": False}
        except Exception as e:
            print(f"Error extracting metadata from {file_path}: {e}")
            return {}

    def _camera_from_extension(self, ext: str) -> str:
        raw_ext_to_brand = {
            '.cr2': 'Canon', '.cr3': 'Canon',
            '.nef': 'Nikon',
            '.arw': 'Sony',
            '.dng': 'Generic DNG',
            '.raf': 'Fujifilm',
            '.orf': 'Olympus',
            '.rw2': 'Panasonic',
            '.pef': 'Pentax',
            '.srw': 'Samsung',
        }
        return raw_ext_to_brand.get(ext, "Unknown")
    
    def detect_camera_batch(self, file_paths: List[str]) -> Dict:
        camera_counts = {}
        
        for file_path in file_paths[:10]:
            metadata = self.get_video_metadata(file_path)
            if metadata:
                camera = metadata.get("camera_model", "Unknown")
                if camera != "Unknown":
                    camera_counts[camera] = camera_counts.get(camera, 0) + 1
        
        if camera_counts:
            dominant_camera = max(camera_counts.items(), key=lambda x: x[1])
            return {
                "primary_camera": dominant_camera[0],
                "camera_counts": camera_counts,
                "confidence": dominant_camera[1] / min(len(file_paths), 10)
            }
        
        return {
            "primary_camera": "Unknown",
            "camera_counts": {},
            "confidence": 0
        }
    
    def _builtin_extensions(self) -> set:
        return set(BUILTIN_EXTENSIONS)

    def _load_recognized_extensions(self):
        try:
            raw = db.get_containers()
        except Exception:
            raw = []
        exts = set()
        for e in raw:
            e = e.strip().lower()
            if not e:
                continue
            if not e.startswith("."):
                e = "." + e
            exts.add(e)
        self._recognized_extensions = exts or self._builtin_extensions()

    def refresh_file_types(self):
        self._recognized_extensions = None

    def get_recognized_extensions(self) -> set:
        if self._recognized_extensions is None:
            self._load_recognized_extensions()
        return self._recognized_extensions

    def get_file_type_info(self, file_path: str) -> Dict:
        ext = os.path.splitext(file_path)[1].lower()
        if not ext:
            return {"type": "other", "category": "reference"}
        if ext in VIDEO_EXTENSIONS:
            return {"type": "video", "category": "footage"}
        elif ext in AUDIO_EXTENSIONS:
            return {"type": "audio", "category": "audio"}
        elif ext in RAW_EXTENSIONS:
            return {"type": "raw_image", "category": "photos"}
        elif ext in IMAGE_EXTENSIONS:
            return {"type": "image", "category": "photos"}
        elif ext in self.get_recognized_extensions():
            return {"type": "media", "category": "media"}
        else:
            return {"type": "other", "category": "reference"}

metadata_engine = MetadataEngine()
