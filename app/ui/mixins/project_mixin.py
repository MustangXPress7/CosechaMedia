import os
import shutil
import sys
import json
from datetime import datetime
from PySide6.QtWidgets import QMessageBox, QInputDialog, QDialog
from PySide6.QtCore import Qt, QSettings
from app.core.db import db, WIFI_DEVICE_ID
from app.core.sd_reader import sd_reader
from app.core import translator
from app.ui import theme
from app.ui.about_dialog import AboutDialog


class ProjectMixin:
    """Métodos del ciclo de vida del proyecto extraídos de MainWindow (quick 260906-project-mixin)."""

    def load_existing_projects(self):
        previous_id = self.current_project_id
        previous_session_id = self.current_session_id
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        self.project_combo.addItem(self.tr("-- Selecciona un proyecto --"), None)

        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT id, name, root_path FROM projects ORDER BY id ASC')
            for row in cursor.fetchall():
                label = f"#{row['id']} - {row['name']}"
                self.project_combo.addItem(label, row['id'])
            conn.close()
        except Exception as e:
            QMessageBox.critical(self, self.tr("Error"), self.tr("No se pudieron cargar los proyectos: %1").arg(str(e)))
            return
        finally:
            self.project_combo.blockSignals(False)

        if previous_id is not None:
            idx = self.project_combo.findData(previous_id)
            if idx >= 0:
                self.project_combo.setCurrentIndex(idx)
            # Restaurar sesión activa si sigue existiendo en el proyecto recargado
            if previous_session_id is not None:
                # _load_project se llamará via on_project_selected y luego _refresh_sessions_combo
                # Guardamos el session_id deseado para restaurarlo después de poblar el combo
                self._restore_session_id = previous_session_id

    def on_project_selected(self, index):
        self._reset_wifi_ingestors()
        # Limpieza COM + detención de timers/ingestors al cambiar de proyecto
        # (D-25): igual que al borrar proyecto, para no dejar hilos con
        # referencias COM corruptas ni stagings en curso del proyecto previo.
        self._reset_mtp_thread_local()
        self._reset_ingestors()
        project_id = self.project_combo.itemData(index)
        if project_id is None:
            self.current_project_id = None
            self.dest_root = ""
            self.current_session_id = None
            self.project_path_label.setText("")
            # Sin proyecto no se muestra la fila de descripción.
            self._project_description = ""
            self.project_description_label.setText("")
            self.project_description_label.setVisible(False)
            self.btn_edit_description.setVisible(False)
            self._set_status_color("border_strong")
            self.status_text.setText(self.tr("Listo"))
            self.btn_delete_project.setEnabled(False)
            self.btn_rename_project.setEnabled(False)
            self.btn_duplicate_project.setEnabled(False)
        else:
            self._load_project(project_id)
            self.btn_delete_project.setEnabled(True)
            self.btn_rename_project.setEnabled(True)
            self.btn_duplicate_project.setEnabled(True)
        self.update_start_button_state()

    def _load_project(self, project_id):
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT name, root_path, description, organization_type, duration_type, default_dispositivo, '
            'folder_name, delicate_mode, use_metadata_date, generate_proxies, proxy_resolution, '
            'camera_detection_mode, camera_detection_timeout, '
            'date_mode, manual_date, camera_date_overrides '
            'FROM projects WHERE id = ?',
            (project_id,)
        )
        res = cursor.fetchone()
        conn.close()

        if not res:
            QMessageBox.warning(self, self.tr("Aviso"), self.tr("Proyecto #%1 no encontrado.").arg(project_id))
            return

        self.current_project_id = project_id
        self.current_session_id = None
        self.dest_root = res["root_path"] or ""
        self.project_organization_type = res["organization_type"] if res["organization_type"] is not None else 0
        self.project_duration_type = res["duration_type"] if res["duration_type"] is not None else 1
        self.project_default_dispositivo = res["default_dispositivo"] or ""
        self.project_folder_name = res["folder_name"] or "Footage"
        self.project_delicate_mode = bool(res["delicate_mode"]) if res["delicate_mode"] is not None else False
        self.project_use_metadata_date = bool(res["use_metadata_date"]) if res["use_metadata_date"] is not None else True
        self.project_generate_proxies = bool(res["generate_proxies"]) if res["generate_proxies"] is not None else False
        self.project_proxy_resolution = res["proxy_resolution"] or "720p"
        self.project_camera_detection_mode = res["camera_detection_mode"] or "auto"
        self.project_camera_detection_timeout = res["camera_detection_timeout"] if res["camera_detection_timeout"] is not None else 5
        self.project_date_mode = res["date_mode"] or "auto"
        self.project_manual_date = res["manual_date"]
        self.project_camera_date_overrides = res["camera_date_overrides"] or "{}"

        name = res["name"]
        root = self.dest_root or self.tr("(sin ruta)")
        self.project_path_label.setText(f"→ {root}")
        self._set_project_description(res["description"] or "")
        self._set_status_color("success")
        self.status_text.setText(self.tr("Proyecto: %1").arg(name))

        self._populate_source_paths_from_sessions()
        self._refresh_sessions_combo()
        self._refresh_source_list()

    def _set_project_description(self, text):
        """Muestra la descripción del proyecto bajo la header bar (R-10/B-03)."""
        self._project_description = text or ""
        if not self._project_description:
            self.project_description_label.setText(
                self.tr("Descripción del proyecto: (sin descripción)"))
            self.project_description_label.setToolTip("")
            self.project_description_label.setVisible(True)
            self.btn_edit_description.setVisible(True)
            return
        full = self.tr("Descripción del proyecto") + ": " + self._project_description
        self.project_description_label.setText(full)
        self.project_description_label.setToolTip(full)
        self.project_description_label.setVisible(True)
        self.btn_edit_description.setVisible(True)

    def _edit_project_description(self):
        """Edita la descripción del proyecto en línea (B-03)."""
        if self.current_project_id is None:
            return
        current = getattr(self, "_project_description", "") or ""
        new_desc, ok = QInputDialog.getText(
            self, self.tr("Descripción del proyecto"),
            self.tr("Descripción (opcional):"), text=current)
        if not ok:
            return
        db.update_project_description(self.current_project_id, new_desc.strip())
        self._set_project_description(new_desc.strip())
        self.ingest_status_label.setText(self.tr("Descripción actualizada."))

    def _show_create_project(self):
        # Import local (patrón del archivo); el wizard es QWidget, no QDialog:
        # se muestra con show() + WindowModality, nunca exec().
        from app.ui.project_wizard import ProjectWizard
        wizard = ProjectWizard(self._on_project_wizard_finished,
                               on_cancel_callback=lambda: self._close_project_wizard(wizard))
        self._project_wizard = wizard  # referencia persistente (anti-GC)
        wizard.setWindowModality(Qt.ApplicationModal)
        wizard.show()

    def _on_project_wizard_finished(self, project_id):
        """Callback del ProjectWizard: crea la sesión inicial y activa el proyecto."""
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM projects WHERE id = ?', (project_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return
        name = row['name']

        db.create_session(project_id, f"Sesión 1 - {name}", datetime.now().strftime("%Y-%m-%d"), "active")

        self.load_existing_projects()
        idx = self.project_combo.findData(project_id)
        if idx >= 0:
            self.project_combo.setCurrentIndex(idx)
        self.ingest_status_label.setText(self.tr("Proyecto #%1 creado con sesión inicial.").arg(project_id))
        self.btn_delete_project.setEnabled(True)
        self.btn_rename_project.setEnabled(True)
        self.btn_duplicate_project.setEnabled(True)
        self.update_start_button_state()
        self._close_project_wizard(self._project_wizard)

    def _close_project_wizard(self, wizard):
        """Cierra y libera el wizard (usado por on_finished y on_cancel)."""
        if wizard is not None:
            wizard.close()
            wizard.deleteLater()
        self._project_wizard = None

    def _rename_current_project(self):
        if self.current_project_id is None:
            return
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM projects WHERE id = ?', (self.current_project_id,))
        res = cursor.fetchone()
        conn.close()
        current_name = res["name"] if res else ""
        new_name, ok = QInputDialog.getText(
            self, self.tr("Renombrar proyecto"),
            self.tr("Nuevo nombre del proyecto:"),
            text=current_name
        )
        if not ok or not new_name.strip() or new_name.strip() == current_name:
            return
        new_name = new_name.strip()
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE projects SET name = ? WHERE id = ?', (new_name, self.current_project_id))
            conn.commit()
            conn.close()
            self.load_existing_projects()
            self.project_path_label.setText(f"→ {self.dest_root or self.tr('(sin ruta)')}")
            self.status_text.setText(self.tr("Proyecto: %1").arg(new_name))
            self.ingest_status_label.setText(self.tr("Proyecto renombrado a '%1'.").arg(new_name))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Error"), self.tr("No se pudo renombrar el proyecto: %1").arg(str(e)))

    def _duplicate_current_project(self):
        if self.current_project_id is None:
            return
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT name, root_path, description, organization_type, duration_type, '
            'default_dispositivo, folder_name, delicate_mode, use_metadata_date '
            'FROM projects WHERE id = ?',
            (self.current_project_id,)
        )
        src = cursor.fetchone()
        if not src:
            conn.close()
            return
        default_new_name = f"{src['name']} (copia)"
        new_name, ok = QInputDialog.getText(
            self, self.tr("Duplicar proyecto"),
            self.tr("Nombre del proyecto duplicado:"),
            text=default_new_name
        )
        if not ok or not new_name.strip():
            conn.close()
            return
        new_name = new_name.strip()
        try:
            cursor.execute(
                'INSERT INTO projects '
                '(name, root_path, description, organization_type, duration_type, '
                'default_dispositivo, folder_name, delicate_mode, use_metadata_date) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (
                    new_name, src["root_path"], src["description"],
                    src["organization_type"], src["duration_type"],
                    src["default_dispositivo"], src["folder_name"],
                    src["delicate_mode"], src["use_metadata_date"],
                )
            )
            new_id = cursor.lastrowid
            cursor.execute(
                'INSERT INTO sessions (project_id, name, shoot_date, status, source_path, nombre_dispositivo, '
                'destination_override, delicate_mode) '
                'SELECT ?, name, shoot_date, status, source_path, nombre_dispositivo, '
                'destination_override, delicate_mode FROM sessions WHERE project_id = ?',
                (new_id, self.current_project_id)
            )
            conn.commit()
            conn.close()
            self.load_existing_projects()
            idx = self.project_combo.findData(new_id)
            if idx >= 0:
                self.project_combo.setCurrentIndex(idx)
            self.ingest_status_label.setText(self.tr("Proyecto duplicado como '%1' (ID %2).").arg(new_name).arg(new_id))
        except Exception as e:
            conn.close()
            QMessageBox.critical(self, self.tr("Error"), self.tr("No se pudo duplicar el proyecto: %1").arg(str(e)))

    def _save_project_root(self, new_root):
        if self.current_project_id is None:
            return
        try:
            os.makedirs(new_root, exist_ok=True)
            new_root = os.path.abspath(new_root)
            old_root = os.path.abspath(self.dest_root) if self.dest_root else ""
            if old_root and old_root != new_root:
                self._handle_completed_files_on_root_change(old_root, new_root)
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE projects SET root_path = ? WHERE id = ?',
                (new_root, self.current_project_id)
            )
            conn.commit()
            conn.close()
            self.dest_root = new_root
            self.project_path_label.setText(f"→ {self.dest_root}")
            self.ingest_status_label.setText(self.tr("Destino maestro actualizado: %1").arg(self.dest_root))
            db.save_recent_path(self.dest_root, "dest")
        except Exception as e:
            QMessageBox.critical(self, self.tr("Error"), self.tr("No se pudo actualizar el destino: %1").arg(str(e)))
            return
        sessions = db.get_sessions(self.current_project_id)
        if not sessions:
            from datetime import datetime
            sid = db.create_session(
                self.current_project_id,
                self.tr("Sesión 1"),
                datetime.now().strftime("%Y-%m-%d"), "active",
                source_path="")
            self.current_session_id = sid
        self._refresh_sessions_combo()

    def _completed_files_under_root(self, old_root):
        """Archivos 'completed' del proyecto cuyo destino está bajo ``old_root``."""
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT id, dest_path FROM files
               WHERE session_id IN (SELECT id FROM sessions WHERE project_id = ?)
                 AND status = 'completed' ''',
            (self.current_project_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        old = old_root.replace("\\", "/").rstrip("/") + "/"
        return [r for r in rows
                if r["dest_path"] and r["dest_path"].replace("\\", "/").startswith(old)]

    def _handle_completed_files_on_root_change(self, old_root, new_root):
        """Pregunta qué hacer con los archivos completados de la ubicación
        anterior al mover la carpeta maestra: moverlos, borrarlos de la tabla
        de ingesta, o dejarlos como están."""
        affected = self._completed_files_under_root(old_root)
        if not affected:
            return
        msg = QMessageBox(self)
        msg.setWindowTitle(self.tr("Cambiar carpeta maestra"))
        msg.setText(
            self.tr("La carpeta maestra tiene %1 archivo(s) completado(s) en "
                    "la ubicación anterior (%2).").arg(len(affected)).arg(old_root))
        msg.setInformativeText(self.tr("¿Qué quieres hacer con ellos?"))
        btn_move = msg.addButton(
            self.tr("Mover a la nueva ubicación"), QMessageBox.ActionRole)
        btn_delete = msg.addButton(
            self.tr("Eliminar de la tabla de ingesta"), QMessageBox.DestructiveRole)
        btn_leave = msg.addButton(
            self.tr("Dejar como están"), QMessageBox.ActionRole)
        msg.setDefaultButton(btn_move)
        msg.exec()
        clicked = msg.clickedButton()
        if clicked == btn_move:
            moved, failed = self._move_completed_files(affected, old_root, new_root)
            self.ingest_status_label.setText(
                self.tr("Archivos movidos a la nueva carpeta maestra: %1 "
                        "(%2 con errores).").arg(moved).arg(failed))
        elif clicked == btn_delete:
            self._delete_completed_file_records(affected)
            self.ingest_status_label.setText(
                self.tr("Archivos completados eliminados de la tabla de "
                        "ingesta: %1.").arg(len(affected)))

    def _move_completed_files(self, rows, old_root, new_root):
        """Mueve físicamente los archivos manteniendo la estructura relativa y
        actualiza sus rutas en la tabla ``files``."""
        import shutil
        moved = 0
        failed = 0
        old = old_root.replace("\\", "/").rstrip("/") + "/"
        conn = db.get_connection()
        cursor = conn.cursor()
        for r in rows:
            dest = r["dest_path"]
            npath = dest.replace("\\", "/")
            if not npath.startswith(old):
                continue
            rel = npath[len(old):]
            new_dest = os.path.join(new_root, *rel.split("/"))
            try:
                if not os.path.exists(dest):
                    continue
                os.makedirs(os.path.dirname(new_dest), exist_ok=True)
                if os.path.exists(new_dest):
                    base, ext = os.path.splitext(new_dest)
                    n = 1
                    alt = f"{base} ({n}){ext}"
                    while os.path.exists(alt):
                        n += 1
                        alt = f"{base} ({n}){ext}"
                    new_dest = alt
                shutil.move(dest, new_dest)
                cursor.execute(
                    "UPDATE files SET dest_path = ? WHERE id = ?",
                    (new_dest, r["id"]))
                moved += 1
            except Exception as e:
                print(f"Error moviendo {dest}: {e}")
                failed += 1
        conn.commit()
        conn.close()
        self._prune_empty_dirs(old_root)
        return moved, failed

    def _delete_completed_file_records(self, rows):
        conn = db.get_connection()
        cursor = conn.cursor()
        for r in rows:
            cursor.execute("DELETE FROM files WHERE id = ?", (r["id"],))
        conn.commit()
        conn.close()

    def _prune_empty_dirs(self, root):
        """Elimina los directorios vacíos que queden bajo ``root``."""
        if not root or not os.path.isdir(root):
            return
        for base, dirs, files in os.walk(root, topdown=False):
            try:
                os.rmdir(base)
            except OSError:
                pass

    def open_data_folder(self):
        data_dir = os.path.dirname(db.db_path)
        if sys.platform.startswith("win"):
            os.startfile(data_dir)
        elif sys.platform == "darwin":
            os.system(f'open "{data_dir}"')
        else:
            os.system(f'xdg-open "{data_dir}"')

    def delete_current_project(self):
        if self.current_project_id is None:
            QMessageBox.information(self, self.tr("Sin proyecto"), self.tr("Selecciona un proyecto para eliminar."))
            return

        reply = QMessageBox.question(
            self,
            self.tr("Confirmar eliminación"),
            self.tr("¿Eliminar el proyecto #%1 y todos sus datos?\nEsta acción no se puede deshacer.")
            .arg(self.current_project_id),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.No:
            return

        self._reset_mtp_thread_local()
        self._reset_ingestors()
        self._reset_wifi_ingestors()

        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            # Recoger seriales de sd_cards de las rutas de origen que se borran
            cursor.execute(
                'SELECT source_path FROM sessions WHERE project_id = ?',
                (self.current_project_id,))
            sessions_data = cursor.fetchall()
            volume_serials = set()
            for row in sessions_data:
                sp = row[0]
                if sp:
                    serial = sd_reader.get_volume_serial(sp)
                    if serial:
                        volume_serials.add(serial)

            cursor.execute('DELETE FROM dump_locations WHERE project_id = ?', (self.current_project_id,))
            cursor.execute('DELETE FROM files WHERE session_id IN (SELECT id FROM sessions WHERE project_id = ?)', (self.current_project_id,))
            cursor.execute('DELETE FROM sessions WHERE project_id = ?', (self.current_project_id,))
            cursor.execute('DELETE FROM projects WHERE id = ?', (self.current_project_id,))

            # B-17/D-12: device_settings NO se borra al eliminar el proyecto.
            # Los dispositivos guardados son globales y deben persistir entre
            # proyectos (y visibles en «Añadir origen»). El único camino de
            # borrado es la papelera del diálogo (db.delete_device).
            for serial in volume_serials:
                cursor.execute(
                    'SELECT COUNT(*) FROM sessions WHERE source_path IS NOT NULL AND project_id != ?',
                    (self.current_project_id,))
                if cursor.fetchone()[0] == 0:
                    cursor.execute('DELETE FROM sd_cards WHERE serial = ?', (serial,))

            conn.commit()
            conn.close()

            self.current_project_id = None
            self.current_session_id = None
            self.dest_root = ""
            self.project_path_label.setText("")
            self.btn_delete_project.setEnabled(False)
            self.btn_rename_project.setEnabled(False)
            self.btn_duplicate_project.setEnabled(False)
            self.load_existing_projects()
            self.update_start_button_state()
            QMessageBox.information(self, self.tr("Eliminado"), self.tr("Proyecto eliminado correctamente."))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Error"), self.tr("Error al eliminar el proyecto: %1").arg(str(e)))

    def delete_all_projects(self):
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM projects')
        count = cursor.fetchone()[0]
        conn.close()

        if count == 0:
            QMessageBox.information(self, self.tr("Sin proyectos"), self.tr("No hay proyectos para eliminar."))
            return

        reply = QMessageBox.question(
            self,
            self.tr("Eliminar todos los proyectos"),
            self.tr("¿Eliminar los %1 proyectos y todos sus datos?\nEsta acción no se puede deshacer.").arg(count),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.No:
            return

        self._reset_mtp_thread_local()
        self._reset_ingestors()
        self._reset_wifi_ingestors()

        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM dump_locations')
            cursor.execute('DELETE FROM files')
            cursor.execute('DELETE FROM sessions')
            cursor.execute('DELETE FROM projects')
            cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('projects', 'sessions', 'files', 'dump_locations')")
            conn.commit()
            conn.close()

            self.current_project_id = None
            self.current_session_id = None
            self.dest_root = ""
            self.project_path_label.setText("")
            self.btn_delete_project.setEnabled(False)
            self.btn_rename_project.setEnabled(False)
            self.btn_duplicate_project.setEnabled(False)
            self.load_existing_projects()
            self.update_start_button_state()
            QMessageBox.information(self, self.tr("Eliminados"), self.tr("Todos los proyectos han sido eliminados."))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Error"), self.tr("Error al eliminar los proyectos: %1").arg(str(e)))
            return

        self._create_default_project()

    def _create_default_project(self):
        """Crea un proyecto por defecto para que la app sea usable al instante."""
        from datetime import datetime
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO projects (name, root_path, description) VALUES (?, ?, ?)',
                (self.tr("Proyecto por defecto"), "", self.tr("Proyecto creado automáticamente"))
            )
            project_id = cursor.lastrowid
            conn.commit()
            conn.close()

            db.create_session(project_id, self.tr("Sesión 1"), datetime.now().strftime("%Y-%m-%d"), "active")

            self.load_existing_projects()
            idx = self.project_combo.findData(project_id)
            if idx >= 0:
                self.project_combo.setCurrentIndex(idx)
            self.ingest_status_label.setText(self.tr("Proyecto por defecto creado con sesión inicial."))
            self.btn_delete_project.setEnabled(True)
            self.btn_rename_project.setEnabled(True)
            self.btn_duplicate_project.setEnabled(True)
            self.update_start_button_state()
        except Exception as e:
            QMessageBox.critical(self, self.tr("Error"), self.tr("No se pudo crear el proyecto por defecto: %1").arg(str(e)))

    def show_about(self):
        AboutDialog(self).exec()