"""Harness de capturas offscreen de las 4 zonas de la UI (plan 01-01).

Genera 8 PNG en ``captures/``:
    zonaA_{estado-inicial,configurado}.png  - Ventana principal / dashboard
    zonaB_{estado-inicial,configurado}.png  - Selector de fuentes (SourcePickerDialog)
    zonaC_{estado-inicial,configurado}.png  - Asistente de proyecto (ProjectWizard)
    zonaD_{estado-inicial,configurado}.png  - Zona post-ingesta bajo la barra de progreso

Requisitos:
    - QT_QPA_PLATFORM=offscreen (sin pantalla)
    - Una sola instancia de QApplication
    - No escribe nada bajo app/, tests/ ni tools/ (la BD usa un temp dir)
    - Si una escena no puede renderizarse offscreen, se registra como
      "captura pendiente — <motivo>" y el script continúa (exit 0).
"""

import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Insertar la raíz del repo en sys.path para poder importar app.*
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import Qt
from PySide6.QtWidgets import QApplication

import app.ui.main_window as mw
import app.core.ingestor as ingestor_module
import app.core.metadata_engine as me_module
from app.core.db import DatabaseManager
from app.ui import theme
from app.ui.source_picker import SourcePickerDialog
from app.ui.project_wizard import ProjectWizard

OUT_DIR = os.path.join(_HERE, "captures")
MAX_WIDTH = 1920

pending = []  # (capture_name, motivo)


def _save(widget, name, rect=None):
    """Renderiza ``widget`` a PNG. Devuelve True o registra pendiente."""
    widget.show()
    app = QApplication.instance()
    for _ in range(3):
        app.processEvents()
    try:
        if rect is not None:
            pix = widget.grab(rect)
        else:
            pix = widget.grab()
        if pix.isNull() or pix.width() <= 0:
            raise RuntimeError("pixmap nulo tras grab()")
        if pix.width() > MAX_WIDTH:
            pix = pix.scaledToWidth(MAX_WIDTH, Qt.SmoothTransformation)
        os.makedirs(OUT_DIR, exist_ok=True)
        ok = pix.save(os.path.join(OUT_DIR, name), "PNG")
        if not ok:
            raise RuntimeError("save() devolvió False")
        print(f"CAPTURED {name} ({pix.width()}x{pix.height()})")
        return True
    except Exception as e:  # noqa: BLE001 - el harness nunca debe abortar
        pending.append((name, str(e)))
        print(f"PENDING {name}: {e}")
        return False


def _zonad_rect(window):
    """Rect de la zona post-ingesta: columna izquierda bajo la barra de progreso."""
    top_left = window.progress_bar.mapTo(window, QPoint(0, 0))
    bottom_right = window.chk_shutdown.mapTo(
        window, QPoint(window.chk_shutdown.width(), window.chk_shutdown.height()))
    right_x = window.source_list.mapTo(
        window, QPoint(window.source_list.width(), 0)).x() + 12
    return QRect(0, top_left.y(), right_x, bottom_right.y() - top_left.y() + 12)


def _setup_app():
    app = QApplication.instance() or QApplication([])
    app.setApplicationName("CosechaMedia")
    app.setOrganizationName("Audiovisual Production")
    theme.apply_theme(app)
    return app


def _make_window(tmp):
    """Crea MainWindow con una BD temporal limpia (patrón de tests/test_e2e.py)."""
    orig_db = mw.db
    orig_ing_db = ingestor_module.db
    orig_me_db = me_module.db
    orig_notif = mw.NotificationManager

    class StubNotif:
        def notify_ingest_complete(self, stats):
            pass

        def notify_ingest_stopped(self):
            pass

        def notify_ingest_failed(self, stats=None):
            pass

    db = DatabaseManager(db_path=os.path.join(tmp, "capture.db"))
    mw.db = db
    ingestor_module.db = db
    me_module.db = db
    mw.NotificationManager = StubNotif

    window = mw.MainWindow()
    window.resize(1200, 780)

    def _cleanup():
        try:
            window.close()
        except Exception:  # noqa: BLE001
            pass
        mw.db = orig_db
        ingestor_module.db = orig_ing_db
        me_module.db = orig_me_db
        mw.NotificationManager = orig_notif

    return window, db, _cleanup


def _seed_project(db, tmp):
    """Crea un proyecto + sesión + ubicación de volcado en la BD temporal."""
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO projects (name, root_path) VALUES ('Rodaje_Test', ?)",
        (os.path.join(tmp, "dest"),))
    pid = cursor.lastrowid
    conn.commit()
    conn.close()
    db.create_session(pid, "Sesión 1", "2026-08-15", "active",
                      os.path.join(tmp, "src"))
    db.add_dump_location(pid, os.path.join(tmp, "disk_a"), "Disco A")
    return pid


