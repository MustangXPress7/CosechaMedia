import secrets
import sqlite3
import os
import sys
from datetime import datetime
from typing import List, Tuple, Optional


class DuplicateMasterPathError(Exception):
    """Se lanza al intentar crear un proyecto con una master_path que ya existe."""
    pass

def data_dir() -> str:
    """Directorio de datos de la app (junto al ejecutable si frozen)."""
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        from pathlib import Path
        base_dir = str(Path(__file__).resolve().parents[2])
    data_dir_path = os.path.join(base_dir, "data")
    os.makedirs(data_dir_path, exist_ok=True)
    return data_dir_path


def _resolve_db_path() -> str:
    return os.path.join(data_dir(), "sd_import.db")


WIFI_DEVICE_ID = "wifi:pairdrop"

class DatabaseManager:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or _resolve_db_path()
        self.create_tables()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=5)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.row_factory = sqlite3.Row
        return conn

    def create_tables(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                root_path TEXT,
                description TEXT,
                duration_type INTEGER DEFAULT 1,
                organization_type INTEGER DEFAULT 0,
                use_metadata_date BOOLEAN DEFAULT 1,
                default_dispositivo TEXT DEFAULT '',
                folder_name TEXT DEFAULT 'Footage',
                delicate_mode INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute("PRAGMA table_info(projects)")
        existing_cols = [row[1] for row in cursor.fetchall()]
        project_migrations = [
            ("duration_type", "INTEGER DEFAULT 1"),
            ("organization_type", "INTEGER DEFAULT 0"),
            ("use_metadata_date", "BOOLEAN DEFAULT 1"),
            ("default_dispositivo", "TEXT DEFAULT ''"),
            ("folder_name", "TEXT DEFAULT 'Footage'"),
            ("delicate_mode", "INTEGER DEFAULT 0"),
            ("dump_path", "TEXT"),
            ("camera_detection_mode", "TEXT DEFAULT 'auto'"),
            ("camera_detection_timeout", "INTEGER DEFAULT 5"),
            ("generate_proxies", "INTEGER DEFAULT 0"),
            ("proxy_resolution", "TEXT DEFAULT '720p'"),
            ("date_mode", "TEXT DEFAULT 'auto'"),
            ("manual_date", "TEXT"),
            ("camera_date_overrides", "TEXT DEFAULT '{}'"),
        ]
        for col_name, col_def in project_migrations:
            if col_name not in existing_cols:
                cursor.execute(f'ALTER TABLE projects ADD COLUMN {col_name} {col_def}')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dump_locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                path TEXT NOT NULL,
                label TEXT,
                include_date INTEGER DEFAULT 1,
                include_camera INTEGER DEFAULT 1,
                order_index INTEGER DEFAULT 0,
                FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
            )
        ''')

        # Backfill: Si un proyecto ya tiene ubicaciones de volcado, copiar la primera
        # (menor order_index) a la nueva columna dump_path. Después limpiar dump_locations.
        if "dump_path" not in existing_cols:
            cursor.execute('''
                SELECT p.id AS pid, (
                    SELECT dl.path FROM dump_locations dl
                    WHERE dl.project_id = p.id
                    ORDER BY dl.order_index ASC, dl.id ASC LIMIT 1
                ) AS first_path
                FROM projects p
            ''')
            for row in cursor.fetchall():
                pid = row[0]
                first_path = row[1]
                if first_path:
                    cursor.execute(
                        'UPDATE projects SET dump_path = ? WHERE id = ?',
                        (first_path, pid)
                    )
            # Eliminar todas las ubicaciones de volcado (ya migradas a dump_path).
            cursor.execute('DELETE FROM dump_locations')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dispositivos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                name TEXT NOT NULL,
                folder_name TEXT,
                FOREIGN KEY (project_id) REFERENCES projects (id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                name TEXT,
                dispositivo_id INTEGER,
                shoot_date DATE,
                status TEXT,
                content_mode TEXT DEFAULT 'all',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                destination_override TEXT,
                folder_name TEXT,
                organization_type INTEGER,
                duration_type INTEGER,
                default_dispositivo TEXT,
                use_metadata_date INTEGER,
                delicate_mode INTEGER,
                FOREIGN KEY (project_id) REFERENCES projects (id),
                FOREIGN KEY (dispositivo_id) REFERENCES dispositivos (id)
            )
        ''')

        cursor.execute("PRAGMA table_info(sessions)")
        sess_cols = [row[1] for row in cursor.fetchall()]
        if "name" not in sess_cols:
            cursor.execute("ALTER TABLE sessions ADD COLUMN name TEXT")

        session_migrations = [
            ("destination_override", "TEXT"),
            ("folder_name", "TEXT"),
            ("organization_type", "INTEGER"),
            ("duration_type", "INTEGER"),
            ("default_dispositivo", "TEXT"),
            ("use_metadata_date", "INTEGER"),
            ("delicate_mode", "INTEGER"),
            ("folder_mode", "INTEGER"),
            ("content_mode", "TEXT DEFAULT 'all'"),
            ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
            ("source_path", "TEXT"),
            ("nombre_dispositivo", "TEXT"),
            ("content_filter", "TEXT"),
            ("device_id", "TEXT"),
            ("device_folder", "TEXT"),
            ("enabled", "INTEGER DEFAULT 1"),
            ("date_mode", "TEXT"),
            ("manual_date", "TEXT"),
        ]
        for col_name, col_def in session_migrations:
            if col_name not in sess_cols:
                cursor.execute(f'ALTER TABLE sessions ADD COLUMN {col_name} {col_def}')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                source_path TEXT,
                dest_path TEXT,
                dump_location_id INTEGER,
                file_size INTEGER,
                md5_hash TEXT,
                status TEXT,
                verified_at TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (id)
            )
        ''')

        cursor.execute("PRAGMA table_info(files)")
        files_cols = [row[1] for row in cursor.fetchall()]
        if "dump_location_id" not in files_cols:
            cursor.execute("ALTER TABLE files ADD COLUMN dump_location_id INTEGER")

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sd_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                serial TEXT UNIQUE,
                brand TEXT,
                model TEXT,
                capacity_gb REAL,
                nombre_dispositivo TEXT,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute("PRAGMA table_info(sd_cards)")
        sd_cols = [row[1] for row in cursor.fetchall()]
        if "nombre_dispositivo" not in sd_cols:
            cursor.execute("ALTER TABLE sd_cards ADD COLUMN nombre_dispositivo TEXT")

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recent_paths (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL,
                path_type TEXT NOT NULL,
                last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                use_count INTEGER DEFAULT 1
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ftp_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                host TEXT NOT NULL,
                port INTEGER DEFAULT 21,
                username TEXT,
                password TEXT,
                base_folder TEXT DEFAULT '',
                passive INTEGER DEFAULT 1,
                timeout INTEGER DEFAULT 15,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inbox_senders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                location TEXT DEFAULT '',
                token TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute("PRAGMA table_info(inbox_senders)")
        sender_cols = [row[1] for row in cursor.fetchall()]
        if "location" not in sender_cols:
            cursor.execute(
                "ALTER TABLE inbox_senders ADD COLUMN location TEXT DEFAULT ''")

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS containers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS device_settings (
                device_key TEXT PRIMARY KEY,
                delicate_mode INTEGER DEFAULT 0
            )
        ''')
        cursor.execute("PRAGMA table_info(device_settings)")
        ds_cols = [row[1] for row in cursor.fetchall()]
        if "nombre_dispositivo" not in ds_cols:
            cursor.execute("ALTER TABLE device_settings ADD COLUMN nombre_dispositivo TEXT")

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        default_containers = [
            ".mp4", ".mov", ".avi", ".mkv", ".mxf", ".mts", ".m2ts", ".ts", ".mpg", ".mpeg",
            ".wav", ".mp3", ".aac", ".flac", ".ogg", ".m4a",
            ".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".gif", ".webp",
            ".cr2", ".cr3", ".nef", ".arw", ".dng", ".raf", ".orf", ".rw2", ".pef", ".srw",
        ]
        cursor.execute("SELECT name FROM containers LIMIT 1")
        first_row = cursor.fetchone()
        legacy = first_row is not None and not (first_row[0] or "").startswith(".")
        if legacy:
            cursor.execute("DELETE FROM containers")
        for c in default_containers:
            cursor.execute('INSERT OR IGNORE INTO containers (name) VALUES (?)', (c,))

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS footage_folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        ''')

        default_footage_folders = ["Footage", "Material", "Rodaje", "CAM", "Footage Final"]
        for f in default_footage_folders:
            cursor.execute('INSERT OR IGNORE INTO footage_folders (name) VALUES (?)', (f,))

        # Inventario de archivos vistos por el watcher (D-04). Migración
        # aditiva — no toca tablas existentes. `filter_key` guarda la firma
        # estable del content-filter activo para filas con veredicto
        # 'filtered' (re-evaluar si la ventana cambia) y es NULL en el resto.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS watcher_seen (
                source_path  TEXT NOT NULL,
                file_path    TEXT NOT NULL,
                first_seen   TEXT DEFAULT CURRENT_TIMESTAMP,
                last_verdict TEXT CHECK (last_verdict IN ('copied','filtered','errored')),
                filter_key   TEXT,
                PRIMARY KEY (source_path, file_path)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS known_devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT UNIQUE NOT NULL,
                device_type TEXT NOT NULL,
                name TEXT,
                serial TEXT,
                last_camera TEXT,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata_json TEXT
            )
        ''')

        cursor.execute('SELECT COUNT(*) FROM projects')
        if cursor.fetchone()[0] == 0:
            default_dest = os.path.join(
                os.path.dirname(self.db_path), "projects", "Default"
            )
            os.makedirs(default_dest, exist_ok=True)
            cursor.execute('''
                INSERT INTO projects (name, root_path, description)
                VALUES (?, ?, ?)
            ''', ("Default", os.path.abspath(default_dest),
                  "Proyecto creado automáticamente al primer arranque."))

        conn.commit()
        conn.close()

    def create_project(self, name: str, root_path: str, description: str = "") -> int:
        """Crea un proyecto verificando duplicados de master_path ANTES de la transacción.
        
        Args:
            name: Nombre del proyecto
            root_path: Ruta maestra (master path)
            description: Descripción opcional
            
        Returns:
            ID del proyecto creado
            
        Raises:
            DuplicateMasterPathError: Si ya existe un proyecto con la misma root_path
        """
        root_path = os.path.abspath(root_path)
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM projects WHERE root_path = ?', (root_path,))
            if cursor.fetchone():
                raise DuplicateMasterPathError(f"Ya existe un proyecto con la ruta maestra: {root_path}")
            
            cursor.execute(
                'INSERT INTO projects (name, root_path, description) VALUES (?, ?, ?)',
                (name, root_path, description)
            )
            project_id = cursor.lastrowid
            conn.commit()
            return project_id
        finally:
            conn.close()

    def save_recent_path(self, path: str, path_type: str):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id FROM recent_paths WHERE path = ? AND path_type = ?',
            (path, path_type)
        )
        row = cursor.fetchone()
        if row:
            cursor.execute(
                'UPDATE recent_paths SET last_used = ?, use_count = use_count + 1 WHERE id = ?',
                (now, row[0])
            )
        else:
            cursor.execute(
                'INSERT INTO recent_paths (path, path_type, last_used) VALUES (?, ?, ?)',
                (path, path_type, now)
            )
        cursor.execute(
            'DELETE FROM recent_paths WHERE path_type = ? AND id NOT IN (SELECT id FROM recent_paths WHERE path_type = ? ORDER BY last_used DESC, id DESC LIMIT 10)',
            (path_type, path_type)
        )
        conn.commit()
        conn.close()

    def get_recent_paths(self, path_type: str, limit: int = 10):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT path FROM recent_paths WHERE path_type = ? ORDER BY last_used DESC, id DESC LIMIT ?',
            (path_type, limit)
        )
        paths = [row[0] for row in cursor.fetchall()]
        conn.close()
        return paths

    def remove_recent_path(self, path: str, path_type: str = "source"):
        """Olvida una ruta guardada (no borra la carpeta ni sus sesiones)."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'DELETE FROM recent_paths WHERE path = ? AND path_type = ?',
            (path, path_type)
        )
        conn.commit()
        conn.close()

    def get_containers(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM containers ORDER BY name')
        names = [row[0] for row in cursor.fetchall()]
        conn.close()
        return names

    @staticmethod
    def _normalize_container(name: str) -> str:
        name = (name or "").strip()
        if name and not name.startswith("."):
            name = "." + name
        return name

    def add_container(self, name: str):
        name = self._normalize_container(name)
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO containers (name) VALUES (?)', (name,))
        conn.commit()
        conn.close()

    def delete_container(self, name: str):
        name = self._normalize_container(name)
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM containers WHERE name = ?', (name,))
        conn.commit()
        conn.close()

    def rename_container(self, old_name: str, new_name: str):
        old_name = self._normalize_container(old_name)
        new_name = self._normalize_container(new_name)
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE containers SET name = ? WHERE name = ?', (new_name, old_name))
        conn.commit()
        conn.close()

    def get_footage_folders(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM footage_folders ORDER BY name')
        names = [row[0] for row in cursor.fetchall()]
        conn.close()
        return names

    def add_footage_folder(self, name: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO footage_folders (name) VALUES (?)', (name,))
        conn.commit()
        conn.close()

    def rename_footage_folder(self, old_name: str, new_name: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE footage_folders SET name = ? WHERE name = ?', (new_name, old_name))
        conn.commit()
        conn.close()

    def delete_footage_folder(self, name: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM footage_folders WHERE name = ?', (name,))
        conn.commit()
        conn.close()

    def duplicate_footage_folder(self, name: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO footage_folders (name) VALUES (?)', (f"{name} (copia)",))
        conn.commit()
        conn.close()

    def get_project_dump_path(self, project_id: int):
        """Devuelve la carpeta de volcado del proyecto o None si no está fijada."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT dump_path FROM projects WHERE id = ?', (project_id,)
        )
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        return row[0] or None

    def set_project_dump_path(self, project_id: int, path: str):
        """Fija la única carpeta de volcado del proyecto (path abspath)."""
        if path:
            path = os.path.abspath(path)
        else:
            path = None
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE projects SET dump_path = ? WHERE id = ?',
            (path, project_id)
        )
        conn.commit()
        conn.close()

    def update_project_description(self, project_id: int, text: str):
        """Actualiza la descripción del proyecto."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE projects SET description = ? WHERE id = ?',
            (text, project_id)
        )
        conn.commit()
        conn.close()

    def create_session(self, project_id: int, name: str, shoot_date: str = None, status: str = "pending", source_path: str = None, content_mode: str = "all"):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO sessions (project_id, name, shoot_date, status, content_mode, source_path) VALUES (?, ?, ?, ?, ?, ?)',
            (project_id, name, shoot_date, status, content_mode, source_path)
        )
        session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return session_id

    def get_sessions(self, project_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT id, name, shoot_date, status, destination_override,
                      folder_name, organization_type, duration_type, default_dispositivo,
                      use_metadata_date, delicate_mode, created_at, source_path, nombre_dispositivo,
                      content_filter, device_id, device_folder, enabled, folder_mode, content_mode
                FROM sessions WHERE project_id = ? ORDER BY id ASC''',
            (project_id,)
        )
        rows = []
        for r in cursor.fetchall():
            rows.append({
                "id": r[0],
                "name": r[1],
                "date": r[2],
                "status": r[3],
                "destination_override": r[4],
                "folder_name": r[5],
                "organization_type": r[6],
                "duration_type": r[7],
                "default_dispositivo": r[8],
                "use_metadata_date": r[9],
                "delicate_mode": r[10],
                "created_at": r[11],
                "source_path": r[12],
                "nombre_dispositivo": r[13],
                "content_filter": r[14],
                "device_id": r[15],
                "device_folder": r[16],
                "enabled": r[17],
                "folder_mode": r[18],
                "content_mode": r[19],
            })
        conn.close()
        return rows

    def get_session(self, session_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT id, project_id, name, shoot_date, status, destination_override,
                      folder_name, organization_type, duration_type, default_dispositivo,
                      use_metadata_date, delicate_mode, created_at, source_path, nombre_dispositivo,
                      content_filter, device_id, device_folder, enabled, folder_mode, content_mode
                FROM sessions WHERE id = ?''',
            (session_id,)
        )
        r = cursor.fetchone()
        conn.close()
        if not r:
            return None
        return {
            "id": r[0],
            "project_id": r[1],
            "name": r[2],
            "date": r[3],
            "status": r[4],
            "destination_override": r[5],
            "folder_name": r[6],
            "organization_type": r[7],
            "duration_type": r[8],
            "default_dispositivo": r[9],
            "use_metadata_date": r[10],
            "delicate_mode": r[11],
            "created_at": r[12],
            "source_path": r[13],
            "nombre_dispositivo": r[14],
            "content_filter": r[15],
            "device_id": r[16],
            "device_folder": r[17],
            "enabled": r[18],
            "folder_mode": r[19],
            "content_mode": r[20],
        }

    def get_files_by_session(self, session_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT source_path, dest_path, file_size, md5_hash, status, verified_at
               FROM files WHERE session_id = ? ORDER BY id''',
            (session_id,)
        )
        rows = [{"source_path": r[0], "dest_path": r[1], "file_size": r[2],
                 "md5_hash": r[3], "status": r[4], "verified_at": r[5]}
                for r in cursor.fetchall()]
        conn.close()
        return rows

    def get_last_dump_date_for_session(self, session_id: int) -> Optional[str]:
        """Devuelve la fecha del último archivo archivado (YYYY-MM-DD) o None si no hay archivos."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT verified_at FROM files 
               WHERE session_id = ? AND verified_at IS NOT NULL
               ORDER BY verified_at DESC LIMIT 1''',
            (session_id,)
        )
        row = cursor.fetchone()
        conn.close()
        if row and row[0]:
            try:
                dt = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
                return dt.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                return None
        return None

    def update_session_config(self, session_id: int, **kwargs):
        if not kwargs:
            return
        allowed = {"destination_override", "folder_name", "organization_type",
                   "duration_type", "default_dispositivo", "use_metadata_date",
                   "delicate_mode", "folder_mode", "name", "shoot_date", "status",
                   "source_path", "nombre_dispositivo", "content_filter",
                   "device_id", "device_folder", "enabled", "content_mode"}
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if not fields:
            return
        set_clause = ", ".join(f"{k} = ?" for k in fields.keys())
        values = list(fields.values()) + [session_id]
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f"UPDATE sessions SET {set_clause} WHERE id = ?", values)
        conn.commit()
        conn.close()

    def delete_session(self, session_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM files WHERE session_id = ?', (session_id,))
        cursor.execute('DELETE FROM sessions WHERE id = ?', (session_id,))
        conn.commit()
        conn.close()

    def get_devices(self):
        """Devuelve dispositivos guardados (device_id, device_folder) con nº de sesiones."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT device_id, device_folder, COUNT(*) AS session_count
               FROM sessions
               WHERE device_id IS NOT NULL AND device_id != ''
               GROUP BY device_id, device_folder
               ORDER BY device_id ASC'''
        )
        rows = [{
            "device_id": r[0],
            "device_folder": r[1] or "",
            "session_count": r[2],
        } for r in cursor.fetchall()]
        conn.close()
        return rows

    def get_sessions_by_device(self, device_id: str):
        """Devuelve las sesiones asociadas a un dispositivo (para auto-sync)."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT id, project_id, name, shoot_date, status, destination_override,
                      folder_name, organization_type, duration_type, default_dispositivo,
                      use_metadata_date, delicate_mode, created_at, source_path, nombre_dispositivo,
                      content_filter, device_id, device_folder
               FROM sessions WHERE device_id = ? AND device_id != '' ORDER BY id ASC''',
            (device_id,)
        )
        rows = []
        for r in cursor.fetchall():
            rows.append({
                "id": r[0],
                "project_id": r[1],
                "name": r[2],
                "date": r[3],
                "status": r[4],
                "destination_override": r[5],
                "folder_name": r[6],
                "organization_type": r[7],
                "duration_type": r[8],
"default_dispositivo": r[9],
                "use_metadata_date": r[10],
                "delicate_mode": r[11],
                "created_at": r[12],
                "source_path": r[13],
                "nombre_dispositivo": r[14],
                "content_filter": r[15],
                "device_id": r[16],
                "device_folder": r[17],
            })
        conn.close()
        return rows

    def delete_device(self, device_id: str):
        """Elimina todas las sesiones (y sus archivos) asociadas a un dispositivo.

        También limpia el mapeo de cámara guardado del dispositivo
        (device_settings), para que al volver a detectarlo no resucite un
        nombre de cámara que el usuario solicitó borrar (bug origen 1)."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id FROM sessions WHERE device_id = ? AND device_id != ?',
            (device_id, "")
        )
        ids = [r[0] for r in cursor.fetchall()]
        for sid in ids:
            cursor.execute('DELETE FROM files WHERE session_id = ?', (sid,))
        cursor.execute(
            'DELETE FROM sessions WHERE device_id = ? AND device_id != ?',
            (device_id, "")
        )
        cursor.execute(
            'DELETE FROM device_settings WHERE device_key = ?',
            (device_id,)
        )
        conn.commit()
        conn.close()
        return ids

    def delete_device_settings_by_key(self, device_key: str):
        """Elimina el mapeo de cámara guardado (device_settings) de un device_key.

        Se usa para limpiar entradas huérfanas que un bug anterior guardó bajo
        ids WPD de almacenamiento masivo (usbstor), que no son MTP reales."""
        if not device_key:
            return
        conn = self.get_connection()
        conn.execute('DELETE FROM device_settings WHERE device_key = ?', (device_key,))
        conn.commit()
        conn.close()

    def add_ftp_profile(self, name: str, host: str, port: int = 21, username: str = "",
                        password: str = "", base_folder: str = "",
                        passive: bool = True, timeout: int = 15) -> int:
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO ftp_profiles (name, host, port, username, password, base_folder, passive, timeout)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                (name, host, int(port), username or "", password or "",
                 base_folder or "", int(bool(passive)), int(timeout or 15))
            )
            pid = cursor.lastrowid
            conn.commit()
            return pid
        finally:
            conn.close()

    def get_ftp_profile(self, profile_id: int):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT id, name, host, port, username, password, base_folder, passive, timeout
                   FROM ftp_profiles WHERE id = ?''', (profile_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "id": row[0], "name": row[1], "host": row[2], "port": row[3],
                "username": row[4], "password": row[5], "base_folder": row[6],
                "passive": bool(row[7]), "timeout": row[8],
            }
        finally:
            conn.close()

    def list_ftp_profiles(self):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT id, name, host, port, username, password, base_folder, passive, timeout
                   FROM ftp_profiles ORDER BY id ASC'''
            )
            rows = [{
                "id": r[0], "name": r[1], "host": r[2], "port": r[3],
                "username": r[4], "password": r[5], "base_folder": r[6],
                "passive": bool(r[7]), "timeout": r[8],
            } for r in cursor.fetchall()]
            return rows
        finally:
            conn.close()

    def update_ftp_profile(self, profile_id: int, **kwargs):
        allowed = {"name", "host", "port", "username", "password",
                   "base_folder", "passive", "timeout"}
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if not fields:
            return
        set_clause = ", ".join(f"{k} = ?" for k in fields.keys())
        values = list(fields.values()) + [profile_id]
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE ftp_profiles SET {set_clause} WHERE id = ?", values)
            conn.commit()
        finally:
            conn.close()

    def delete_ftp_profile(self, profile_id: int):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM ftp_profiles WHERE id = ?', (profile_id,))
            conn.commit()
        finally:
            conn.close()

    def upsert_known_device(self, device_id: str, device_type: str, name: str = None,
                           serial: str = None, last_camera: str = None, metadata: dict = None) -> int:
        """Inserta o actualiza un dispositivo conocido.
        
        Args:
            device_id: ID único del dispositivo (PnP para MTP, ftp:<id> para FTP, wifi:<alias> para WiFi)
            device_type: 'mtp', 'ftp', 'wifi', 'usb'
            name: Nombre amigable del dispositivo
            serial: Número de serie si disponible
            last_camera: Último nombre de cámara detectado
            metadata: Dict con metadatos extra (modelo, fabricante, etc.)
            
        Returns:
            ID del dispositivo en known_devices
        """
        import json
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO known_devices (device_id, device_type, name, serial, last_camera, metadata_json, last_seen)
                   VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(device_id) DO UPDATE SET
                       device_type = excluded.device_type,
                       name = COALESCE(excluded.name, known_devices.name),
                       serial = COALESCE(excluded.serial, known_devices.serial),
                       last_camera = COALESCE(excluded.last_camera, known_devices.last_camera),
                       metadata_json = COALESCE(excluded.metadata_json, known_devices.metadata_json),
                       last_seen = CURRENT_TIMESTAMP''',
                (device_id, device_type, name, serial, last_camera, json.dumps(metadata) if metadata else None)
            )
            cursor.execute('SELECT id FROM known_devices WHERE device_id = ?', (device_id,))
            row = cursor.fetchone()
            conn.commit()
            return row[0] if row else None
        finally:
            conn.close()

    def get_known_device(self, device_id: str):
        """Obtiene la información completa de un dispositivo conocido."""
        import json
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id, device_id, device_type, name, serial, last_camera, last_seen, metadata_json '
                'FROM known_devices WHERE device_id = ?', (device_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "device_id": row[1],
                "device_type": row[2],
                "name": row[3],
                "serial": row[4],
                "last_camera": row[5],
                "last_seen": row[6],
                "metadata": json.loads(row[7]) if row[7] else None,
            }
        finally:
            conn.close()

    def list_known_devices(self):
        """Lista todos los dispositivos conocidos para la UI."""
        import json
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id, device_id, device_type, name, serial, last_camera, last_seen, metadata_json '
                'FROM known_devices ORDER BY last_seen DESC'
            )
            rows = []
            for r in cursor.fetchall():
                rows.append({
                    "id": r[0],
                    "device_id": r[1],
                    "device_type": r[2],
                    "name": r[3],
                    "serial": r[4],
                    "last_camera": r[5],
                    "last_seen": r[6],
                    "metadata": json.loads(r[7]) if r[7] else None,
                })
            return rows
        finally:
            conn.close()

    def delete_known_device(self, device_id: str):
        """Elimina un dispositivo conocido."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM known_devices WHERE device_id = ?', (device_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def sync_device_settings_to_known(self):
        """Migra datos de device_settings a known_devices (one-time migration)."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT device_key, nombre_dispositivo FROM device_settings WHERE nombre_dispositivo IS NOT NULL AND nombre_dispositivo != ""')
            migrated = 0
            for device_key, nombre in cursor.fetchall():
                # device_key puede ser PnP ID (MTP) o ftp:<id> (FTP)
                if device_key.startswith("ftp:"):
                    device_type = "ftp"
                elif device_key.startswith("wifi:"):
                    device_type = "wifi"
                else:
                    device_type = "mtp"
                self.upsert_known_device(device_key, device_type, name=nombre)
                migrated += 1
            conn.commit()
            return migrated
        finally:
            conn.close()

    def list_known_camera_names(self):
        """Nombres de cámara conocidos agregados de sd_cards, device_settings y dispositivos."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            names = set()
            for table, col in (("sd_cards", "nombre_dispositivo"),
                               ("device_settings", "nombre_dispositivo"),
                               ("dispositivos", "name")):
                try:
                    cursor.execute(f'SELECT {col} FROM {table}')
                    for (n,) in cursor.fetchall():
                        n = (n or "").strip()
                        if n:
                            names.add(n)
                except Exception:
                    pass
            return sorted(n for n in names if n and n != "Sin nombre")
        finally:
            conn.close()

    def delete_all_known_cameras(self):
        """Limpia todos los nombres de cámara conocidos (CHG-2)."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM sd_cards')
            cursor.execute('DELETE FROM device_settings')
            cursor.execute('DELETE FROM dispositivos')
            conn.commit()
        finally:
            conn.close()

    def delete_all_saved_devices(self):
        """Borra todos los dispositivos guardados y remitentes sino perfiles FTP (CHG-1).

        Limpia las tablas de dispositivo/remitente/perfil; las sesiones se
        conservan (solo se olvida el registro guardado)."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM sd_cards')
            cursor.execute('DELETE FROM device_settings')
            cursor.execute('DELETE FROM dispositivos')
            cursor.execute('DELETE FROM inbox_senders')
            cursor.execute('DELETE FROM ftp_profiles')
            conn.commit()
        finally:
            conn.close()

    def list_inbox_senders(self):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT id, name, location, token, created_at FROM inbox_senders ORDER BY id ASC'''
            )
            rows = [{
                "id": r[0], "name": r[1], "location": r[2], "token": r[3], "created_at": r[4],
            } for r in cursor.fetchall()]
            return rows
        finally:
            conn.close()

    def add_inbox_sender(self, name: str, location: str = "") -> int:
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO inbox_senders (name, location, token) VALUES (?, ?, ?)''',
                (name, location, secrets.token_urlsafe(12))
            )
            sid = cursor.lastrowid
            conn.commit()
            return sid
        finally:
            conn.close()

    def update_inbox_sender(self, sender_id: int, name: str, location: str = ""):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE inbox_senders SET name = ?, location = ? WHERE id = ?',
                (name, location, sender_id))
            conn.commit()
        finally:
            conn.close()

    def delete_inbox_sender(self, sender_id: int):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM inbox_senders WHERE id = ?', (sender_id,))
            conn.commit()
        finally:
            conn.close()

    def get_or_create_wifi_session(self, project_id: int, sender_name: str,
                                    source_path: str, location: str = "") -> int:
        """Devuelve/crea la sesión de ingesta WiFi de un remitente.

        Cada remitente de PairDrop es una sesión con ``device_id =
        'wifi:pairdrop'`` y ``device_folder = sanitize_alias(sender_name)``.
        La ubicación del remitente (opcional) se traduce al
        ``destination_override`` de la sesión, de modo que la ingesta posterior
        respete ese destino. El ``source_path`` apunta a la caché local de
        recepción (``data/inbox/<alias>``).
        """
        from datetime import datetime as _dt
        from app.core.shoot_inbox import sanitize_alias
        alias = sanitize_alias(sender_name)
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM sessions WHERE project_id = ? AND device_id = ? AND device_folder = ?",
                (project_id, WIFI_DEVICE_ID, alias),
            )
            row = cursor.fetchone()
            if row is not None:
                sid = row[0]
                if location:
                    # Si el remitente tiene ubicación se aplica; si no, se respeta
                    # el destination_override que el usuario haya configurado.
                    cursor.execute(
                        "UPDATE sessions SET source_path = ?, nombre_dispositivo = ?, "
                        "destination_override = ? WHERE id = ?",
                        (source_path, sender_name, location, sid),
                    )
                else:
                    cursor.execute(
                        "UPDATE sessions SET source_path = ?, nombre_dispositivo = ? "
                        "WHERE id = ?",
                        (source_path, sender_name, sid),
                    )
                conn.commit()
                return sid
            cursor.execute(
                "INSERT INTO sessions (project_id, name, shoot_date, status, "
                "source_path, nombre_dispositivo, device_id, device_folder, destination_override) "
                "VALUES (?, ?, ?, 'active', ?, ?, ?, ?, ?)",
                (
                    project_id,
                    f"WiFi ({sender_name})",
                    _dt.now().strftime("%Y-%m-%d"),
                    source_path,
                    sender_name,
                    WIFI_DEVICE_ID,
                    alias,
                    location or None,
                ),
            )
            sid = cursor.lastrowid
            conn.commit()
            return sid
        finally:
            conn.close()

    def list_wifi_sessions(self, project_id: int):
        """Devuelve las sesiones WiFi (PairDrop) de un proyecto."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name, device_folder, source_path, nombre_dispositivo, "
                "destination_override FROM sessions "
                "WHERE project_id = ? AND device_id = ? ORDER BY id ASC",
                (project_id, WIFI_DEVICE_ID),
            )
            rows = [{
                "id": r[0],
                "name": r[1],
                "device_folder": r[2],
                "source_path": r[3],
                "nombre_dispositivo": r[4],
                "destination_override": r[5],
            } for r in cursor.fetchall()]
            return rows
        finally:
            conn.close()

    def dump_locations(self, project_id: int):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT id, path, label, include_date, include_camera, order_index
                   FROM dump_locations WHERE project_id = ? ORDER BY order_index ASC, id ASC''',
                (project_id,)
            )
            rows = [{
                "id": r[0], "path": r[1], "label": r[2],
                "include_date": bool(r[3]), "include_camera": bool(r[4]),
                "order_index": r[5]
            } for r in cursor.fetchall()]
            return rows
        finally:
            conn.close()

    def add_dump_location(self, project_id: int, path: str, label: str = None,
                          include_date: bool = True, include_camera: bool = True):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT COALESCE(MAX(order_index), -1) + 1 FROM dump_locations WHERE project_id = ?',
                (project_id,)
            )
            next_idx = cursor.fetchone()[0]
            cursor.execute(
                '''INSERT INTO dump_locations (project_id, path, label, include_date, include_camera, order_index)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (project_id, os.path.abspath(path), label, int(include_date), int(include_camera), next_idx)
            )
            lid = cursor.lastrowid
            conn.commit()
            return lid
        finally:
            conn.close()

    def update_dump_location(self, location_id: int, **kwargs):
        allowed = {"path", "label", "include_date", "include_camera", "order_index"}
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if not fields:
            return
        if "path" in fields:
            fields["path"] = os.path.abspath(fields["path"])
        set_clause = ", ".join(f"{k} = ?" for k in fields.keys())
        values = list(fields.values()) + [location_id]
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE dump_locations SET {set_clause} WHERE id = ?", values)
            conn.commit()
        finally:
            conn.close()

    def delete_dump_location(self, location_id: int):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM dump_locations WHERE id = ?', (location_id,))
            conn.commit()
        finally:
            conn.close()

    def reorder_dump_locations(self, project_id: int, ordered_ids: list):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            for idx, loc_id in enumerate(ordered_ids):
                cursor.execute(
                    'UPDATE dump_locations SET order_index = ? WHERE id = ? AND project_id = ?',
                    (idx, loc_id, project_id)
                )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _sanitize_dispositivo_nombre(name: str) -> str:
        """Limpia un nombre de dispositivo antes de persistirlo (T-01.6.0-15).

        Elimina caracteres de control (ord < 32), recorta espacios y limita
        la longitud a 100 caracteres para proteger la UI y la exportación.
        """
        if not name:
            return name
        cleaned = "".join(ch for ch in name if ord(ch) >= 32)
        cleaned = cleaned.strip()
        return cleaned[:100]

    def save_dispositivo(self, volume_serial: str, nombre_dispositivo: str, brand: str = None, model: str = None):
        """Guarda o actualiza el mapeo serial→cámara para una tarjeta SD."""
        nombre_dispositivo = self._sanitize_dispositivo_nombre(nombre_dispositivo)
        if not volume_serial or not nombre_dispositivo:
            return
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id FROM sd_cards WHERE serial = ?', (volume_serial,)
            )
            row = cursor.fetchone()
            if row:
                updates = ['nombre_dispositivo = ?', 'last_used = CURRENT_TIMESTAMP']
                params = [nombre_dispositivo]
                if brand:
                    updates.append('brand = ?')
                    params.append(brand)
                if model:
                    updates.append('model = ?')
                    params.append(model)
                params.append(volume_serial)
                cursor.execute(
                    f'UPDATE sd_cards SET {", ".join(updates)} WHERE serial = ?', params
                )
            else:
                cursor.execute(
                    'INSERT INTO sd_cards (serial, brand, model, nombre_dispositivo) VALUES (?, ?, ?, ?)',
                    (volume_serial, brand, model, nombre_dispositivo)
                )
            conn.commit()
        finally:
            conn.close()

    def get_dispositivo_for_card(self, volume_serial: str):
        """Devuelve el nombre de cámara conocido para un serial de tarjeta, o None."""
        if not volume_serial:
            return None
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT nombre_dispositivo FROM sd_cards WHERE serial = ?', (volume_serial,)
            )
            row = cursor.fetchone()
            if row and row['nombre_dispositivo']:
                return row['nombre_dispositivo']
            return None
        finally:
            conn.close()

    def get_dispositivo_for_device(self, device_id: str):
        """Devuelve el nombre de dispositivo conocido para un dispositivo MTP/FTP, o None.
        
        Prioridad: known_devices (nueva tabla unificada) > device_settings (legacy).
        """
        if not device_id:
            return None
        # Primero buscar en known_devices (tabla unificada)
        known = self.get_known_device(device_id)
        if known and known.get("name"):
            return known["name"]
        # Fallback a device_settings (legacy)
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT nombre_dispositivo FROM device_settings WHERE device_key = ?',
                (device_id,)
            )
            row = cursor.fetchone()
            if row and row['nombre_dispositivo']:
                return row['nombre_dispositivo']
            return None
        finally:
            conn.close()

    def save_dispositivo_config(self, device_id: str, nombre_dispositivo: str):
        """Guarda o actualiza el mapeo device_id→cámara para dispositivos MTP/FTP."""
        nombre_dispositivo = self._sanitize_dispositivo_nombre(nombre_dispositivo)
        if not device_id or not nombre_dispositivo:
            return
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT device_key FROM device_settings WHERE device_key = ?',
                (device_id,)
            )
            row = cursor.fetchone()
            if row:
                cursor.execute(
                    'UPDATE device_settings SET nombre_dispositivo = ? WHERE device_key = ?',
                    (nombre_dispositivo, device_id)
                )
            else:
                cursor.execute(
                    'INSERT INTO device_settings (device_key, nombre_dispositivo) VALUES (?, ?)',
                    (device_id, nombre_dispositivo)
                )
            conn.commit()
        finally:
            conn.close()

    def get_device_delicate(self, device_key: str):
        """Devuelve el modo delicado para un dispositivo (0/1), o None si no hay config."""
        if not device_key:
            return None
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT delicate_mode FROM device_settings WHERE device_key = ?',
                (device_key,)
            )
            row = cursor.fetchone()
            return int(row['delicate_mode']) if row else None
        finally:
            conn.close()

    def set_device_delicate(self, device_key: str, delicate: bool):
        """Guarda el modo delicado para un dispositivo."""
        if not device_key:
            return
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT OR REPLACE INTO device_settings (device_key, delicate_mode) VALUES (?, ?)',
                (device_key, int(delicate))
            )
            conn.commit()
        finally:
            conn.close()

    def get_setting(self, key: str, default=None):
        """Obtiene un valor de configuración general."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT value FROM settings WHERE key = ?', (key,)
            )
            row = cursor.fetchone()
            if row:
                return row[0]
            return default
        finally:
            conn.close()

    def set_setting(self, key: str, value):
        """Guarda un valor de configuración general."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
                (key, value)
            )
            conn.commit()
        finally:
            conn.close()

    def load_seen(self, source_path: str) -> dict:
        """Inventario de archivos vistos por el watcher para una fuente.

        Devuelve ``dict[file_path_normalizado, verdict]`` donde el valor es
        el último veredicto ('copied'/'filtered'/'errored'). Las rutas se
        normalizan con ``os.path.normpath`` para que variantes (p. ej.
        separadores Windows/Linux) dedupliquen correctamente.
        """
        seen = {}
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT file_path, last_verdict, filter_key FROM watcher_seen "
                "WHERE source_path = ?",
                (os.path.normpath(source_path),)
            )
            for row in cursor.fetchall():
                seen[os.path.normpath(row["file_path"])] = row["last_verdict"]
        finally:
            conn.close()
        return seen

    def load_seen_filter_key(self, source_path: str, file_path: str) -> Optional[str]:
        """Firma del content-filter guardada para un archivo 'filtered'.

        Devuelve el ``filter_key`` de la fila del inventario, o ``None`` si la
        fila no existe o no tiene filtro asociado (no-'filtered'). Se usa en
        ``should_skip`` para re-evaluar cuando la ventana cambia (Open
        Question 4).
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT filter_key FROM watcher_seen "
                "WHERE source_path = ? AND file_path = ?",
                (os.path.normpath(source_path), os.path.normpath(file_path))
            )
            row = cursor.fetchone()
            return row["filter_key"] if row else None
        finally:
            conn.close()

    def save_seen(self, source_path: str, verdicts: dict, filter_keys: dict = None) -> None:
        """Graba el inventario de la pasada del watcher en una transacción.

        ``verdicts`` es un dict ``{file_path: verdict}`` (uno por archivo);
        ``filter_keys`` opcional ``{file_path: firma}`` para las filas
        'filtered'. ``INSERT OR IGNORE`` evita duplicar entradas ya vistas.
        Las rutas se normalizan en ambas direcciones.
        """
        if not verdicts:
            return
        filter_keys = filter_keys or {}
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            norm_source = os.path.normpath(source_path)
            for file_path, verdict in verdicts.items():
                cursor.execute(
                    "INSERT OR IGNORE INTO watcher_seen "
                    "(source_path, file_path, last_verdict, filter_key) "
                    "VALUES (?, ?, ?, ?)",
                    (norm_source, os.path.normpath(file_path), verdict,
                     filter_keys.get(file_path))
                )
            conn.commit()
        except Exception as e:
            print(f"Error saving watcher inventory for {source_path}: {e}")
            conn.rollback()
        finally:
            conn.close()

    def prune_seen(self, source_path: str, days: int = 30) -> None:
        """Poda por antigüedad del inventario de una fuente.

        Elimina filas vistas hace más de ``days`` días (por defecto 30). El
        número de días se pasa parametrizado a SQLite (jamás interpolado).
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM watcher_seen WHERE source_path = ? "
                "AND first_seen < datetime('now', ?)",
                (os.path.normpath(source_path), f'-{days} days')
            )
            conn.commit()
        except Exception as e:
            print(f"Error pruning watcher inventory for {source_path}: {e}")
            conn.rollback()
        finally:
            conn.close()


db = DatabaseManager()
