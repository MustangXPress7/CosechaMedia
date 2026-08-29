import os
import threading
import time
from collections import OrderedDict
from typing import Callable, Optional
from app.core.ingestor import Ingestor
from app.core.db import db
from app.core.metadata_engine import _is_system_entry

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
        scanned_files = OrderedDict()
        print(f"Watcher started on: {self.source_dir}")

        # El watcher sirve a un ingestor por fuente: le comunica su origen
        # para que should_skip registre/lea el inventario persistente (D-04).
        self.ingestor.source_dir = self.source_dir
        db.load_seen(self.source_dir)

        first_pass = True
        while self.running:
            try:
                current_files = set()
                for root, dirs, files in os.walk(self.source_dir):
                    dirs[:] = [d for d in dirs if not _is_system_entry(d)]
                    for file in files:
                        path = os.path.join(root, file)
                        current_files.add(path)

                        # Ignora archivos del sistema/ocultos: el chequeo debe
                        # ser sobre el nombre, no sobre la ruta absoluta
                        # (path.startswith('.') nunca se cumple en Windows).
                        if not self.ingestor.should_skip(path) and not _is_system_entry(file):
                            self.ingestor.handle_new_file(path)
                        scanned_files[path] = None

                # Evict entries for files that no longer exist on disk
                stale = [k for k in scanned_files if not os.path.exists(k)]
                for k in stale:
                    del scanned_files[k]

                # El inventario persiste en DB (tabla watcher_seen) en vez de
                # un cap en memoria: se guarda en lote y se poda por antigüedad.
                verdicts, filter_keys = self.ingestor.pass_verdicts()
                if verdicts:
                    db.save_seen(self.source_dir, verdicts, filter_keys)
                db.prune_seen(self.source_dir, days=30)

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
