import subprocess
import os
from typing import Optional

class FFmpegProcessor:
    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg_path = ffmpeg_path

    def create_proxy(self, input_path: str, output_folder: str, height: int = 720) -> Optional[str]:
        """
        Creates a low-resolution proxy of a video file.
        
        Args:
            input_path: Path to the source video file.
            output_folder: Folder where the proxy will be saved.
            height: Height in pixels of the proxy (e.g. 720 or 1080).
            
        Returns:
            The path to the created proxy file, or None if it fails.
        """
        # Ensure output folder exists
        os.makedirs(output_folder, exist_ok=True)
        
        # Generate output filename (change extension to .mp4)
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(output_folder, f"{base_name}_proxy.mp4")

        # FFmpeg command for a generic proxy:
        # -vf scale=-1:{height} (height in pixels, maintain aspect ratio)
        # -c:v libx264 (standard H.264)
        # -preset ultrafast (fast encoding)
        # -crf 28 (good balance for proxies)
        # -c:a aac (standard audio)
        command = [
            self.ffmpeg_path,
            "-y",                # Overwrite output
            "-i", input_path,
            "-vf", f"scale=-1:{height}",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "28",
            "-c:a", "aac",
            "-b:a", "128k",
            output_path
        ]

        try:
            # Run ffmpeg and hide output unless there's an error
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            return output_path
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg Error: {e.stderr}")
            return None
        except FileNotFoundError:
            print("FFmpeg not found in system path.")
            return None

# Singleton instance
ffmpeg = FFmpegProcessor()
