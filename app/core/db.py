import sqlite3
import os
import sys
from datetime import datetime
from typing import List, Tuple

def _resolve_db_path() -> str:
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.getcwd()
    data_dir = os.path.join(base_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "sd_import.db")

class DatabaseManager:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or _resolve_db_path()
        self.create_tables()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=5)
        conn.execute("PRAGMA journal_mode=WAL")
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
                default_camera TEXT DEFAULT '',
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
            ("default_camera", "TEXT DEFAULT ''"),
            ("folder_name", "TEXT DEFAULT 'Footage'"),
            ("delicate_mode", "INTEGER DEFAULT 0"),
            ("dump_path", "TEXT"),
            ("camera_detection_mode", "TEXT DEFAULT 'auto'"),
            ("camera_detection_timeout", "INTEGER DEFAULT 5"),
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
            CREATE TABLE IF NOT EXISTS cameras (
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
                camera_id INTEGER,
                shoot_date DATE,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                destination_override TEXT,
                folder_name TEXT,
                organization_type INTEGER,
                duration_type INTEGER,
                default_camera TEXT,
                use_metadata_date INTEGER,
                delicate_mode INTEGER,
                FOREIGN KEY (project_id) REFERENCES projects (id),
                FOREIGN KEY (camera_id) REFERENCES cameras (id)
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
            ("default_camera", "TEXT"),
            ("use_metadata_date", "INTEGER"),
            ("delicate_mode", "INTEGER"),
            ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
            ("source_path", "TEXT"),
            ("camera_name", "TEXT"),
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
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

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
            CREATE TABLE IF NOT EXISTS containers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
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
            'DELETE FROM recent_paths WHERE path_type = ? AND id NOT IN (SELECT id FROM recent_paths WHERE path_type = ? ORDER BY last_used DESC LIMIT 10)',
            (path_type, path_type)
        )
        conn.commit()
        conn.close()

    def get_recent_paths(self, path_type: str, limit: int = 10):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT path FROM recent_paths WHERE path_type = ? ORDER BY last_used DESC LIMIT ?',
            (path_type, limit)
        )
        paths = [row[0] for row in cursor.fetchall()]
        conn.close()
        return paths

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

    def create_session(self, project_id: int, name: str, shoot_date: str = None, status: str = "pending", source_path: str = None):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO sessions (project_id, name, shoot_date, status, source_path) VALUES (?, ?, ?, ?, ?)',
            (project_id, name, shoot_date, status, source_path)
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
                      folder_name, organization_type, duration_type, default_camera,
                      use_metadata_date, delicate_mode, created_at, source_path, camera_name
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
                "default_camera": r[8],
                "use_metadata_date": r[9],
                "delicate_mode": r[10],
                "created_at": r[11],
                "source_path": r[12],
                "camera_name": r[13],
            })
        conn.close()
        return rows

    def get_session(self, session_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT id, project_id, name, shoot_date, status, destination_override,
                      folder_name, organization_type, duration_type, default_camera,
                      use_metadata_date, delicate_mode, created_at, source_path, camera_name
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
            "default_camera": r[9],
            "use_metadata_date": r[10],
            "delicate_mode": r[11],
            "created_at": r[12],
            "source_path": r[13],
            "camera_name": r[14],
        }

    def update_session_config(self, session_id: int, **kwargs):
        if not kwargs:
            return
        allowed = {"destination_override", "folder_name", "organization_type",
                   "duration_type", "default_camera", "use_metadata_date",
                   "delicate_mode", "name", "shoot_date", "status",
                   "source_path", "camera_name"}
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

    def dump_locations(self, project_id: int):
        conn = self.get_connection()
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
        conn.close()
        return rows

    def add_dump_location(self, project_id: int, path: str, label: str = None,
                          include_date: bool = True, include_camera: bool = True):
        conn = self.get_connection()
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
        conn.close()
        return lid

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
        cursor = conn.cursor()
        cursor.execute(f"UPDATE dump_locations SET {set_clause} WHERE id = ?", values)
        conn.commit()
        conn.close()

    def delete_dump_location(self, location_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM dump_locations WHERE id = ?', (location_id,))
        conn.commit()
        conn.close()

    def reorder_dump_locations(self, project_id: int, ordered_ids: list):
        conn = self.get_connection()
        cursor = conn.cursor()
        for idx, loc_id in enumerate(ordered_ids):
            cursor.execute(
                'UPDATE dump_locations SET order_index = ? WHERE id = ? AND project_id = ?',
                (idx, loc_id, project_id)
            )
        conn.commit()
        conn.close()

db = DatabaseManager()