def scene_zona_a_estado_inicial(window):
    return _save(window, "zonaA_estado-inicial.png")


def scene_zona_a_configurado(window, db, tmp):
    pid = _seed_project(db, tmp)
    window.load_existing_projects()
    idx = window.project_combo.findData(pid)
    if idx >= 0:
        window.project_combo.setCurrentIndex(idx)
    window._refresh_source_list()
    window._refresh_sessions_combo()
    window.current_session_id = db.get_sessions(pid)[0]["id"]

    # Progreso / estado simulado
    window.progress_bar.setValue(40)
    window.ingest_status_label.setText("Copiando…")
    window.lbl_files_processed.setText("12")
    window.lbl_files_pending.setText("8")
    window.lbl_files_errors.setText("0")
    window.chk_generate_proxies.setChecked(True)
    window.proxy_resolution.setCurrentIndex(1)  # 1080p
    window.btn_start.setEnabled(False)
    window.btn_stop.setEnabled(True)

    # Filas de ejemplo en la tabla de archivos
    window.table.setRowCount(3)
    for r, (arch, cam, estado, prog, dest) in enumerate([
        ("clip_0001.mp4", "Cámara A", "Copiado", "100%", "Disco A"),
        ("clip_0002.MOV", "Cámara A", "Copiando…", "40%", "Disco A"),
        ("clip_0003.mp4", "Cámara B", "Pendiente", "—", "Disco B"),
    ]):
        for c, val in enumerate((arch, cam, estado, prog, dest)):
            from PySide6.QtWidgets import QTableWidgetItem
            window.table.setItem(r, c, QTableWidgetItem(val))

    return _save(window, "zonaA_configurado.png")


def scene_zona_b_estado_inicial():
    dlg = SourcePickerDialog(folders=(), senders=(), ftp_profiles=())
    return _save(dlg, "zonaB_estado-inicial.png")


def scene_zona_b_configurado():
    folders = [r"E:\DCIM\100EOS5D", r"D:\Rodaje\Clip1"]
    senders = [{"name": "Móvil de Ana", "used": True},
               {"name": "iPhone de Luis", "used": False}]
    ftp_profiles = [{"id": 1, "name": "Servidor FTP", "host": "192.168.1.50"}]
    dlg = SourcePickerDialog(folders=folders, senders=senders,
                             ftp_profiles=ftp_profiles)
    return _save(dlg, "zonaB_configurado.png")


def scene_zona_c_estado_inicial():
    wizard = ProjectWizard(on_finished_callback=lambda: None,
                           on_cancel_callback=lambda: None)
    wizard.resize(640, 560)
    return _save(wizard, "zonaC_estado-inicial.png")


def scene_zona_c_configurado():
    wizard = ProjectWizard(on_finished_callback=lambda: None,
                           on_cancel_callback=lambda: None)
    wizard.resize(640, 560)
    wizard.name_input.setText("Rodaje_Cine_01")
    wizard.desc_input.setText("Cortometraje: capítulo 3")
    wizard.dest_input.setText(r"H:\Produccion\Proyectos")
    wizard.radio_multiple_days.setChecked(True)
    wizard.org_combo.setCurrentIndex(1)  # Fecha primero
    wizard.chk_use_metadata_date.setChecked(True)
    return _save(wizard, "zonaC_configurado.png")


def scene_zona_d_estado_inicial(window):
    return _save(window, "zonaD_estado-inicial.png", _zonad_rect(window))


def scene_zona_d_configurado(window, db, tmp):
    pid = _seed_project(db, tmp)
    window.load_existing_projects()
    idx = window.project_combo.findData(pid)
    if idx >= 0:
        window.project_combo.setCurrentIndex(idx)
    window._refresh_source_list()
    window._refresh_sessions_combo()

    window.progress_bar.setValue(40)
    window.chk_format_sources.setChecked(True)
    window.combo_format_mode.setCurrentIndex(1)  # Completo
    window.chk_shutdown.setChecked(True)
    return _save(window, "zonaD_configurado.png", _zonad_rect(window))


def main():
    tmp = tempfile.mkdtemp(prefix="cm_capture_")
    _setup_app()
    try:
        window, db, cleanup = _make_window(tmp)
        try:
            scene_zona_a_estado_inicial(window)
            scene_zona_a_configurado(window, db, tmp)
            scene_zona_b_estado_inicial()
            scene_zona_b_configurado()
            scene_zona_c_estado_inicial()
            scene_zona_c_configurado()
            scene_zona_d_estado_inicial(window)
            scene_zona_d_configurado(window, db, tmp)
        finally:
            cleanup()
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)

    if pending:
        print("PENDIENTES:")
        for name, motivo in pending:
            print(f"  {name}: {motivo}")
    print(f"OK - {8 - len(pending)}/8 capturas en {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
