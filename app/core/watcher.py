import os
import threading
import time
from typing import Callable, Optional
from app.core.ingestor import Ingestor

class FileSystemWatcher:
    def __init__(self, source_dir: str, ingestor: Ingestor, status_callback: Optional[Callable[[str], None]] = None):
        self.source_dir = source_dir
        self.ingestor = ingestor
        self.status_callback = status_callback
        self.running = False
        self._thread = None

    def start(self):
        if not self.running:
            self.running = True
            self._thread = threading.Thread(target=self._watch, daemon=True)
            self._thread.start()

    def stop(self):
        self.running = False

    def _watch(self):
        scanned_files = set()
        print(f"Watcher started on: {self.source_dir}")
        
        first_pass = True
        while self.running:
            try:
                current_files = set()
                for root, dirs, files in os.walk(self.source_dir):
                    for file in files:
                        path = os.path.join(root, file)
                        current_files.add(path)
                        
                        # Ignore hidden files and specific system files
                        if path not in scanned_files and not path.startswith('.'):
                            self.ingestor.handle_new_file(path)
                            scanned_files.add(path)
                
                # Keep set size manageable by removing old files
                if len(scanned_files) > 10000:
                    scanned_files = current_files
                
                if self.status_callback:
                    self.status_callback(f"Escaneados {len(current_files)} archivos en {self.source_dir}")
                
                if first_pass:
                    first_pass = False
                    self.ingestor.watcher_completed()
                    self.running = False
                    return
                
                time.sleep(1.0)
            except Exception as e:
                print(f"Watcher error: {e}")
