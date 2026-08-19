import sys
import os
import json
import time
from datetime import datetime
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QLineEdit, QProgressBar, QTableWidget,
                             QTableWidgetItem, QHeaderView, QFrame, QStackedWidget, QDateEdit,
                             QComboBox, QMessageBox, QFileDialog, QMenuBar, QMenu, QCheckBox,
                             QGroupBox, QGridLayout, QSplashScreen, QSystemTrayIcon,
                             QListWidget, QListWidgetItem, QInputDialog, QFormLayout, QDialog,
                             QTextEdit, QSpinBox, QSizePolicy, QSplitter)
from PySide6.QtGui import QAction, QActionGroup, QIcon, QFont, QColor, QPixmap, QPainter
from PySide6.QtCore import Qt, QThread, QObject, Signal, QDate, QTimer, QSize, QPropertyAnimation, QSettings, QByteArray
from app.core.ingestor import Ingestor, DumpTarget
from app.core.watcher import FileSystemWatcher
from app.core.db import db, WIFI_DEVICE_ID
from app.core.notifications import NotificationManager
from app.core.sd_reader import sd_reader
from app.core.ffmpeg_utils import ffmpeg
from app.core.utils import create_folder_structure, get_mounted_drives, is_removable_drive, resource_path
from app.core.metadata_engine import metadata_engine
from app.core import translator
from app.core import updater
from app.core.translator import QtString
from app.ui import theme
from app.ui import icons
from app.ui.about_dialog import AboutDialog
from app.ui.wheat_field import paint_wheat_field
import app.ui.wheat_field as wheat_field
from app.core import ftp, mtp
from app.core import shoot_inbox as inboxmod
from app.core.ftp import FtpBackend
from app.core.metadata_engine import _is_system_entry
from app.ui.ftp_picker import FtpPickerDialog
from app.ui.selective_dump import SelectiveDumpAssistant, content_summary
from app.ui.source_picker import SourcePickerDialog
from app.ui.wifi_panel import SenderEditDialog, ShootInboxPanel

ORG_TYPE_MAP = {
    0: "camera_first",
    1: "date_first",
    2: "camera_only",
    3: "flat",
}

def _format_drive(path: str, quick: bool = True):
    if sys.platform != "win32":
        raise RuntimeError(translator.tr("El formateo de tarjetas solo está disponible en Windows."))
    if len(path) >= 2 and path[1] == ":":
        drive = path[:2]
        cmd = f"format {drive} /FS:exFAT /Q" if quick else f"format {drive} /FS:exFAT"
        import subprocess
        subprocess.run(
            ["cmd", "/c", f"echo S | {cmd}"],
            shell=False,
            check=True,
            timeout=600,
        )
    else:
        raise RuntimeError(translator.tr("Solo se admiten letras de unidad de Windows en este momento."))

def _format_sources_worker(progress, paths, quick):
    results = []
    for i, path in enumerate(paths, start=1):
        progress.emit(translator.tr("Formateando %1 (%2/%3)...").arg(path).arg(i).arg(len(paths)))
        try:
            _format_drive(path, quick=quick)
            results.append((path, True, ""))
        except Exception as e:
            results.append((path, False, str(e)))
    return results

def _generate_proxies_worker(progress, jobs, height):
    count = 0
    for i, (path, root) in enumerate(jobs, start=1):
        proxy_dir = os.path.join(root, "Proxies")
        os.makedirs(proxy_dir, exist_ok=True)
        progress.emit(translator.tr("Proxy %1/%2: %3").arg(i).arg(len(jobs)).arg(os.path.basename(path)))
        if ffmpeg.create_proxy(path, proxy_dir, height=height):
            count += 1
    return count

def _reorganize_worker(progress, ingestors):
    for i, ing in enumerate(ingestors, start=1):
        progress.emit(translator.tr("Reorganizando ingesta %1/%2...").arg(i).arg(len(ingestors)))
        ing.reorganize_by_metadata()
    return True

class _StageWorker(QObject):
    """Staging incremental de una carpeta de dispositivo MTP en QThread."""
    progress = Signal(str)
    done = Signal(bool, object)

    def __init__(self, backend, device_id, device_folder):
        super().__init__()
        self._backend = backend
        self._device_id = device_id
        self._device_folder = device_folder
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        try:
            def on_progress(name, current, total):
                self.progress.emit(
                    translator.tr("Sincronizando %1 (%2/%3)…").arg(name).arg(current).arg(total)
                )
            result = self._backend.stage(
                self._device_id,
                self._device_folder,
                on_progress=on_progress,
                cancel=lambda: self._cancel,
            )
            self.done.emit(True, result)
        except Exception as e:
            self.done.emit(False, str(e))

class DashboardBackground(QWidget):
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(theme.tinted_bg()))
        paint_wheat_field(painter, self.width(), self.height(), theme.get_theme(), theme.get_accent())
        painter.end()

class _TaskWorker(QObject):
    """Ejecuta una función en un QThread y notifica por señales Qt (cola segura)."""
    progress = Signal(str)
    finished = Signal(bool, object)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            result = self._fn(self.progress, *self._args, **self._kwargs)
            self.finished.emit(True, result)
        except Exception as e:
            print(f"Background task error: {e}")
            self.finished.emit(False, e)

class MainWindow(QMainWindow):
    def tr(self, text, *args, **kwargs):
        return QtString(super().tr(text, *args, **kwargs))

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CosechaMedia")
        self.setMinimumSize(800, 500)
        self.resize(1200, 750)

        logo_path = resource_path(os.path.join("app", "ui", "logo.png"))
        if os.path.exists(logo_path):
            self.setWindowIcon(QIcon(logo_path))

        self.current_project_id = None
        self.dest_root = ""
        self.project_organization_type = 0
        self.project_duration_type = 1
        self.project_default_camera = ""
        self.project_folder_name = "Footage"
        self.project_delicate_mode = False
        self.project_use_metadata_date = True
        self.project_generate_proxies = False
        self.project_proxy_resolution = "720p"
        self.project_date = QDate.currentDate()
        self.current_session_id = None
        self._ingestors = []
        self._ingest_completed = set()
        self.watchers = []
        self._file_row_map = {}
        self.project_camera_detection_mode = "auto"
        self.project_camera_detection_timeout = 5
        self._source_paths = []
        self._processed_count = 0
        self._total_files = 0
        self._source_paths = []
        self._unknown_cameras = set()
        self._ingested_videos = []
        self._background_tasks = []
        self._poll_in_progress = False

        self.notification_manager = NotificationManager()

        self._wifi_server = None
        self._wifi_panel = None
        self._wifi_ingestors = {}  # session_id -> Ingestor

        self.build_menu()
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.setup_views()

        settings = QSettings("Audiovisual Production", "CosechaMedia")
        stored_mode = settings.value("camera_detection_mode", "manual")
        self.project_camera_detection_mode = stored_mode if stored_mode in ("manual", "auto") else "manual"
        self.project_camera_detection_timeout = settings.value("camera_detection_timeout", 5, type=int)
        self._update_detect_button_state()
        geometry = settings.value("geometry", type=QByteArray)
        if geometry:
            self.restoreGeometry(geometry)
        state = settings.value("windowState", type=QByteArray)
        if state:
            self.restoreState(state)

        if getattr(sys, "frozen", False) and settings.value("checkUpdatesOnStart", True, type=bool):
            QTimer.singleShot(3000, self._run_startup_update_check)

        self._last_device_sync = {}
        self._sync_timer = QTimer(self)
        self._sync_timer.setInterval(5000)
        self._sync_timer.timeout.connect(self._auto_sync_check)
        self._sync_timer.start()

    def _auto_sync_check(self):
        """Auto-sync MTP/FTP: detecta dispositivos en hilo de fondo para
        no bloquear la UI."""
        if getattr(self, "_stage_thread", None) and self._stage_thread.isRunning():
            return
        if self.current_project_id is None:
            return
        sessions = [s for s in db.get_sessions(self.current_project_id) if s.get("device_id")]
        if not sessions:
            return
        if self._poll_in_progress:
            return
        self._poll_in_progress = True

        def _probe_devices(progress_signal):
            mtp_connected = set()
            try:
                mtp_connected = {d.device_id for d in mtp.WpdBackend().list_devices()}
            except Exception:
                pass
            ftp_backend = FtpBackend()
            ftp_reachable = set()
            for s in sessions:
                did = s["device_id"]
                if str(did).startswith("ftp:"):
                    try:
                        if ftp_backend.is_reachable(did):
                            ftp_reachable.add(did)
                    except Exception:
                        pass
            return {"mtp_connected": mtp_connected, "ftp_reachable": ftp_reachable,
                    "ftp_backend": ftp_backend}

        def _on_poll_done(ok, result):
            self._poll_in_progress = False
            if not ok:
                return
            self._process_device_poll(result, sessions)

        self._run_background(_probe_devices, _on_poll_done)

    def _process_device_poll(self, result, sessions):
        """Procesa los resultados de la detección en el hilo UI."""
        now = time.time()
        mtp_connected = result["mtp_connected"]
        ftp_reachable = result["ftp_reachable"]
        ftp_backend = result["ftp_backend"]
        for s in sessions:
            did = s["device_id"]
            is_ftp = str(did).startswith("ftp:")
            if is_ftp:
                if did not in ftp_reachable:
                    continue
            elif did not in mtp_connected:
                continue
            if now - self._last_device_sync.get(did, 0) < 60:
                continue
            self._last_device_sync[did] = now
            cache_dir = s.get("source_path") or mtp.device_cache_dir(did, s.get("device_folder") or "")
            try:
                os.makedirs(cache_dir, exist_ok=True)
            except OSError:
                continue
            self._stage_device_in_background(
                did, s.get("device_folder") or "", s["id"], cache_dir,
                backend=ftp_backend if is_ftp else None, silent=is_ftp)
            return

    def setup_views(self):
        self.dashboard_view = DashboardBackground()
        self.dashboard_view.setObjectName("DashboardView")
        dash_layout = QVBoxLayout(self.dashboard_view)
        dash_layout.setContentsMargins(0, 0, 0, 0)
        dash_layout.setSpacing(0)

        # === HEADER BAR ===
        header_bar = QWidget()
        header_bar.setObjectName("HeaderBar")
        hb = QHBoxLayout(header_bar)
        hb.setContentsMargins(10, 3, 10, 3)
        hb.setSpacing(6)

        app_label = QLabel("CosechaMedia")
        app_label.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {theme.color('accent')};")
        hb.addWidget(app_label)
        hb.addSpacing(6)

        hb.addWidget(QLabel(self.tr("Proyecto:")))
        self.project_combo = QComboBox()
        self.project_combo.setMinimumWidth(160)
        self.project_combo.currentIndexChanged.connect(self.on_project_selected)
        hb.addWidget(self.project_combo)

        for btn, icon_name, tip in [
            ("btn_refresh_projects", "refresh", self.tr("Actualizar proyectos")),
            ("btn_new_project", "plus", self.tr("Nuevo proyecto")),
            ("btn_delete_project", "x", self.tr("Eliminar proyecto…")),
            ("btn_rename_project", "pencil", self.tr("Renombrar proyecto")),
            ("btn_duplicate_project", "copy", self.tr("Duplicar proyecto")),
            ("btn_browse_root", "folder", self.tr("Cambiar ruta maestra del proyecto")),
        ]:
            b = QPushButton()
            b.setObjectName("IconButton")
            b.setFixedSize(28, 28)
            b.setToolTip(tip)
            icons.apply(b, icon_name, size=18)
            b.clicked.connect(getattr(self, {
                "btn_refresh_projects": "load_existing_projects",
                "btn_new_project": "_show_create_project",
                "btn_delete_project": "delete_current_project",
                "btn_rename_project": "_rename_current_project",
                "btn_duplicate_project": "_duplicate_current_project",
                "btn_browse_root": "select_dest_path",
            }[btn]))
            setattr(self, btn, b)
            hb.addWidget(b)
        self.btn_delete_project.setEnabled(False)
        self.btn_rename_project.setEnabled(False)
        self.btn_duplicate_project.setEnabled(False)

        hb.addSpacing(6)

        self.project_path_label = QLabel("")
        self.project_path_label.setStyleSheet(f"color: {theme.color('accent')}; font-size: 11px; font-weight: bold;")
        self.project_path_label.setMaximumWidth(420)
        self.project_path_label.setSizePolicy(
            QSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred))
        hb.addWidget(self.project_path_label)

        hb.addStretch()

        for btn, icon_name, tip, cb in [
            ("btn_show_metadata", "gear", self.tr("Configuración"), "_show_metadata_dialog"),
        ]:
            b = QPushButton()
            b.setObjectName("IconButton")
            b.setFixedSize(28, 28)
            b.setToolTip(tip)
            icons.apply(b, icon_name, size=18)
            b.clicked.connect(getattr(self, cb))
            setattr(self, btn, b)
            hb.addWidget(b)

        hb.addSpacing(4)

        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(8, 8)
        self._set_status_color("border_strong")
        hb.addWidget(self.status_indicator)

        self.status_text = QLabel(self.tr("Listo"))
        self.status_text.setStyleSheet(f"color: {theme.color('text_secondary')}; font-size: 10px;")
        hb.addWidget(self.status_text)

        dash_layout.addWidget(header_bar)

        # --- Project description (R-10) ---
        desc_box = QGroupBox(self.tr("Descripción"))
        desc_box.setObjectName("DescriptionBox")
        desc_box_layout = QHBoxLayout(desc_box)
        desc_box_layout.setContentsMargins(8, 6, 8, 6)
        desc_box_layout.setSpacing(6)
        self.project_description_label = QLabel("")
        self.project_description_label.setStyleSheet(
            f"color: {theme.color('text_secondary')}; font-size: 11px;")
        self.project_description_label.setWordWrap(True)
        self.project_description_label.setSizePolicy(
            QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred))
        desc_box_layout.addWidget(self.project_description_label, 1)

        self.btn_edit_description = QPushButton()
        self.btn_edit_description.setObjectName("IconButton")
        self.btn_edit_description.setFixedSize(24, 24)
        self.btn_edit_description.setToolTip(self.tr("Editar descripción del proyecto"))
        icons.apply(self.btn_edit_description, "pencil", size=16)
        self.btn_edit_description.clicked.connect(self._edit_project_description)
        desc_box_layout.addWidget(self.btn_edit_description, 0, Qt.AlignRight | Qt.AlignTop)
        self._desc_box = desc_box

        # === MAIN CONTENT ===
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(4)
        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        left_widget = QWidget()
        left_widget.setContentsMargins(10, 6, 6, 6)
        left_col = QVBoxLayout(left_widget)
        left_col.setContentsMargins(0, 0, 0, 0)
        left_col.setSpacing(6)

        left_col.addWidget(self._desc_box)

        # --- Sources ---
        src_label_row = QHBoxLayout()
        src_label = QLabel(self.tr("Orígenes:"))
        src_label.setStyleSheet(f"font-weight: 600; font-size: 11px; color: {theme.color('text_secondary')};")
        src_label_row.addWidget(src_label)
        src_label_row.addStretch()
        left_col.addLayout(src_label_row)

        src_top = QHBoxLayout()
        src_top.setSpacing(4)
        self.source_input = QComboBox()
        self.source_input.setEditable(True)
        self.source_input.setPlaceholderText(self.tr("E:\\DCIM..."))
        self.source_input.setMinimumWidth(100)
        self.source_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.source_input.currentTextChanged.connect(self.update_start_button_state)
        src_top.addWidget(self.source_input, 1)

        self.btn_add_source = QPushButton(self.tr("+ Origen"))
        self.btn_add_source.setToolTip(self.tr("Añadir un origen guardado, un dispositivo USB, WiFi o FTP"))
        self.btn_add_source.setMinimumWidth(70)
        self.btn_add_source.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        self.btn_add_source.clicked.connect(self._add_source_entry)
        src_top.addWidget(self.btn_add_source, 0)

        left_col.addLayout(src_top)

        self.source_list = QTableWidget()
        self.source_list.setColumnCount(4)
        self.source_list.setHorizontalHeaderLabels(
            [self.tr("Ruta de origen"), self.tr("Cámara"), self.tr("Contenido"), ""])
        header = self.source_list.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.setMinimumSectionSize(32)
        header.resizeSection(0, 100)
        header.resizeSection(1, 60)
        header.resizeSection(3, 36)
        self.source_list.verticalHeader().setVisible(False)
        self.source_list.setSelectionBehavior(QTableWidget.SelectRows)
        self.source_list.setSelectionMode(QTableWidget.SingleSelection)
        self.source_list.setSizePolicy(
            QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred))
        self.source_list.itemChanged.connect(self._on_source_check_changed)
        self.source_list.itemDoubleClicked.connect(self._on_source_double_clicked)
        self.source_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.source_list.customContextMenuRequested.connect(
            self._show_source_context_menu)
        left_col.addWidget(self.source_list)

        src_scan_row = QHBoxLayout()
        self.btn_detect_drives = QPushButton(self.tr("Detectar"))
        self.btn_detect_drives.setToolTip(self.tr("Detectar unidades extraíbles"))
        icons.apply(self.btn_detect_drives, "refresh", size=14)
        self.btn_detect_drives.clicked.connect(self._auto_detect_removable_drives)
        src_scan_row.addWidget(self.btn_detect_drives)
        self.btn_scan_cameras = QPushButton(self.tr("Escanear cámaras"))
        self.btn_scan_cameras.setToolTip(self.tr("Escanear cámaras de todos los orígenes checkeados"))
        icons.apply(self.btn_scan_cameras, "camera", size=14)
        self.btn_scan_cameras.clicked.connect(self._scan_all_cameras)
        src_scan_row.addWidget(self.btn_scan_cameras)

        self.btn_selective_dump = QPushButton(self.tr("Volcado selectivo…"))
        self.btn_selective_dump.setToolTip(self.tr("Seleccionar por fecha qué archivos volcar de un origen"))
        self.btn_selective_dump.clicked.connect(self._open_selective_dump)
        src_scan_row.addWidget(self.btn_selective_dump)

        src_scan_row.addStretch()
        left_col.addLayout(src_scan_row)

        # --- Sessions ---
        sess_box = QGroupBox(self.tr("Sesiones"))
        sess_box.setObjectName("SessionsBox")
        sess_box_layout = QVBoxLayout(sess_box)
        sess_box_layout.setContentsMargins(8, 6, 8, 6)
        sess_box_layout.setSpacing(4)

        sess_top = QHBoxLayout()
        self.sessions_combo = QComboBox()
        self.sessions_combo.setMinimumWidth(100)
        self.sessions_combo.setMaximumWidth(200)
        self.sessions_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.sessions_combo.currentIndexChanged.connect(self._on_session_selected)
        sess_top.addWidget(self.sessions_combo)

        self.btn_new_session = QPushButton()
        self.btn_new_session.setObjectName("IconButton")
        self.btn_new_session.setFixedSize(28, 28)
        self.btn_new_session.setToolTip(self.tr("Nueva sesión"))
        icons.apply(self.btn_new_session, "plus", size=18)
        self.btn_new_session.clicked.connect(self._add_manual_session)
        sess_top.addWidget(self.btn_new_session)

        self.btn_delete_session = QPushButton()
        self.btn_delete_session.setObjectName("IconButton")
        self.btn_delete_session.setFixedSize(28, 28)
        self.btn_delete_session.setToolTip(self.tr("Eliminar sesión…"))
        icons.apply(self.btn_delete_session, "minus", size=18)
        self.btn_delete_session.setEnabled(False)
        self.btn_delete_session.clicked.connect(self._delete_current_session)
        sess_top.addWidget(self.btn_delete_session)

        sess_top.addStretch()
        sess_box_layout.addLayout(sess_top)

        sess_src_row = QHBoxLayout()
        self._btn_browse_sess_src = QPushButton()
        self._btn_browse_sess_src.setObjectName("IconButton")
        self._btn_browse_sess_src.setFixedSize(28, 28)
        self._btn_browse_sess_src.setToolTip(self.tr("Examinar origen de sesión…"))
        icons.apply(self._btn_browse_sess_src, "folder", size=18)
        self._btn_browse_sess_src.clicked.connect(self._browse_session_src)
        sess_src_row.addWidget(self._btn_browse_sess_src)
        sess_src_row.addWidget(QLabel(self.tr("Origen:")))
        self.session_src_label = QLabel("")
        self.session_src_label.setStyleSheet(f"color: {theme.color('text_secondary')}; font-size: 11px;")
        self.session_src_label.setSizePolicy(
            QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred))
        sess_src_row.addWidget(self.session_src_label)
        sess_box_layout.addLayout(sess_src_row)

        sess_dest_row = QHBoxLayout()
        self._btn_browse_sess_dest = QPushButton()
        self._btn_browse_sess_dest.setObjectName("IconButton")
        self._btn_browse_sess_dest.setFixedSize(28, 28)
        self._btn_browse_sess_dest.setToolTip(self.tr("Examinar destino de sesión…"))
        icons.apply(self._btn_browse_sess_dest, "folder", size=18)
        self._btn_browse_sess_dest.clicked.connect(self._browse_session_dest)
        sess_dest_row.addWidget(self._btn_browse_sess_dest)
        sess_dest_row.addWidget(QLabel(self.tr("Destino:")))
        self.session_dest_label = QLabel(self.tr("Por defecto"))
        self.session_dest_label.setStyleSheet(f"color: {theme.color('text_secondary')}; font-size: 11px;")
        self.session_dest_label.setSizePolicy(
            QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred))
        sess_dest_row.addWidget(self.session_dest_label)
        sess_box_layout.addLayout(sess_dest_row)

        sess_post_row = QHBoxLayout()
        sess_post_row.setSpacing(10)
        sess_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        sess_post_row.addWidget(sess_box, 1)

        # --- Post-ingest actions (R-01: subgrupos "Al terminar" / "Operaciones") ---
        post_box = QGroupBox(self.tr("Acciones post-ingesta"))
        post_box.setObjectName("PostActionsBox")
        post_box_layout = QVBoxLayout(post_box)
        post_box_layout.setContentsMargins(8, 6, 8, 6)
        post_box_layout.setSpacing(6)

        post_terminar = QVBoxLayout()
        post_terminar.setSpacing(2)
        term_label = QLabel(self.tr("Al terminar"))
        term_label.setStyleSheet(f"font-weight: 600; font-size: 10px; color: {theme.color('text_secondary')};")
        post_terminar.addWidget(term_label)

        format_row = QHBoxLayout()
        format_row.setSpacing(6)
        self.chk_format_sources = QCheckBox(self.tr("Formatear orígenes al acabar:"))
        self.chk_format_sources.setToolTip(self.tr("Formatea las unidades de origen al acabar el volcado y la comprobación"))
        format_row.addWidget(self.chk_format_sources)
        self.combo_format_mode = QComboBox()
        self.combo_format_mode.addItems([self.tr("Rápido"), self.tr("Completo")])
        self.combo_format_mode.setFixedWidth(100)
        self.combo_format_mode.setEnabled(False)
        format_row.addWidget(self.combo_format_mode)
        format_row.addStretch()
        post_terminar.addLayout(format_row)
        self.chk_format_sources.toggled.connect(self.combo_format_mode.setEnabled)

        self.chk_shutdown = QCheckBox(self.tr("Apagar al acabar"))
        self.chk_shutdown.setToolTip(self.tr("Apaga el ordenador al finalizar todas las tareas de ingesta"))
        post_terminar.addWidget(self.chk_shutdown)

        post_box_layout.addLayout(post_terminar)

        post_operaciones = QVBoxLayout()
        post_operaciones.setSpacing(2)
        op_label = QLabel(self.tr("Operaciones"))
        op_label.setStyleSheet(f"font-weight: 600; font-size: 10px; color: {theme.color('text_secondary')};")
        post_operaciones.addWidget(op_label)

        op_row = QHBoxLayout()
        op_row.setSpacing(6)
        self.btn_reorganize = QPushButton(self.tr("Reorganizar por metadatos"))
        self.btn_reorganize.setToolTip(self.tr("Reorganiza los archivos en 'Unknown_Camera' detectando su cámara por metadatos"))
        self.btn_reorganize.clicked.connect(self._reorganize_by_metadata)
        op_row.addWidget(self.btn_reorganize)

        self.btn_clear_completed = QPushButton(self.tr("Limpiar completados"))
        self.btn_clear_completed.setToolTip(self.tr("Quita de la tabla las filas completadas"))
        self.btn_clear_completed.clicked.connect(self._clear_completed_rows)
        op_row.addWidget(self.btn_clear_completed)

        op_row.addStretch()
        post_operaciones.addLayout(op_row)

        post_box_layout.addLayout(post_operaciones)

        post_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        sess_post_row.addWidget(post_box, 1)
        left_col.addLayout(sess_post_row)

        left_col.addStretch()

        # --- Action buttons ---
        action_row = QHBoxLayout()
        self.btn_start = QPushButton(self.tr("INICIAR INGESTA"))
        self.btn_start.setObjectName("PrimaryAction")
        self.btn_start.setEnabled(False)
        self.btn_start.setMinimumHeight(36)
        self.btn_start.clicked.connect(self.start_ingest)

        self.btn_stop = QPushButton(self.tr("DETENER"))
        self.btn_stop.setObjectName("DangerAction")
        self.btn_stop.setEnabled(False)
        self.btn_stop.setMinimumHeight(36)
        self.btn_stop.clicked.connect(self.stop_ingest)

        action_row.addWidget(self.btn_start)
        action_row.addWidget(self.btn_stop)
        left_col.addLayout(action_row)

        self.ingest_status_label = QLabel("")
        self.ingest_status_label.setStyleSheet(f"color: {theme.color('text_secondary')}; font-style: italic; font-size: 10px; padding: 4px 10px;")

        # --- Progress ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setMinimumHeight(18)
        self.progress_bar.setFormat(self.tr("%v / %m archivos"))
        left_col.addWidget(self.progress_bar)

        stats_row = QHBoxLayout()
        self.lbl_files_processed = QLabel(self.tr("0 procesados"))
        self.lbl_files_processed.setStyleSheet(f"color: {theme.color('success')}; font-weight: bold; font-size: 10px;")
        self.lbl_files_pending = QLabel(self.tr("0 pendientes"))
        self.lbl_files_pending.setStyleSheet(f"color: {theme.color('warning')}; font-weight: bold; font-size: 10px;")
        self.lbl_files_errors = QLabel(self.tr("0 errores"))
        self.lbl_files_errors.setStyleSheet(f"color: {theme.color('danger')}; font-weight: bold; font-size: 10px;")
        stats_row.addWidget(self.lbl_files_processed)
        stats_row.addWidget(self.lbl_files_pending)
        stats_row.addWidget(self.lbl_files_errors)
        stats_row.addStretch()
        left_col.addLayout(stats_row)

        # --- Files table ---
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            self.tr("Archivo"), self.tr("Cámara"), self.tr("Estado"),
            self.tr("Progreso"), self.tr("Destino"), "",
        ])
        th = self.table.horizontalHeader()
        th.setSectionResizeMode(QHeaderView.Interactive)
        th.setStretchLastSection(False)
        th.setSectionResizeMode(4, QHeaderView.Stretch)
        th.setSectionResizeMode(5, QHeaderView.Fixed)
        th.resizeSection(0, 280)
        th.resizeSection(1, 130)
        th.resizeSection(2, 110)
        th.resizeSection(3, 90)
        th.resizeSection(5, 40)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_table_context_menu)
        self._style_table_viewports()

        splitter.addWidget(left_widget)
        splitter.addWidget(self.table)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        splitter.setSizes([400, 800])
        self._main_splitter = splitter
        self._splitter_default_sizes = [400, 800]

        self._splitter_restore_btn = QPushButton()
        self._splitter_restore_btn.setObjectName("IconButton")
        self._splitter_restore_btn.setFixedSize(28, 28)
        self._splitter_restore_btn.setToolTip(self.tr("Restaurar vista dividida"))
        self._splitter_restore_btn.setStyleSheet(
            "QPushButton { background-color: %s; border: 1px solid %s; border-radius: 14px; }"
            "QPushButton:hover { background-color: %s; }"
            % (theme.color("bg_elevated"), theme.color("border"), theme.color("border")))
        icons.apply(self._splitter_restore_btn, "refresh", size=16)
        self._splitter_restore_btn.clicked.connect(self._restore_splitter)
        self._splitter_restore_btn.hide()
        self._splitter_restore_btn.setParent(self.dashboard_view)
        splitter.splitterMoved.connect(self._on_splitter_moved)

        dash_layout.addWidget(splitter, 1)
        dash_layout.addWidget(self.ingest_status_label)

        self.main_layout.addWidget(self.dashboard_view)

        self.load_existing_projects()
        self._refresh_recent_paths()

        settings = QSettings("Audiovisual Production", "CosechaMedia")
        if settings.value("autoDetectDrives", False, type=bool):
            QTimer.singleShot(200, self._auto_detect_removable_drives)

    def _on_splitter_moved(self, pos, index):
        sizes = self._main_splitter.sizes()
        total = sum(sizes) or 1
        threshold = total * 0.03
        hidden = sizes[0] < threshold or sizes[1] < threshold
        if hidden:
            self._splitter_restore_btn.show()
            self._position_splitter_restore_btn()
        else:
            self._splitter_restore_btn.hide()

    def _position_splitter_restore_btn(self):
        handle = self._main_splitter.handle(1)
        if handle:
            pos = handle.mapTo(self.dashboard_view, handle.rect().center())
            btn = self._splitter_restore_btn
            btn.move(pos.x() - btn.width() // 2,
                     pos.y() - btn.height() // 2)

    def _restore_splitter(self):
        self._main_splitter.setSizes(self._splitter_default_sizes)
        self._splitter_restore_btn.hide()

    def _show_metadata_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(self.tr("Configuración"))
        dialog.setMinimumWidth(480)
        layout = QFormLayout(dialog)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 12, 16, 12)

        folder_input = QComboBox()
        folder_input.setEditable(True)
        folder_input.addItems(db.get_footage_folders())
        folder_input.setCurrentText(self.project_folder_name or "Footage")
        layout.addRow(self.tr("Carpeta footage:"), folder_input)

        org_combo = QComboBox()
        org_combo.addItems([self.tr("Cámara primero"), self.tr("Fecha primero"), self.tr("Solo cámara"), self.tr("Sin subcarpetas")])
        org_combo.setCurrentIndex(self.project_organization_type)
        layout.addRow(self.tr("Organización:"), org_combo)

        dur_combo = QComboBox()
        dur_combo.addItems([self.tr("Un solo día"), self.tr("Múltiples días"), self.tr("Sin fecha")])
        dur_map = {1: 0, 2: 1, 3: 2}
        dur_combo.setCurrentIndex(dur_map.get(self.project_duration_type, 0))
        layout.addRow(self.tr("Duración:"), dur_combo)

        chk_use_meta = QCheckBox()
        chk_use_meta.setChecked(self.project_use_metadata_date)
        layout.addRow(self.tr("Usar fecha de metadatos:"), chk_use_meta)

        date_input = QDateEdit()
        date_input.setCalendarPopup(True)
        date_input.setDate(self.project_date)
        date_input.setDisplayFormat("yyyy-MM-dd")
        layout.addRow(self.tr("Fecha:"), date_input)

        layout.addRow("", QWidget())

        # Proxies
        chk_gen_proxies = QCheckBox(self.tr("Generar proxies tras la ingesta"))
        chk_gen_proxies.setChecked(self.project_generate_proxies)
        layout.addRow(self.tr("Proxies:"), chk_gen_proxies)

        proxy_res_combo = QComboBox()
        proxy_res_combo.addItems(["720p", "1080p"])
        proxy_res_combo.setCurrentText(self.project_proxy_resolution)
        proxy_res_combo.setEnabled(self.project_generate_proxies)
        layout.addRow(self.tr("Resolución proxy:"), proxy_res_combo)
        chk_gen_proxies.toggled.connect(proxy_res_combo.setEnabled)

        layout.addRow("", QWidget())

        # Ruta maestra
        root_btn = QPushButton(self.tr("Cambiar..."))
        root_label = QLabel(self.dest_root or self.tr("(sin definir)"))
        root_label.setStyleSheet(f"color: {theme.color('text_secondary')};")
        root_row = QHBoxLayout()
        root_row.addWidget(root_label, 1)
        root_row.addWidget(root_btn)
        layout.addRow(self.tr("Ruta maestra:"), root_row)

        def _change_root():
            path = QFileDialog.getExistingDirectory(dialog, self.tr("Seleccionar ruta maestra"), self.dest_root or "")
            if path:
                if self.current_project_id is not None:
                    self._save_project_root(path)
                root_label.setText(path)

        root_btn.clicked.connect(_change_root)

        # Botones
        btn_save = QPushButton(self.tr("Guardar"))
        btn_save.setObjectName("PrimaryAction")

        def _save():
            self.project_folder_name = folder_input.currentText().strip() or "Footage"
            self.project_organization_type = org_combo.currentIndex()
            dur_idx = dur_combo.currentIndex()
            self.project_duration_type = {0: 1, 1: 2, 2: 3}.get(dur_idx, 1)
            self.project_use_metadata_date = chk_use_meta.isChecked()
            self.project_date = date_input.date()
            self.project_generate_proxies = chk_gen_proxies.isChecked()
            self.project_proxy_resolution = proxy_res_combo.currentText()
            if self.current_project_id is not None:
                db.add_footage_folder(self.project_folder_name)
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    'UPDATE projects SET folder_name=?, organization_type=?, duration_type=?, '
                    'use_metadata_date=?, generate_proxies=?, proxy_resolution=? WHERE id=?',
                    (self.project_folder_name, self.project_organization_type,
                     self.project_duration_type, int(self.project_use_metadata_date),
                     int(self.project_generate_proxies), self.project_proxy_resolution,
                     self.current_project_id)
                )
                conn.commit()
                conn.close()
            self._refresh_source_list()
            dialog.accept()

        btn_save.clicked.connect(_save)

        btn_defaults = QPushButton(self.tr("Establecer como predeterminado"))
        def _set_defaults():
            settings = QSettings("Audiovisual Production", "CosechaMedia")
            settings.setValue("default_folder_name", folder_input.currentText().strip() or "Footage")
            settings.setValue("default_organization_type", org_combo.currentIndex())
            settings.setValue("default_duration_type",
                              {0: 1, 1: 2, 2: 3}.get(dur_combo.currentIndex(), 1))
            settings.setValue("default_use_metadata_date", chk_use_meta.isChecked())
            self.ingest_status_label.setText(self.tr("Valores guardados como predeterminados."))
        btn_defaults.clicked.connect(_set_defaults)

        btn_cancel = QPushButton(self.tr("Cancelar"))
        btn_cancel.clicked.connect(dialog.reject)
        btn_row = QHBoxLayout()
        btn_row.addWidget(btn_defaults)
        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        layout.addRow("", btn_row)

        dialog.exec()

    def _show_camera_detection_dialog(self):
        settings = QSettings("Audiovisual Production", "CosechaMedia")
        dialog = QDialog(self)
        dialog.setWindowTitle(self.tr("Detección de cámara"))
        dialog.setMinimumWidth(320)
        layout = QVBoxLayout(dialog)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 12, 16, 12)

        mode_group = QGroupBox(self.tr("Modo"))
        mode_layout = QVBoxLayout(mode_group)
        mode_combo = QComboBox()
        mode_combo.addItems([self.tr("Manual"), self.tr("Automático (experimental)")])
        mode_combo.setCurrentIndex(0 if self.project_camera_detection_mode != "auto" else 1)
        mode_combo.setToolTip(
            self.tr("El modo automático es experimental: detecta la cámara desde un archivo de muestra "
                    "y puede no funcionar en todas las tarjetas."))
        mode_layout.addWidget(mode_combo)
        layout.addWidget(mode_group)

        timeout_group = QGroupBox(self.tr("Tiempo máximo de escaneo"))
        timeout_layout = QHBoxLayout(timeout_group)
        timeout_spin = QSpinBox()
        timeout_spin.setRange(5, 30)
        timeout_spin.setValue(self.project_camera_detection_timeout)
        timeout_spin.setEnabled(mode_combo.currentIndex() == 1)
        timeout_spin.setToolTip(self.tr("Segundos que espera el modo automático antes de preguntar por la cámara."))
        timeout_layout.addWidget(timeout_spin)
        timeout_layout.addStretch()
        layout.addWidget(timeout_group)

        def _on_mode_changed(index):
            timeout_spin.setEnabled(index == 1)
        mode_combo.currentIndexChanged.connect(_on_mode_changed)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton(self.tr("Cancelar"))
        btn_cancel.clicked.connect(dialog.reject)
        btn_save = QPushButton(self.tr("Guardar"))
        btn_save.setObjectName("PrimaryAction")
        def _save():
            selected = "auto" if mode_combo.currentIndex() == 1 else "manual"
            settings.setValue("camera_detection_mode", selected)
            settings.setValue("camera_detection_timeout", timeout_spin.value())
            self.project_camera_detection_mode = selected
            self.project_camera_detection_timeout = timeout_spin.value()
            self._update_detect_button_state()
            self._refresh_source_list()
            self.ingest_status_label.setText(self.tr("Detección de cámara actualizada."))
            dialog.accept()
        btn_save.clicked.connect(_save)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)
        dialog.exec()

    def _show_names_manager(self, title, getter, add_cb, rename_cb, delete_cb, duplicate_cb):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setMinimumWidth(380)
        dialog.setMinimumHeight(360)
        layout = QVBoxLayout(dialog)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 12, 16, 12)

        hint = QLabel(
            self.tr("Puedes añadir, duplicar, renombrar o eliminar nombres.")
            if duplicate_cb is not None
            else self.tr("Puedes añadir, renombrar o eliminar nombres.")
        )
        hint.setStyleSheet(f"color: {theme.color('text_secondary')}; font-size: 10px;")
        layout.addWidget(hint)

        search = QLineEdit()
        search.setPlaceholderText(self.tr("Buscar..."))
        layout.addWidget(search)

        listw = QListWidget()
        layout.addWidget(listw, 1)

        self._names_manager = {"filter": "", "items": []}

        def refresh():
            listw.clear()
            items = getter()
            self._names_manager["items"] = list(items)
            filter_text = self._names_manager["filter"].lower()
            for name in items:
                if not filter_text or filter_text in name.lower():
                    listw.addItem(name)
            if listw.count():
                listw.setCurrentRow(0)

        def on_search(text):
            self._names_manager["filter"] = text
            refresh()

        search.textChanged.connect(on_search)
        refresh()

        def _selected():
            item = listw.currentItem()
            return item.text() if item else None

        def _add():
            name, ok = QInputDialog.getText(dialog, self.tr("Añadir"), self.tr("Nuevo nombre:"))
            name = name.strip() if ok else ""
            if name:
                add_cb(name)
                refresh()

        def _dup():
            name = _selected()
            if not name:
                return
            duplicate_cb(name)
            refresh()

        def _ren():
            name = _selected()
            if not name:
                return
            new_name, ok = QInputDialog.getText(dialog, self.tr("Renombrar"), self.tr("Nuevo nombre:"), text=name)
            new_name = new_name.strip() if ok else ""
            if new_name and new_name != name:
                rename_cb(name, new_name)
                refresh()

        def _del():
            name = _selected()
            if not name:
                return
            reply = QMessageBox.question(
                dialog, self.tr("Eliminar"),
                self.tr("¿Eliminar '%1'?").arg(name),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                delete_cb(name)
                refresh()

        btn_row = QHBoxLayout()
        btn_add = QPushButton(self.tr("Añadir..."))
        btn_ren = QPushButton(self.tr("Renombrar..."))
        btn_del = QPushButton(self.tr("Eliminar"))
        for b in (btn_add, btn_ren, btn_del):
            btn_row.addWidget(b)
        btn_dup = None
        if duplicate_cb is not None:
            btn_dup = QPushButton(self.tr("Duplicar"))
            btn_row.addWidget(btn_dup)
        btn_row.addStretch()
        btn_close = QPushButton(self.tr("Cerrar"))
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

        btn_add.clicked.connect(_add)
        if btn_dup is not None:
            btn_dup.clicked.connect(_dup)
        btn_ren.clicked.connect(_ren)
        btn_del.clicked.connect(_del)
        btn_close.clicked.connect(dialog.accept)
        dialog.exec()

    def _manage_footage_folders(self):
        self._show_names_manager(
            self.tr("Personalizar carpeta de footage"),
            db.get_footage_folders,
            db.add_footage_folder,
            db.rename_footage_folder,
            db.delete_footage_folder,
            db.duplicate_footage_folder,
        )

    def _manage_containers(self):
        self._show_names_manager(
            self.tr("Personalizar contenedores de archivos"),
            db.get_containers,
            db.add_container,
            db.rename_container,
            db.delete_container,
            None,
        )
        metadata_engine.refresh_file_types()

    def _manage_dump_locations(self):
        if self.current_project_id is None:
            QMessageBox.information(self, self.tr("Sin proyecto"), self.tr("Selecciona un proyecto primero."))
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(self.tr("Destinos de volcado"))
        dialog.setMinimumSize(480, 340)
        layout = QVBoxLayout(dialog)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 12, 16, 12)

        hint = QLabel(
            self.tr("Los archivos se repartirán entre estos destinos por orden. Cuando uno esté lleno se pasará al siguiente. Deja vacío para usar la ruta maestra del proyecto.")
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {theme.color('text_secondary')}; font-size: 10px;")
        layout.addWidget(hint)

        listw = QListWidget()
        layout.addWidget(listw, 1)

        def refresh():
            listw.clear()
            for loc in db.dump_locations(self.current_project_id):
                include = []
                if loc["include_date"]:
                    include.append(self.tr("fecha"))
                if loc["include_camera"]:
                    include.append(self.tr("cámara"))
                suffix = f"  [{', '.join(include)}]" if include else ""
                listw.addItem(f"{loc['path']}{suffix}")

        btn_row = QHBoxLayout()
        btn_add = QPushButton(self.tr("Añadir..."))
        btn_del = QPushButton(self.tr("Eliminar"))
        btn_up = QPushButton(self.tr("Subir"))
        btn_down = QPushButton(self.tr("Bajar"))
        for b in (btn_add, btn_del, btn_up, btn_down):
            btn_row.addWidget(b)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        def _add():
            path = QFileDialog.getExistingDirectory(
                dialog, self.tr("Seleccionar destino de volcado"), self.dest_root or os.path.expanduser("~")
            )
            if not path:
                return
            label, ok = QInputDialog.getText(dialog, self.tr("Destino de volcado"), self.tr("Etiqueta (opcional):"))
            label = label.strip() if ok else None
            db.add_dump_location(self.current_project_id, path, label or None)
            refresh()

        def _del():
            row = listw.currentRow()
            if row < 0:
                return
            locs = db.dump_locations(self.current_project_id)
            db.delete_dump_location(locs[row]["id"])
            refresh()

        def _move(delta):
            row = listw.currentRow()
            if row < 0:
                return
            locs = db.dump_locations(self.current_project_id)
            new_row = row + delta
            if new_row < 0 or new_row >= len(locs):
                return
            locs[row], locs[new_row] = locs[new_row], locs[row]
            db.reorder_dump_locations(
                self.current_project_id, [l["id"] for l in locs]
            )
            refresh()
            listw.setCurrentRow(new_row)

        btn_add.clicked.connect(_add)
        btn_del.clicked.connect(_del)
        btn_up.clicked.connect(lambda: _move(-1))
        btn_down.clicked.connect(lambda: _move(1))

        btn_close = QPushButton(self.tr("Cerrar"))
        btn_close.setObjectName("PrimaryAction")
        bottom = QHBoxLayout()
        bottom.addStretch()
        bottom.addWidget(btn_close)
        btn_close.clicked.connect(dialog.accept)
        layout.addLayout(bottom)

        refresh()
        dialog.exec()

    def closeEvent(self, event):
        self._stop_wifi_reception()
        if self._wifi_panel is not None:
            self._wifi_panel.close()
        settings = QSettings("Audiovisual Production", "CosechaMedia")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        header = self.source_list.horizontalHeader()
        settings.setValue("sourceListWidths", [
            header.sectionSize(0), header.sectionSize(1), header.sectionSize(2), header.sectionSize(3)])
        event.accept()

    def load_existing_projects(self):
        previous_id = self.current_project_id
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

    def on_project_selected(self, index):
        self._reset_wifi_ingestors()
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
            'SELECT name, root_path, description, organization_type, duration_type, default_camera, '
            'folder_name, delicate_mode, use_metadata_date, generate_proxies, proxy_resolution '
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
        self.project_default_camera = res["default_camera"] or ""
        self.project_folder_name = res["folder_name"] or "Footage"
        self.project_delicate_mode = bool(res["delicate_mode"]) if res["delicate_mode"] is not None else False
        self.project_use_metadata_date = bool(res["use_metadata_date"]) if res["use_metadata_date"] is not None else True
        self.project_generate_proxies = bool(res["generate_proxies"]) if res["generate_proxies"] is not None else False
        self.project_proxy_resolution = res["proxy_resolution"] or "720p"

        name = res["name"]
        root = self.dest_root or self.tr("(sin ruta)")
        self.project_path_label.setText(f"→ {root}")
        self._set_project_description(res["description"] or "")
        self._set_status_color("success")
        self.status_text.setText(self.tr("Proyecto: %1").arg(name))

        self._populate_source_paths_from_sessions()
        self._refresh_sessions_combo()
        self._refresh_source_list()
        self._update_detect_button_state()

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

    def _update_detect_button_state(self):
        is_auto = self.project_camera_detection_mode == "auto"
        self.btn_detect_drives.setEnabled(True)
        self.btn_scan_cameras.setEnabled(is_auto)

    def _style_table_viewports(self):
        """Aplica el fondo semi-transparente a los viewports de las tablas."""
        base_rgba = theme.rgba50(theme.tinted_bg())
        for tbl in [self.table, self.source_list]:
            tbl.viewport().setStyleSheet("background-color: %s;" % base_rgba)

    def _set_status_color(self, color_key, radius=4):
        self._status_color_key = color_key
        self._status_color_radius = radius
        self.status_indicator.setStyleSheet(
            f"background-color: {theme.color(color_key)}; border-radius: {radius}px;"
        )

    def _switch_theme(self, name):
        theme.set_theme(name)
        theme.apply_theme()
        icons.refresh_all()
        self._style_table_viewports()
        self.dashboard_view.update()
        if getattr(self, "_status_color_key", None):
            self._set_status_color(self._status_color_key, self._status_color_radius)

    def _switch_accent(self, name):
        theme.set_accent(name)
        theme.apply_theme()
        icons.refresh_all()
        self._style_table_viewports()
        self.dashboard_view.update()
        if getattr(self, "_status_color_key", None):
            self._set_status_color(self._status_color_key, self._status_color_radius)

    def _toggle_wheat_background(self, checked):
        wheat_field.set_enabled(checked)
        self.dashboard_view.update()
        QSettings("Audiovisual Production", "CosechaMedia").setValue("wheatBg", checked)

    def update_start_button_state(self):
        if self.current_project_id is None:
            self.btn_start.setEnabled(False)
            return
        single = self.source_input.currentText().strip()
        if single and os.path.isdir(single):
            self.btn_start.setEnabled(True)
            return
        sessions = db.get_sessions(self.current_project_id)
        self.btn_start.setEnabled(
            any(s.get("source_path") and os.path.isdir(s["source_path"])
                and s.get("enabled", True) for s in sessions)
        )
        self._update_format_sources_state()

    def _refresh_recent_paths(self):
        source_paths = db.get_recent_paths("source")
        self.source_input.blockSignals(True)
        current_source = self.source_input.currentText()
        self.source_input.clear()
        self.source_input.addItems(source_paths)
        if current_source:
            self.source_input.setCurrentText(current_source)
        self.source_input.blockSignals(False)

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
            'default_camera, folder_name, delicate_mode, use_metadata_date '
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
                'default_camera, folder_name, delicate_mode, use_metadata_date) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (
                    new_name, src["root_path"], src["description"],
                    src["organization_type"], src["duration_type"],
                    src["default_camera"], src["folder_name"],
                    src["delicate_mode"], src["use_metadata_date"],
                )
            )
            new_id = cursor.lastrowid
            cursor.execute(
                'INSERT INTO sessions (project_id, name, shoot_date, status, source_path, camera_name, '
                'destination_override, delicate_mode) '
                'SELECT ?, name, shoot_date, status, source_path, camera_name, '
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



    def start_ingest(self):
        if self.current_project_id is None:
            return
        sessions = db.get_sessions(self.current_project_id)
        active = []
        single = self.source_input.currentText().strip()
        if single and os.path.isdir(single):
            active = [{
                "id": None,
                "source_path": single,
                "destination_override": None,
                "folder_name": None,
                "organization_type": None,
                "duration_type": None,
                "default_camera": None,
                "use_metadata_date": None,
                "delicate_mode": None,
            }]
        else:
            active = [
                s for s in sessions
                if s.get("source_path") and os.path.isdir(s["source_path"])
                and s.get("enabled", True)
            ]

        if not active:
            QMessageBox.warning(self, self.tr("Sin orígenes"), self.tr("No hay sesiones con rutas de origen válidas."))
            return

        sources = [s["source_path"] for s in active]
        for s in sources:
            db.save_recent_path(s, "source")
        self._refresh_recent_paths()

        if any(getattr(w, "running", False) for w in self.watchers):
            QMessageBox.information(self, self.tr("Ya en marcha"), self.tr("El monitoreo de la SD ya está activo."))
            return

        folder_name = self.project_folder_name or "Footage"
        if folder_name:
            db.add_footage_folder(folder_name)

        self.table.setRowCount(0)
        self.table.setSortingEnabled(False)
        self.progress_bar.setValue(0)
        self._file_row_map = {}
        self._processed_count = 0
        self._total_files = 0
        self._unknown_cameras = set()
        self._ingested_videos = []
        self._ingestors = []
        self._ingest_completed = set()

        camera_map = {}
        for s in sessions:
            sp = s.get("source_path")
            cn = s.get("camera_name")
            if sp and cn:
                camera_map[os.path.normpath(sp)] = cn
        self._current_camera_map = camera_map

        project_targets = []
        if self.current_project_id is not None:
            for loc in db.dump_locations(self.current_project_id):
                if loc["path"] and os.path.isdir(loc["path"]):
                    project_targets.append(
                        DumpTarget(loc["id"], loc["path"], loc["include_date"], loc["include_camera"])
                    )

        for sess in active:
            sid = sess.get("id")
            s_folder = sess.get("folder_name") or self.project_folder_name or "Footage"
            s_org_raw = sess.get("organization_type")
            s_org = self.project_organization_type if s_org_raw is None else s_org_raw
            s_dur = sess.get("duration_type")
            s_dur = self.project_duration_type if s_dur is None else s_dur
            s_cam = sess.get("default_camera")
            s_cam = self.project_default_camera if s_cam is None else s_cam
            s_use_meta = sess.get("use_metadata_date")
            s_use_meta = self.project_use_metadata_date if s_use_meta is None else s_use_meta
            device_key = sess.get("device_id") or sess.get("source_path") or ""
            dev_delicate = db.get_device_delicate(device_key)
            if dev_delicate is not None:
                s_delicate = bool(dev_delicate)
            else:
                s_delicate = self.project_delicate_mode

            s_content_filter = None
            try:
                raw_filter = sess.get("content_filter")
                if raw_filter:
                    s_content_filter = json.loads(raw_filter)
            except (TypeError, ValueError):
                s_content_filter = None

            dest_root = sess.get("destination_override") or self.dest_root
            sess_targets = None
            if not sess.get("destination_override"):
                sess_targets = project_targets or None
            order_val = ORG_TYPE_MAP.get(s_org, "camera_first")

            if sid is not None:
                db.update_session_config(sid, status="active")

            ing = Ingestor(
                self.current_project_id,
                dest_root,
                folder_name=s_folder,
                use_metadata_date=bool(s_use_meta),
                order_type=order_val,
                duration_type=s_dur,
                default_camera=s_cam,
                delicate_mode=bool(s_delicate),
                session_id=sid,
                camera_map=camera_map,
                manual_date=self.project_date.toString("yyyy-MM-dd"),
                dump_targets=sess_targets,
                project_master_root=self.dest_root,
                content_filter=s_content_filter,
            )
            ing.file_started.connect(
                lambda sp, i=ing: self.on_file_started(sp, ingestor=i)
            )
            ing.copy_progress.connect(
                lambda sp, cb, tb, i=ing: self.on_copy_progress(sp, cb, tb, ingestor=i)
            )
            ing.file_finished.connect(
                lambda sp, dp, ok, md, i=ing: self.on_file_finished(sp, dp, ok, md, ingestor=i)
            )
            ing.ingest_complete.connect(
                lambda stats, i=ing: self._on_ingestor_complete(stats, i)
            )
            ing.camera_rename_needed.connect(self._on_camera_rename_needed)
            self._ingestors.append(ing)

        self.watchers = []
        for idx, sess in enumerate(active):
            ing = self._ingestors[idx]
            watcher = FileSystemWatcher(
                sess["source_path"],
                ing,
                status_callback=self.update_status_from_watcher
            )
            ing.begin_watching(1)
            watcher.start()
            self.watchers.append(watcher)

        self.btn_start.setEnabled(False)
        self.btn_start.setText(self.tr("Procesando..."))
        self.btn_stop.setEnabled(True)
        self.ingest_status_label.setText(self.tr("Procesando %1 ruta(s): %2").arg(len(sources)).arg(', '.join(sources)))
        self._set_status_color("warning", 6)
        self.status_text.setText(self.tr("En progreso"))

    def stop_ingest(self):
        for watcher in self.watchers:
            if watcher:
                watcher.stop()
        self.watchers = []

        for ing in self._ingestors:
            ing.stop()

        self.btn_start.setText(self.tr("Iniciar Ingesta"))
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.table.setSortingEnabled(True)
        self.ingest_status_label.setText(self.tr("Ingesta detenida por el usuario"))
        self._set_status_color("danger", 6)
        self.status_text.setText(self.tr("Detenido"))

        self.notification_manager.notify_ingest_stopped()

    def on_file_started(self, source_path, ingestor=None):
        was_sorted = self.table.isSortingEnabled()
        if was_sorted:
            self.table.setSortingEnabled(False)
        row = self.table.rowCount()
        self.table.insertRow(row)

        filename_item = QTableWidgetItem(os.path.basename(source_path))
        filename_item.setFlags(filename_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, 0, filename_item)

        cam_name = self._camera_for_path(source_path)
        if cam_name:
            cam_text = cam_name
        elif self.project_camera_detection_mode == "manual":
            cam_text = self.tr("Sin nombre")
        else:
            cam_text = self.tr("Detectando...")
        camera_item = QTableWidgetItem(cam_text)
        camera_item.setFlags(camera_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, 1, camera_item)

        status_item = QTableWidgetItem(self.tr("Copiando..."))
        status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, 2, status_item)

        progress_item = QTableWidgetItem("0%")
        progress_item.setFlags(progress_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, 3, progress_item)

        dest_item = QTableWidgetItem("")
        dest_item.setFlags(dest_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, 4, dest_item)

        self.table.setCellWidget(row, 5, self._build_remove_file_button(filename_item))

        if was_sorted:
            self.table.setSortingEnabled(True)

        # Con el mismo origen compartido por varias sesiones (fan-out WiFi),
        # cada ingestor tiene su propia fila; si no hay ingestor (llamadas
        # externas/directas) se indexa solo por ruta como antes.
        key = self._file_row_key(source_path, ingestor)
        self._file_row_map[key] = filename_item
        self._total_files += 1
        self.progress_bar.setMaximum(self._total_files)
        self.ingest_status_label.setText(self.tr("Procesando: %1").arg(os.path.basename(source_path)))

    @staticmethod
    def _file_row_key(source_path, ingestor):
        return (id(ingestor), source_path) if ingestor is not None else source_path

    def on_copy_progress(self, source_path, copied_bytes, total_bytes, ingestor=None):
        item = self._file_row_map.get(self._file_row_key(source_path, ingestor))
        if item is None or not total_bytes:
            return
        row = self.table.indexFromItem(item).row()
        pct = int(copied_bytes * 100.0 / total_bytes)
        pct = max(0, min(100, pct))
        progress_item = QTableWidgetItem(f"{pct}%")
        progress_item.setFlags(progress_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, 3, progress_item)

    def on_file_finished(self, source_path, dest_path, success, metadata=None, ingestor=None):
        item = self._file_row_map.get(self._file_row_key(source_path, ingestor))
        if item is not None:
            row = self.table.indexFromItem(item).row()
            if self.project_camera_detection_mode != "manual" and metadata and metadata.get("camera_model") != "Unknown":
                camera_item = QTableWidgetItem(metadata["camera_model"])
                self.table.setItem(row, 1, camera_item)

            if success:
                status = self.tr("Completado")
                text_color = QColor(theme.color("success"))
            else:
                status = self.tr("Error")
                text_color = QColor(theme.color("danger"))

            status_item = QTableWidgetItem(status)
            status_item.setForeground(text_color)
            self.table.setItem(row, 2, status_item)

            progress_item = QTableWidgetItem("100%" if success else "0%")
            progress_item.setForeground(text_color if success else QColor(theme.color("danger")))
            progress_item.setFlags(progress_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 3, progress_item)

            if dest_path:
                dest_item = QTableWidgetItem(dest_path)
                self.table.setItem(row, 4, dest_item)

        if success and dest_path:
            ftype = metadata_engine.get_file_type_info(dest_path)
            if ftype.get("type") == "video":
                root = ingestor.destination_root if ingestor else self.dest_root
                self._ingested_videos.append((dest_path, root))
            # Un archivo recibido por WiFi ya está en su destino: lo sacamos de
            # la caché para que no se vuelva a ingerir en la próxima pasada.
            if self._is_inbox_cache_path(source_path):
                self._remove_ingested_wifi_source(source_path)

        self._processed_count += 1
        self.progress_bar.setValue(self._processed_count)

        self.lbl_files_processed.setText(self.tr("%1 procesados").arg(self._processed_count))
        self.lbl_files_pending.setText(self.tr("%1 pendientes").arg(max(0, self._total_files - self._processed_count)))

    def _on_ingestor_complete(self, stats, ingestor):
        self._ingest_completed.add(id(ingestor))
        if ingestor.session_id is not None:
            db.update_session_config(ingestor.session_id, status="completed")
        if len(self._ingest_completed) >= len(self._ingestors):
            self._finalize_ingest()

    def _finalize_ingest(self):
        try:
            for watcher in self.watchers:
                if watcher:
                    watcher.stop()
            self.watchers = []

            for ing in self._ingestors:
                ing.stop()

            self.btn_start.setText(self.tr("Iniciar Ingesta"))
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)

            total_processed = sum(ing.get_stats().get("processed", 0) for ing in self._ingestors)
            total_errors = sum(ing.get_stats().get("errors", 0) for ing in self._ingestors)
            total_skipped = sum(ing.get_stats().get("skipped", 0) for ing in self._ingestors)
            self.ingest_status_label.setText(
                self.tr("Ingesta completada: %1 procesados, %2 errores, %3 omitidos.")
                .arg(total_processed).arg(total_errors).arg(total_skipped)
            )

            self._set_status_color("success", 6)
            self.status_text.setText(self.tr("Completado"))

            stats = {
                "processed": total_processed,
                "errors": total_errors,
                "skipped": total_skipped,
            }
            if total_errors > 0:
                self.notification_manager.notify_ingest_failed(stats)
            else:
                self.notification_manager.notify_ingest_complete(stats)

            self._refresh_sessions_combo()
            self._post_ingest_rename_dialog()
            self.table.setSortingEnabled(True)

            if total_errors == 0:
                # Limpia la caché WiFi que haya quedado (ya ingerida).
                for ing in self._ingestors:
                    if ing.session_id is not None:
                        self._clear_wifi_cache(ing.session_id)

            can_destroy = total_errors == 0
            blocked = []
            if self.chk_format_sources.isChecked() and not can_destroy:
                blocked.append(self.tr("formateo de orígenes"))
            if self.chk_shutdown.isChecked() and not can_destroy:
                blocked.append(self.tr("apagado del equipo"))
            if blocked:
                QMessageBox.warning(
                    self, self.tr("Acciones posteriores bloqueadas"),
                    self.tr("Hay errores en la ingesta. Por seguridad, se han bloqueado las siguientes acciones:\n• %1")
                    .arg("\n• ".join(blocked))
                )

            self._pending_actions = []
            if self.chk_format_sources.isChecked() and can_destroy:
                self._pending_actions.append("format")
            if self.project_generate_proxies:
                self._pending_actions.append("proxies")
            if self.chk_shutdown.isChecked() and can_destroy:
                self._pending_actions.append("shutdown")
            self._run_next_post_ingest_action()
        except Exception as e:
            print(f"Error al finalizar la ingesta: {e}")
            self.notification_manager.notify_ingest_failed({})

    def _run_next_post_ingest_action(self):
        while True:
            if not self._pending_actions:
                self.btn_start.setText(self.tr("Iniciar Ingesta"))
                self.btn_start.setEnabled(True)
                return
            action = self._pending_actions[0]
            if action == "format":
                started = self._format_sources_after_ingest()
            elif action == "proxies":
                started = self._generate_proxies_after_ingest()
            elif action == "shutdown":
                self._pending_actions.pop(0)
                self._shutdown_computer()
                continue
            else:
                started = False
            self._pending_actions.pop(0)
            if started:
                return

    def _is_managed_source_path(self, path):
        """True si ``path`` es una caché gestionada (WiFi/FTP/MTP), no editable
        por el usuario y nunca formateable."""
        if not path:
            return False
        p = os.path.normpath(os.path.abspath(path))
        data_root = os.path.normpath(os.path.abspath(os.path.dirname(db.db_path)))
        for sub in ("inbox", "device_cache"):
            root = os.path.join(data_root, sub)
            if p.startswith(root + os.sep) or p == root:
                return True
        return False

    def _is_managed_session(self, session):
        """True si la sesión es auto-gestionada (WiFi/FTP/MTP): su origen es la
        caché local del dispositivo, no un destino elegido por el usuario."""
        did = (session or {}).get("device_id") or ""
        if did.startswith("wifi:") or did.startswith("ftp:"):
            return True
        return self._is_managed_source_path((session or {}).get("source_path"))

    def _format_candidate_paths(self):
        """Rutas de unidades extraíbles reales y no gestionadas: las únicas que
        tiene sentido formatear al acabar la ingesta."""
        if self.current_project_id is None:
            return []
        return [p for p in self._source_paths
                if is_removable_drive(p) and not self._is_managed_source_path(p)]

    def _update_format_sources_state(self):
        """Desactiva «Formatear orígenes» cuando no hay ninguna unidad extraíble
        formateable (p. ej. proyectos solo-WiFi)."""
        has_candidates = bool(self._format_candidate_paths())
        self.chk_format_sources.setEnabled(has_candidates)
        if not has_candidates and self.chk_format_sources.isChecked():
            self.chk_format_sources.setChecked(False)
        self.combo_format_mode.setEnabled(
            has_candidates and self.chk_format_sources.isChecked())

    def _format_sources_after_ingest(self) -> bool:
        if sys.platform != "win32":
            QMessageBox.information(
                self, self.tr("Formatear orígenes"),
                self.tr("El formateo de tarjetas solo está disponible en Windows.")
            )
            return False
        if not self._source_paths:
            QMessageBox.information(self, self.tr("Formatear orígenes"), self.tr("No hay orígenes que formatear."))
            return False
        mode_idx = self.combo_format_mode.currentIndex()
        mode = self.tr("completo") if mode_idx == 1 else self.tr("rápido")
        removable = self._format_candidate_paths()
        skipped = [p for p in self._source_paths if p not in removable]
        if not removable:
            QMessageBox.warning(
                self, self.tr("Formatear orígenes"),
                self.tr("Ninguno de los orígenes es una unidad extraíble. No se formateará nada.")
            )
            return False
        lines = [self.tr("Se formatearán las unidades extraíbles (modo %1):").arg(mode)]
        lines += removable
        if skipped:
            lines.append(self.tr("\nSe omitirán (no son unidades extraíbles):"))
            lines += skipped
        reply = QMessageBox.question(
            self, self.tr("Formatear orígenes"),
            "\n".join(lines) + self.tr("\n\n¿Continuar?"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return False
        self.btn_start.setEnabled(False)
        self.btn_start.setText(self.tr("Formateando..."))
        self._run_background(
            _format_sources_worker, self._on_format_finished,
            removable, quick=(mode_idx != 1)
        )
        return True

    def _on_format_finished(self, success, payload):
        if not success:
            QMessageBox.critical(self, self.tr("Formatear"), self.tr("No se pudo completar el formateo:\n%1").arg(str(payload)))
        else:
            failed = [f"{p}: {e}" for p, ok, e in payload if not ok]
            ok_count = sum(1 for _, ok, _ in payload if ok)
            if failed:
                self.ingest_status_label.setText(self.tr("Formateados %1/%2 con errores").arg(ok_count).arg(len(payload)))
                QMessageBox.warning(
                    self, self.tr("Formatear"),
                    self.tr("Formateados %1/%2.\nErrores:\n%3").arg(ok_count).arg(len(payload)).arg("\n".join(failed))
                )
            else:
                self.ingest_status_label.setText(self.tr("Orígenes formateados: %1/%2").arg(ok_count).arg(len(payload)))
                QMessageBox.information(
                    self, self.tr("Formatear"),
                    self.tr("Orígenes formateados correctamente: %1/%2.").arg(ok_count).arg(len(payload))
                )
        self._run_next_post_ingest_action()

    def _shutdown_computer(self):
        reply = QMessageBox.question(
            self, self.tr("Apagar ordenador"),
            self.tr("Todas las tareas han finalizado. ¿Apagar el ordenador ahora?"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        import subprocess
        try:
            if sys.platform.startswith("win"):
                subprocess.run(["shutdown", "/s", "/t", "10"], check=False)
            elif sys.platform == "darwin":
                subprocess.run(["sudo", "shutdown", "-h", "+1"], check=False)
            else:
                subprocess.run(["shutdown", "-h", "+1"], check=False)
            self.ingest_status_label.setText(self.tr("Apagado programado."))
        except Exception as e:
            QMessageBox.warning(self, self.tr("Apagar"), self.tr("No se pudo programar el apagado:\n%1").arg(str(e)))

    def update_status_from_watcher(self, message):
        self.ingest_status_label.setText(message)

    def _run_background(self, fn, on_finished, *args, **kwargs):
        """Lanza `fn` en un QThread. on_finished(success, payload) corre en la UI."""
        thread = QThread(self)
        worker = _TaskWorker(fn, *args, **kwargs)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self.ingest_status_label.setText)
        worker.finished.connect(thread.quit)
        worker.finished.connect(lambda ok, res, t=thread, w=worker: self._cleanup_background(t, w))
        thread.finished.connect(thread.deleteLater)
        worker.finished.connect(on_finished)
        self._background_tasks.append((thread, worker))
        thread.start()

    def _cleanup_background(self, thread, worker):
        self._background_tasks = [(t, w) for (t, w) in self._background_tasks if t is not thread]

    def _on_camera_rename_needed(self, source_path, camera_name):
        if self.project_camera_detection_mode == "manual":
            return
        self._unknown_cameras.add(camera_name)

    def _show_table_context_menu(self, pos):
        context_menu = QMenu(self)
        clear_action = context_menu.addAction(self.tr("Eliminar completados"))
        clear_action.triggered.connect(self._clear_completed_rows)
        context_menu.exec(self.table.viewport().mapToGlobal(pos))

    def _clear_completed_rows(self):
        """Quita de la tabla de ingesta las filas cuyo estado es «Completado»."""
        done_text = self.tr("Completado")
        was_sorted = self.table.isSortingEnabled()
        self.table.setSortingEnabled(False)
        try:
            for r in range(self.table.rowCount() - 1, -1, -1):
                status_item = self.table.item(r, 2)
                if status_item and status_item.text() == done_text:
                    self.table.removeRow(r)
        finally:
            self.table.setSortingEnabled(was_sorted)

    def _post_ingest_rename_dialog(self):
        if self.project_camera_detection_mode == "manual":
            self._unknown_cameras.clear()
            return
        if not self._unknown_cameras:
            return
        unknown_list = list(self._unknown_cameras)
        self._unknown_cameras.clear()
        for old_name in unknown_list:
            new_name, ok = QInputDialog.getText(
                self, self.tr("Cámara desconocida detectada"),
                self.tr("Se detectó '%1' sin identificar.\nIntroduce un nombre para el dispositivo:").arg(old_name),
                text=""
            )
            if ok and new_name.strip():
                new_cam = new_name.strip()
                for ing in self._ingestors:
                    ing.rename_camera(old_name, new_cam)
                for r in range(self.table.rowCount()):
                    cam_item = self.table.item(r, 1)
                    if cam_item and cam_item.text() == old_name:
                        cam_item.setText(new_cam)
                sessions = db.get_sessions(self.current_project_id) if self.current_project_id else []
                for s in sessions:
                    if s.get("camera_name") == old_name:
                        sp = s.get("source_path", "")
                        self._persist_camera_mapping(s["id"], sp, new_cam)
                self.ingest_status_label.setText(self.tr("Cámara renombrada: %1 → %2").arg(old_name).arg(new_cam))

    def _on_source_double_clicked(self, item):
        if item.column() == 0:
            self._prompt_change_source_path(item.row())
        elif item.column() == 1:
            self._prompt_rename_camera(item.row())

    def _prompt_change_source_path(self, row):
        if row < 0 or row >= len(self._source_paths):
            return
        old = self._source_paths[row]
        start = old if os.path.isdir(old) else os.path.expanduser("~")
        new = QFileDialog.getExistingDirectory(
            self, self.tr("Seleccionar carpeta de la Tarjeta SD"), start)
        if not new or new == old:
            return
        if new in self._source_paths:
            QMessageBox.information(
                self, self.tr("Aviso"),
                self.tr("El origen '%1' ya está en la lista.").arg(new))
            return
        if 0 <= row < len(self._source_paths):
            self._source_paths[row] = new
        if self.current_project_id is not None:
            for s in db.get_sessions(self.current_project_id):
                if s.get("source_path") == old:
                    db.update_session_config(s["id"], source_path=new)
        self._refresh_source_list()
        self._refresh_sessions_combo()
        self.update_start_button_state()
        self.ingest_status_label.setText(self.tr("Origen cambiado: %1").arg(new))

    def _prompt_rename_camera(self, row):
        if self.current_project_id is None:
            return
        if row < 0 or row >= len(self._source_paths):
            return
        path = self._source_paths[row]
        sessions = db.get_sessions(self.current_project_id)
        session = next((s for s in sessions if s.get("source_path") == path), None)
        if not session:
            return
        current = session.get("camera_name") or ""
        name, ok = QInputDialog.getText(
            self, self.tr("Renombrar cámara"),
            self.tr("Nombre de la cámara para este origen:"),
            text=current
        )
        if ok:
            db.update_session_config(session["id"], camera_name=name.strip() or None)
            self._refresh_source_list()
            self._refresh_sessions_combo()

    def _refresh_source_list(self):
        self.source_list.blockSignals(True)
        self.source_list.setRowCount(0)
        if self.current_project_id is None:
            self.source_list.blockSignals(False)
            return
        sessions = db.get_sessions(self.current_project_id)
        by_path = {}
        for s in sessions:
            sp = s.get("source_path")
            if sp:
                by_path.setdefault(sp, []).append(s)
        for row, path in enumerate(self._source_paths):
            self.source_list.insertRow(row)
            # Column 0: source path with checkbox + optional QR/FTP button
            path_sessions = by_path.get(path) or []
            sess = path_sessions[0] if path_sessions else None
            any_enabled = any(s.get("enabled", True) for s in path_sessions)
            checked = (sess is not None and any_enabled)
            self.source_list.setCellWidget(row, 0, self._build_path_widget(row, path, sess, checked))

            # Column 1: camera name
            cam = sess.get("camera_name") if sess else None
            cam_text = cam if cam else (self.tr("Sin nombre") if self.project_camera_detection_mode == "manual" else "—")
            cam_item = QTableWidgetItem(cam_text)
            if self.project_camera_detection_mode != "manual":
                cam_item.setFlags(cam_item.flags() & ~Qt.ItemIsEditable)
            self.source_list.setItem(row, 1, cam_item)
            # Column 2: content filter (always, including WiFi/FTP)
            self.source_list.setCellWidget(row, 2, self._build_content_button(row, sess))
            # Column 3: per-row delete
            self.source_list.setCellWidget(row, 3, self._build_remove_source_button(row))
        self.source_list.blockSignals(False)
        self._update_format_sources_state()
        self._update_source_list_height()

    def _update_source_list_height(self):
        """Altura mínima de la tabla de orígenes según su contenido (B-06).

        La tabla crece con las filas sin saltos bruscos, pero sin fijar un
        máximo: con espacio disponible la amplía el propio layout."""
        header = self.source_list.horizontalHeader().height() or 26
        row_h = self.source_list.verticalHeader().defaultSectionSize() or 30
        height = header + self.source_list.rowCount() * row_h
        self.source_list.setMinimumHeight(max(56, height))

    def _build_path_widget(self, row, path, session, checked):
        widget = QWidget()
        lay = QHBoxLayout(widget)
        lay.setContentsMargins(4, 0, 4, 0)
        lay.setSpacing(4)
        cb = QCheckBox()
        cb.setChecked(checked)
        cb.stateChanged.connect(lambda state, r=row, p=path: self._on_source_widget_check_changed(r, p, state))
        lay.addWidget(cb)
        lbl = QLabel(path)
        lbl.setStyleSheet(f"font-size: 11px;")
        lbl.setToolTip(path)
        lbl.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred))
        lay.addWidget(lbl, 1)
        device_id = (session or {}).get("device_id") or ""
        is_wifi = bool(session) and device_id == WIFI_DEVICE_ID
        is_ftp = bool(session) and device_id.startswith("ftp:")
        if is_wifi or is_ftp:
            remote_btn = self._build_remote_source_button(row, session, is_wifi)
            lay.addWidget(remote_btn)
        return widget

    def _on_source_widget_check_changed(self, row, path, state):
        checked = state == Qt.Checked
        if self.current_project_id is None:
            return
        existing = db.get_sessions(self.current_project_id)
        with_path = [s for s in existing if s.get("source_path") == path]
        if checked:
            if not with_path:
                no_source = [s for s in existing if not s.get("source_path")]
                base = self._drive_label(path)
                name = f"Auto ({base})"
                if no_source:
                    sid = no_source[0]["id"]
                    db.update_session_config(sid, source_path=path, name=name)
                    self.ingest_status_label.setText(self.tr("Origen asignado a sesión #%1").arg(sid))
                else:
                    sid = db.create_session(
                        self.current_project_id, name,
                        QDate.currentDate().toString("yyyy-MM-dd"), "active",
                        source_path=path
                    )
                    self.ingest_status_label.setText(self.tr("Sesión auto creada para %1").arg(path))
                self.current_session_id = sid
                self._detect_camera_for_session(sid, path)
            else:
                for s in with_path:
                    db.update_session_config(s["id"], enabled=1)
                self.ingest_status_label.setText(self.tr("Origen habilitado: %1").arg(path))
        else:
            if with_path:
                for s in with_path:
                    db.update_session_config(s["id"], enabled=0)
                self.ingest_status_label.setText(self.tr("Origen deshabilitado: %1").arg(path))
        self._refresh_sessions_combo()
        self.update_start_button_state()

    def _build_remote_source_button(self, row, session, is_wifi):
        text = self.tr("QR") if is_wifi else self.tr("FTP")
        tip = (self.tr("Mostrar el código QR de este dispositivo")
               if is_wifi else self.tr("Configurar este origen FTP"))
        btn = QPushButton(text)
        btn.setToolTip(tip)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
            "QPushButton { border: none; text-align: left; padding: 2px 6px;"
            " color: %s; font-size: 11px; }"
            "QPushButton:hover { color: %s; }"
            "QPushButton:disabled { color: %s; }"
            % (theme.color("text_secondary"), theme.color("accent"), theme.color("text_disabled"))
        )
        if is_wifi:
            sender_name = (session.get("camera_name")
                           or session.get("device_folder") or "")
            btn.clicked.connect(
                lambda _=False, n=sender_name: self._show_wifi_qr_for_sender(n))
        else:
            btn.clicked.connect(
                lambda _=False, s=session: self._reconfigure_ftp_source(s))
        return btn

    def _build_content_button(self, row, session):
        device_id = (session or {}).get("device_id") or ""
        device_key = device_id or ((session or {}).get("source_path") or "")
        filt = None
        if session:
            try:
                raw = session.get("content_filter")
                if raw:
                    filt = json.loads(raw)
            except (TypeError, ValueError):
                filt = None
        text = content_summary(filt)

        wrapper = QWidget()
        wrapper_lay = QHBoxLayout(wrapper)
        wrapper_lay.setContentsMargins(0, 0, 0, 0)
        wrapper_lay.setSpacing(2)

        btn = QPushButton(text)
        btn.setToolTip(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
            "QPushButton { border: none; text-align: left; padding: 2px 6px;"
            " color: %s; font-size: 11px; }"
            "QPushButton:hover { color: %s; }"
            "QPushButton:disabled { color: %s; }"
            % (theme.color("text_secondary"), theme.color("accent"), theme.color("text_disabled"))
        )
        if not session:
            btn.setEnabled(False)
            btn.setToolTip(self.tr("Activa el origen para configurar su contenido."))
        else:
            btn.clicked.connect(lambda _=False, r=row: self._open_content_filter(r))
        wrapper_lay.addWidget(btn, 1)

        is_wifi = device_id == "wifi:pairdrop"
        if is_wifi and session:
            mode_btn = QPushButton()
            mode_btn.setObjectName("IconButton")
            mode_btn.setFixedSize(22, 22)
            mode_btn.setCursor(Qt.PointingHandCursor)
            is_folder = bool(session.get("folder_mode"))
            icons.apply(mode_btn, "folder" if is_folder else "copy", size=14)
            mode_btn.setToolTip(
                self.tr("Modo: enviar archivos sueltos") if not is_folder
                else self.tr("Modo: enviar carpeta entera"))
            mode_btn.clicked.connect(
                lambda _=False, s=session, b=mode_btn: self._toggle_wifi_folder_mode(s, b))
            wrapper_lay.addWidget(mode_btn, 0, Qt.AlignRight)

        delicate_btn = QPushButton()
        delicate_btn.setObjectName("IconButton")
        delicate_btn.setFixedSize(22, 22)
        delicate_btn.setCursor(Qt.PointingHandCursor)
        delicate_btn.setToolTip(self.tr("Cambiar modo: rápido / delicado"))
        is_delicate = bool(db.get_device_delicate(device_key)) if device_key else False
        icons.apply(delicate_btn, "snail" if is_delicate else "zap", size=14)
        if session:
            delicate_btn.clicked.connect(
                lambda _=False, dk=device_key, b=delicate_btn: self._toggle_device_delicate(dk, b))
        else:
            delicate_btn.setEnabled(False)
        wrapper_lay.addWidget(delicate_btn, 0, Qt.AlignRight)

        return wrapper

    def _toggle_wifi_folder_mode(self, session, btn):
        sid = session["id"]
        current = bool(session.get("folder_mode"))
        new_val = 0 if current else 1
        db.update_session_config(sid, folder_mode=new_val)
        session["folder_mode"] = new_val
        icons.apply(btn, "folder" if new_val else "copy", size=14)
        btn.setToolTip(
            self.tr("Modo: enviar archivos sueltos") if not new_val
            else self.tr("Modo: enviar carpeta entera"))
        if self._wifi_server is not None and self._wifi_server.running:
            self._wifi_server.folder_mode = bool(new_val)
        if self._wifi_panel is not None:
            self._wifi_panel.refresh()

    def _toggle_device_delicate(self, device_key, btn):
        current = bool(db.get_device_delicate(device_key))
        db.set_device_delicate(device_key, not current)
        icons.apply(btn, "snail" if not current else "zap", size=14)

    def _build_remove_source_button(self, row):
        btn = QPushButton()
        btn.setObjectName("IconButton")
        btn.setFixedSize(24, 24)
        btn.setToolTip(self.tr("Eliminar este origen…"))
        btn.setCursor(Qt.PointingHandCursor)
        icons.apply(btn, "trash", size=16)
        btn.clicked.connect(lambda: self._delete_source_at_row(row))
        return btn

    def _build_remove_file_button(self, row_item):
        btn = QPushButton()
        btn.setObjectName("IconButton")
        btn.setFixedSize(24, 24)
        btn.setToolTip(self.tr("Quitar de la vista…"))
        btn.setCursor(Qt.PointingHandCursor)
        icons.apply(btn, "trash", size=16)
        btn.clicked.connect(lambda: self._remove_file_row(row_item))
        return btn

    def _remove_file_row(self, row_item):
        row = self.table.indexFromItem(row_item).row()
        if row < 0:
            return
        self.table.removeRow(row)

    def _show_wifi_qr_for_sender(self, sender_name):
        """Abre la ventana QR mostrando el dispositivo de un origen WiFi."""
        if self.current_project_id is None:
            return
        if not self._ensure_wifi_server():
            return
        self._sync_wifi_sessions()
        self._show_wifi_panel()
        if self._wifi_panel is not None:
            self._wifi_panel.select_sender(sender_name)
        self._ensure_wifi_ingestion()

    def _reconfigure_ftp_source(self, session):
        """Reabre el selector FTP con el perfil de este origen preseleccionado."""
        profile_id = ftp.profile_id_from_device_key(
            session.get("device_id") or "")
        self._pick_ftp_source(preset_profile_id=profile_id)

    @staticmethod
    def _drive_label(path):
        if len(path) >= 2 and path[1] == ":":
            return path[:2]
        return os.path.basename(path.rstrip("/\\"))

    def _find_smallest_media(self, source_path):
        exts = {'.mp4','.mov','.mxf','.avi','.m4v','.mkv','.mts','.m2ts',
                '.cr2','.cr3','.nef','.arw','.dng','.jpg','.jpeg','.png','.bmp','.tiff','.tif'}
        candidates = []
        for root, dirs, files in os.walk(source_path):
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in exts:
                    fp = os.path.join(root, f)
                    try:
                        candidates.append((os.path.getsize(fp), fp))
                    except OSError:
                        pass
        if not candidates:
            return None
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]

    def _set_camera_cell_text(self, source_path, text):
        for row in range(self.source_list.rowCount()):
            if row < len(self._source_paths) and self._source_paths[row] == source_path:
                cam_item = self.source_list.item(row, 1)
                if cam_item:
                    self.source_list.blockSignals(True)
                    cam_item.setText(text)
                    self.source_list.blockSignals(False)
                break

    def _camera_for_path(self, source_path):
        camera_map = getattr(self, "_current_camera_map", None)
        if not camera_map:
            return None
        npath = source_path.replace("\\", "/")
        for root, cam in camera_map.items():
            if npath.startswith(root.replace("\\", "/")):
                return cam
        return None

    def _detect_camera_for_session(self, session_id, source_path):
        """Detecta la cámara para una sesión. Flujo I-03+I-14:
        1. Buscar nombre conocido (sd_cards por serial o device_settings por device_id)
        2. Auto-rellenar si se conoce → guardar en sesión y volver
        3. Si no se conoce → detección automática (ffprobe) o prompt manual
        """
        # 1. Buscar cámara conocida (I-03)
        sess = db.get_session(session_id)
        device_id = sess.get("device_id") if sess else None
        known_cam = None
        if device_id and str(device_id).startswith("ftp:"):
            known_cam = db.get_camera_for_device(device_id)
        elif device_id and not str(device_id).startswith("wifi:"):
            known_cam = db.get_camera_for_device(device_id)
        else:
            serial = sd_reader.get_volume_serial(source_path)
            if serial:
                known_cam = db.get_camera_for_card(serial)

        # 2. Auto-rellenar si se conoce (I-03)
        if known_cam:
            db.update_session_config(session_id, camera_name=known_cam)
            self._set_camera_cell_text(source_path, known_cam)
            self._refresh_source_list()
            self._refresh_sessions_combo()
            self.ingest_status_label.setText(self.tr("Cámara conocida: %1").arg(known_cam))
            return

        # 3. Detección automática (I-14): manual no hace nada aquí; el prompt
        # se lanza solo en cambio de origen o registro de dispositivo.
        if self.project_camera_detection_mode == "manual":
            self._set_camera_cell_text(source_path, self.tr("Sin nombre"))
            return

        self._set_camera_cell_text(source_path, "🔄 Escaneando…")
        import threading
        self._cam_timer = QTimer(self)
        self._cam_timer.setSingleShot(True)
        self._cam_detected = None
        self._cam_scan_scheduled = False

        def _apply_detection():
            """Aplica el resultado del scan y muestra prompt (main thread)."""
            if self._cam_scan_scheduled:
                return
            self._cam_scan_scheduled = True
            cam = getattr(self, '_cam_detected', None)
            if cam:
                self._set_camera_cell_text(source_path, cam)
                db.update_session_config(session_id, camera_name=cam)
                self._persist_camera_mapping(session_id, source_path, cam)
                self._refresh_source_list()
                self._refresh_sessions_combo()
                self.ingest_status_label.setText(
                    self.tr("Cámara detectada: %1").arg(cam))
            else:
                self._set_camera_cell_text(source_path, self.tr("Sin nombre"))
            QTimer.singleShot(0, lambda c=cam or "": self._prompt_camera_name(session_id, source_path, c))

        def on_timeout():
            _apply_detection()

        self._cam_timer.timeout.connect(on_timeout)
        self._cam_timer.start(self.project_camera_detection_timeout * 1000)

        def scan():
            smallest = self._find_smallest_media(source_path)
            if smallest is None:
                self._cam_detected = None
                QTimer.singleShot(0, _apply_detection)
                return
            try:
                meta = metadata_engine.get_video_metadata(smallest)
                cam = meta.get("camera_model", "") or ""
                if cam and cam.strip() and cam != "Unknown":
                    self._cam_detected = cam.strip()
                    QTimer.singleShot(0, _apply_detection)
                    return
            except Exception:
                pass
            self._cam_detected = None
            QTimer.singleShot(0, _apply_detection)

        self._cam_done = False
        t = threading.Thread(target=scan, daemon=True)
        t.start()

    def _prompt_camera_name(self, session_id, source_path, suggested_name=""):
        """Prompt manual para nombre de cámara (I-14)."""
        self.raise_()
        self.activateWindow()
        base = self._drive_label(source_path)
        name, ok = QInputDialog.getText(
            self, self.tr("Nombre de cámara"),
            self.tr("Introduce el nombre de la cámara para %1:").arg(base),
            text=suggested_name,
        )
        if ok and name.strip():
            cam = name.strip()
            db.update_session_config(session_id, camera_name=cam)
            self._set_camera_cell_text(source_path, cam)
            self._persist_camera_mapping(session_id, source_path, cam)
        else:
            db.update_session_config(session_id, camera_name=None)
            self._set_camera_cell_text(source_path, self.tr("Sin nombre"))
        self._refresh_source_list()
        self._refresh_sessions_combo()
        self.ingest_status_label.setText(
            self.tr("Cámara: %1").arg(cam if ok and name.strip() else self.tr("Sin nombre"))
        )

    def _persist_camera_mapping(self, session_id, source_path, camera_name):
        """Persiste el mapeo cámara→dispositivo en sd_cards o device_settings (I-03)."""
        if not camera_name:
            return
        sess = db.get_session(session_id)
        if not sess:
            return
        device_id = sess.get("device_id")
        if device_id and not str(device_id).startswith("wifi:"):
            db.save_device_camera(device_id, camera_name)
        else:
            serial = sd_reader.get_volume_serial(source_path)
            if serial:
                db.save_card_camera(serial, camera_name)

    def _scan_all_cameras(self):
        if self.current_project_id is None:
            return
        sessions = db.get_sessions(self.current_project_id)
        count = 0
        for s in sessions:
            sp = s.get("source_path")
            if not sp or not os.path.isdir(sp):
                continue
            if self.project_camera_detection_mode == "manual":
                db.update_session_config(s["id"], camera_name=None)
                count += 1
            elif not s.get("camera_name"):
                self._detect_camera_for_session(s["id"], sp)
                count += 1
        if count:
            self._refresh_source_list()
            self._refresh_sessions_combo()
            self.ingest_status_label.setText(self.tr("Escaneo de cámaras: %1 sesion(es) procesada(s).").arg(count))

    def _on_camera_cell_edited(self, item):
        row = item.row()
        if row < 0 or row >= len(self._source_paths):
            return
        path = self._source_paths[row]
        sessions = db.get_sessions(self.current_project_id)
        session = next((s for s in sessions if s.get("source_path") == path), None)
        if not session:
            return
        new_name = item.text().strip()
        db.update_session_config(session["id"], camera_name=new_name or None)
        self._refresh_sessions_combo()
        self.ingest_status_label.setText(self.tr("Cámara: %1").arg(new_name or self.tr("Sin nombre")))

    def _show_source_context_menu(self, pos):
        row = self.source_list.rowAt(pos.y())
        if row < 0:
            return
        menu = QMenu(self)
        delete_action = menu.addAction(self.tr("Eliminar origen…"))
        delete_action.triggered.connect(
            lambda: self._delete_source_at_row(row))
        menu.exec(self.source_list.viewport().mapToGlobal(pos))

    def _delete_source_at_row(self, row):
        if row < 0 or row >= len(self._source_paths):
            return
        path = self._source_paths[row]
        if self.current_project_id is None:
            return
        sessions = [s for s in db.get_sessions(self.current_project_id)
                    if s.get("source_path") == path]
        if not sessions:
            return
        names = ", ".join(s["name"] for s in sessions)
        reply = QMessageBox.question(
            self, self.tr("Eliminar origen"),
            self.tr("¿Quitar el origen '%1' de la lista?\n"
                    "Las sesiones se mantienen guardadas.")
            .arg(path).arg(names),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._hide_source_path(path)

    def _remove_source_path(self, path):
        """Borra las sesiones de un origen y, si es WiFi, también su remitente."""
        sessions = [s for s in db.get_sessions(self.current_project_id)
                    if s.get("source_path") == path]
        for s in sessions:
            sid = s["id"]
            ing = self._wifi_ingestors.pop(sid, None)
            if ing is not None:
                try:
                    ing.stop()
                except Exception:
                    pass
            db.delete_session(sid)
            # Si es un origen WiFi, elimina el remitente asociado para que
            # _sync_wifi_sessions no lo recree.
            if s.get("device_id") == "wifi:pairdrop":
                folder = s.get("device_folder") or ""
                for sender in db.list_inbox_senders():
                    if (inboxmod.sanitize_alias(sender["name"]) == folder):
                        db.delete_inbox_sender(sender["id"])
                        break
        if path in self._source_paths:
            self._source_paths.remove(path)
        self._populate_source_paths_from_sessions()
        self._refresh_source_list()
        self._refresh_sessions_combo()
        self.update_start_button_state()
        if self._wifi_panel is not None:
            self._wifi_panel.refresh()
        self.ingest_status_label.setText(
            self.tr("Origen eliminado: %1").arg(path))

    def _hide_source_path(self, path):
        """Quita un origen de la lista visual sin borrar sus sesiones en DB."""
        if path in self._source_paths:
            self._source_paths.remove(path)
        self._refresh_source_list()
        self._refresh_sessions_combo()
        self.update_start_button_state()
        self.ingest_status_label.setText(
            self.tr("Origen ocultado: %1").arg(path))

    def _on_source_check_changed(self, item):
        if self.current_project_id is None:
            return
        if item.column() == 1:
            self._on_camera_cell_edited(item)
            return

    def _refresh_sessions_combo(self):
        prev_id = self.sessions_combo.currentData()
        self.sessions_combo.blockSignals(True)
        self.sessions_combo.clear()
        if self.current_project_id is None:
            self.sessions_combo.blockSignals(False)
            self.btn_delete_session.setEnabled(False)
            self.session_src_label.setText("")
            self._btn_browse_sess_src.setVisible(False)
            self.session_dest_label.setText(self.tr("Por defecto"))
            self._btn_browse_sess_dest.setVisible(False)
            return
        sessions = db.get_sessions(self.current_project_id)
        if not sessions:
            self.sessions_combo.addItem(self.tr("(Sin sesiones)"), None)
            self.sessions_combo.blockSignals(False)
            self.btn_delete_session.setEnabled(False)
            return
        for idx, s in enumerate(sessions, start=1):
            status_fmt = "●" if s["status"] == "active" else "○"
            src = s.get("source_path") or ""
            label = f"{status_fmt} #{idx} - {s['name']}"
            if src and f"({self._drive_label(src)})" not in s.get("name", ""):
                label += f" ({self._drive_label(src)})"
            self.sessions_combo.addItem(label, s["id"])
        if prev_id is not None:
            idx = self.sessions_combo.findData(prev_id)
            if idx >= 0:
                self.sessions_combo.setCurrentIndex(idx)
        elif len(sessions) > 0:
            self.sessions_combo.setCurrentIndex(0)
            self._on_session_selected(0)
        self.sessions_combo.blockSignals(False)
        self.btn_delete_session.setEnabled(True)

    def _on_session_selected(self, index):
        session_id = self.sessions_combo.itemData(index)
        if session_id is None:
            self.current_session_id = None
            self.btn_delete_session.setEnabled(False)
            self.session_src_label.setText("")
            self._btn_browse_sess_src.setVisible(False)
            self.session_dest_label.setText(self.tr("Por defecto"))
            self._btn_browse_sess_dest.setVisible(False)
            return
        self.current_session_id = session_id
        self.btn_delete_session.setEnabled(True)
        session = db.get_session(session_id)
        if not session:
            return
        managed = self._is_managed_session(session)
        # El origen de cualquier sesión se puede cambiar desde el selector
        # (otro remitente WiFi, una carpeta…), también en las gestionadas.
        self._btn_browse_sess_src.setVisible(True)
        self._btn_browse_sess_dest.setVisible(True)
        src = session.get("source_path") or ""
        if managed and src:
            # Muestra el nombre del dispositivo (cámara/móvil) en lugar de la
            # ruta técnica de la caché local (B-02).
            name = session.get("camera_name") or session.get("device_folder") or ""
            if name:
                text = self.tr("Origen automático: %1").arg(name)
            else:
                text = self.tr("Origen automático: %1").arg(src)
        else:
            text = (self.tr("Origen: %1").arg(src) if src
                    else self.tr("Origen: sin origen (no se ejecutará)"))
        self.session_src_label.setText(text)
        self.session_src_label.setToolTip(text)
        dest = session.get("destination_override")
        self.session_dest_label.setText(dest if dest else self.tr("Por defecto"))
        self.session_dest_label.setToolTip(dest or "")

    def _add_manual_session(self):
        if self.current_project_id is None:
            QMessageBox.information(self, self.tr("Sin proyecto"), self.tr("Selecciona un proyecto primero."))
            return
        name, ok = QInputDialog.getText(
            self, self.tr("Nueva Sesión manual"),
            self.tr("Nombre de la sesión:"),
            text="Sesión " + datetime.now().strftime("%Y-%m-%d")
        )
        if not ok or not name.strip():
            return
        session_id = db.create_session(
            self.current_project_id, name.strip(),
            QDate.currentDate().toString("yyyy-MM-dd"), "active"
        )
        self._refresh_sessions_combo()
        idx = self.sessions_combo.findData(session_id)
        if idx >= 0:
            self.sessions_combo.setCurrentIndex(idx)
        self.ingest_status_label.setText(self.tr("Sesión manual '%1' creada (ID: %2)").arg(name.strip()).arg(session_id))

    def _delete_current_session(self):
        if self.current_session_id is None:
            return
        sid = self.current_session_id
        reply = QMessageBox.question(
            self, self.tr("Eliminar sesión"),
            self.tr("¿Eliminar la sesión #%1 y sus registros de ingesta?\n"
                    "Los archivos en disco se conservan.\n"
                    "Esta acción no se puede deshacer.").arg(sid),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.No:
            return
        db.delete_session(sid)
        self.current_session_id = None
        self._refresh_sessions_combo()
        self._refresh_source_list()
        self.ingest_status_label.setText(self.tr("Sesión #%1 eliminada.").arg(sid))

    def _on_session_dest_type_changed(self, index):
        pass

    def _save_session_override(self):
        if self.current_session_id is None:
            return
        dest_text = self.session_dest_label.text().strip()
        is_custom = dest_text and dest_text != self.tr("Por defecto")
        kw = {
            "destination_override": dest_text if is_custom else None,
        }
        db.update_session_config(self.current_session_id, **kw)

    def _browse_session_dest(self):
        current = self.session_dest_label.text().strip()
        if current == self.tr("Por defecto"):
            current = ""
        path = QFileDialog.getExistingDirectory(
            self, self.tr("Seleccionar destino de sesión"),
            current or self.dest_root or os.path.expanduser("~")
        )
        if path:
            self.session_dest_label.setText(path)
            self.session_dest_label.setToolTip(path)
            self._save_session_override()

    def _browse_session_src(self):
        if self.current_session_id is None:
            return
        choice = self._pick_source_entry()
        if choice is None:
            return
        kind, value = choice
        if kind == "browse":
            path = QFileDialog.getExistingDirectory(
                self, self.tr("Seleccionar origen de sesión"),
                os.path.expanduser("~")
            )
            if path:
                self._assign_session_folder(self.current_session_id, path)
        elif kind == "folder":
            self._assign_session_folder(self.current_session_id, value)
        elif kind == "sender":
            self._bind_wifi_sender(value, session_id=self.current_session_id)
        elif kind == "ftp_profile":
            self._pick_ftp_source(preset_profile_id=value)

    def build_menu(self):
        menu_bar = self.menuBar()

        m_file = menu_bar.addMenu(self.tr("&Archivo"))

        act_new = QAction(self.tr("&Nuevo Proyecto…"), self)
        act_new.setShortcut("Ctrl+N")
        act_new.triggered.connect(self._show_create_project)
        m_file.addAction(act_new)

        act_refresh = QAction(self.tr("&Recargar proyectos"), self)
        act_refresh.setShortcut("F5")
        act_refresh.triggered.connect(self.load_existing_projects)
        m_file.addAction(act_refresh)

        act_delete_all = QAction(self.tr("&Eliminar todos los proyectos…"), self)
        act_delete_all.triggered.connect(self.delete_all_projects)
        m_file.addAction(act_delete_all)

        m_file.addSeparator()

        act_quit = QAction(self.tr("&Salir"), self)
        act_quit.setShortcut("Ctrl+Q")
        act_quit.triggered.connect(self.close)
        m_file.addAction(act_quit)

        m_ingest = menu_bar.addMenu(self.tr("&Ingesta"))

        act_pick_dest = QAction(self.tr("Seleccionar &destino del proyecto…"), self)
        act_pick_dest.setShortcut("Ctrl+D")
        act_pick_dest.triggered.connect(self.select_dest_path)
        m_ingest.addAction(act_pick_dest)

        m_ingest.addSeparator()

        self.act_auto_detect = QAction(self.tr("Auto-detectar &unidades extraíbles al inicio"), self)
        self.act_auto_detect.setCheckable(True)
        settings = QSettings("Audiovisual Production", "CosechaMedia")
        self.act_auto_detect.setChecked(
            settings.value("autoDetectDrives", False, type=bool)
        )
        self.act_auto_detect.triggered.connect(self._on_auto_detect_toggled)
        m_ingest.addAction(self.act_auto_detect)

        act_detect_sd = QAction(self.tr("Detectar &información de tarjeta SD…"), self)
        act_detect_sd.triggered.connect(self._detect_sd_card)
        m_ingest.addAction(act_detect_sd)

        m_ingest.addSeparator()

        act_dump_targets = QAction(self.tr("Gestionar &destinos de volcado…"), self)
        act_dump_targets.triggered.connect(self._manage_dump_locations)
        m_ingest.addAction(act_dump_targets)

        act_open_data = QAction(self.tr("Abrir carpeta &datos…"), self)
        act_open_data.triggered.connect(self.open_data_folder)
        m_ingest.addAction(act_open_data)

        m_config = menu_bar.addMenu(self.tr("&Configuración"))

        act_cam_detect = QAction(self.tr("Configurar detección de &cámara…"), self)
        act_cam_detect.triggered.connect(self._show_camera_detection_dialog)
        m_config.addAction(act_cam_detect)

        m_config.addSeparator()

        act_footage = QAction(self.tr("Personalizar &carpeta de footage…"), self)
        act_footage.triggered.connect(self._manage_footage_folders)
        m_config.addAction(act_footage)

        act_containers = QAction(self.tr("Personalizar &contenedores de archivos…"), self)
        act_containers.triggered.connect(self._manage_containers)
        m_config.addAction(act_containers)

        self._view_menu = menu_bar.addMenu(self.tr("&Vista"))
        self._theme_menu = self._view_menu.addMenu(self.tr("Tema"))
        self._theme_group = QActionGroup(self)
        self._theme_group.setExclusive(True)
        current_theme = theme.get_theme()
        theme_names = {
            "dark": self.tr("Oscuro"),
            "light": self.tr("Claro"),
        }
        for key in theme.THEMES:
            act = QAction(theme_names.get(key, key), self)
            act.setCheckable(True)
            act.setChecked(key == current_theme)
            act.triggered.connect(lambda checked=False, k=key: self._switch_theme(k))
            self._theme_group.addAction(act)
            self._theme_menu.addAction(act)

        self._accent_menu = self._view_menu.addMenu(self.tr("Acento"))
        self._accent_group = QActionGroup(self)
        self._accent_group.setExclusive(True)
        current_accent = theme.get_accent()
        accent_names = {
            "default": self.tr("Neutro"),
            "green": self.tr("Verde"),
            "blue": self.tr("Azul"),
            "pink": self.tr("Rosa"),
            "purple": self.tr("Morado"),
            "amber": self.tr("Ámbar"),
        }
        for key in theme.ACCENTS:
            act = QAction(accent_names.get(key, key), self)
            act.setCheckable(True)
            act.setChecked(key == current_accent)
            act.triggered.connect(lambda checked=False, k=key: self._switch_accent(k))
            self._accent_group.addAction(act)
            self._accent_menu.addAction(act)

        self._view_menu.addSeparator()
        bg_enabled = settings.value("wheatBg", True, type=bool)
        if not bg_enabled:
            wheat_field.set_enabled(False)
        self._act_wheat_bg = QAction(self.tr("Fondo de trigo"), self)
        self._act_wheat_bg.setCheckable(True)
        self._act_wheat_bg.setChecked(wheat_field.is_enabled())
        self._act_wheat_bg.triggered.connect(self._toggle_wheat_background)
        self._view_menu.addAction(self._act_wheat_bg)

        m_help = menu_bar.addMenu(self.tr("A&yuda"))
        act_check_updates = QAction(self.tr("&Búsqueda de actualizaciones…"), self)
        act_check_updates.triggered.connect(self._check_for_updates)
        m_help.addAction(act_check_updates)
        m_help.addSeparator()
        act_about = QAction(self.tr("&Acerca de…"), self)
        act_about.triggered.connect(self.show_about)
        m_help.addAction(act_about)

        m_lang = menu_bar.addMenu(self.tr("&Idioma"))
        lang_group = QActionGroup(self)
        lang_group.setExclusive(True)
        current_lang = translator.current_language()
        for code, name in translator.LANGUAGES.items():
            act = QAction(name, self)
            act.setCheckable(True)
            act.setChecked(code == current_lang)
            act.triggered.connect(lambda checked=False, c=code: self._switch_language(c))
            lang_group.addAction(act)
            m_lang.addAction(act)

    def _switch_language(self, code):
        if code == translator.current_language():
            return
        translator.set_language(code)
        QMessageBox.information(
            self, self.tr("Idioma"),
            self.tr("Reinicia la aplicación para aplicar el idioma.")
        )

    def _populate_source_paths_from_sessions(self):
        self._source_paths.clear()
        if self.current_project_id is None:
            return
        for s in db.get_sessions(self.current_project_id):
            sp = s.get("source_path")
            if sp and sp not in self._source_paths:
                self._source_paths.append(sp)

    def _add_source_entry(self):
        choice = self._pick_source_entry()
        if choice is not None:
            self._apply_source_choice(choice)

    def _apply_source_choice(self, choice):
        kind, value = choice
        if kind == "browse":
            start_dir = self.source_input.currentText().strip() or os.path.expanduser("~")
            path = QFileDialog.getExistingDirectory(
                self, self.tr("Seleccionar carpeta de la Tarjeta SD"), start_dir
            )
            if path:
                self._assign_folder_source(path)
        elif kind == "folder":
            self._assign_folder_source(value)
        elif kind == "sender":
            self._bind_wifi_sender(value)
        elif kind == "ftp_profile":
            self._pick_ftp_source(preset_profile_id=value)
        elif kind == "device":
            device_id, device_folder, device_name = value
            self._register_device_source_from_picker(
                device_id, device_folder, device_name, backend=mtp.WpdBackend())
        elif kind == "ftp_new":
            profile_id, device_id, device_folder, device_name = value
            self._register_device_source_from_picker(
                device_id, device_folder, device_name, backend=ftp.FtpBackend())
        elif kind == "wifi":
            self._pick_wifi_source()

    def _pick_source_entry(self):
        """Abre el selector unificado de orígenes (guardados y dispositivos).

        Devuelve una tupla ``(kind, value)`` o ``None`` si se cancela.
        ``kind`` puede ser ``"folder"``/``"sender"``/``"ftp_profile"``/
        ``"browse"``/``"device"``/``"ftp_new"``/``"wifi"``.
        """
        if self.current_project_id is None:
            return None
        sessions = db.get_sessions(self.current_project_id)
        folders = []
        for p in db.get_recent_paths("source"):
            if p not in folders:
                folders.append(p)
        for s in sessions:
            sp = s.get("source_path")
            if sp and not self._is_managed_source_path(sp) and sp not in folders:
                folders.append(sp)
        used = {s.get("device_folder") for s in sessions
                if (s.get("device_id") or "").startswith("wifi:")}
        senders = [{"name": s["name"],
                    "used": inboxmod.sanitize_alias(s["name"]) in used}
                   for s in db.list_inbox_senders()]
        dialog = SourcePickerDialog(self, folders=folders, senders=senders,
                                    devices_missing=self._disconnected_devices(),
                                    on_delete=self._delete_saved_source)
        if dialog.exec() != QDialog.Accepted:
            return None
        if dialog.kind is None:
            return None
        return (dialog.kind, dialog.value)

    def _delete_saved_source(self, kind, value):
        """Borra un guardado desde el diálogo «Añadir origen» (B-04).

        Devuelve True si se eliminó (para quitar el elemento de la lista)."""
        if kind == "folder":
            if self.current_project_id is not None:
                in_use = any(s.get("source_path") == value
                             for s in db.get_sessions(self.current_project_id))
                if in_use:
                    QMessageBox.information(
                        self, self.tr("Eliminar origen"),
                        self.tr("La carpeta '%1' está asignada a una sesión; "
                                "elimínala desde la lista de orígenes.")
                        .arg(value))
                    return False
            db.remove_recent_path(value)
            return True
        if kind == "ftp_profile":
            reply = QMessageBox.question(
                self, self.tr("Eliminar perfil FTP"),
                self.tr("¿Eliminar el perfil FTP guardado?"),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply != QMessageBox.Yes:
                return False
            db.delete_ftp_profile(value)
            return True
        if kind == "sender":
            reply = QMessageBox.question(
                self, self.tr("Eliminar remitente WiFi"),
                self.tr("¿Eliminar el remitente WiFi '%1'?").arg(value),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply != QMessageBox.Yes:
                return False
            for s in db.list_inbox_senders():
                if s["name"] == value:
                    db.delete_inbox_sender(s["id"])
                    break
            self._sync_wifi_sessions()
            return True
        if kind == "device":
            reply = QMessageBox.question(
                self, self.tr("Eliminar dispositivo guardado"),
                self.tr("¿Eliminar este dispositivo guardado y sus sesiones?\n"
                        "Los archivos en disco se conservan.\n"
                        "Esta acción no se puede deshacer."),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply != QMessageBox.Yes:
                return False
            if str(value).startswith("ftp:"):
                pid = ftp.profile_id_from_device_key(value)
                if pid is not None:
                    db.delete_ftp_profile(pid)
            db.delete_device(value)
            self._populate_source_paths_from_sessions()
            self._refresh_source_list()
            self._refresh_sessions_combo()
            self.update_start_button_state()
            return True
        return False

    def _disconnected_devices(self):
        """Dispositivos MTP desconectados y perfiles FTP con sesiones en el
        proyecto, para poder borrarlos desde el diálogo unificado (D-12)."""
        if self.current_project_id is None:
            return []
        try:
            current = {dev.device_id for dev in mtp.WpdBackend().list_devices()}
        except Exception:
            current = set()
        known = {}
        for s in db.get_sessions(self.current_project_id):
            did = s.get("device_id") or ""
            if did.startswith("ftp:"):
                # Los FTP no se pueden "desconectar" por USB; se listan
                # siempre que tengan sesiones para poder borrarlos (sustituye
                # a la vía «Configuración → Dispositivos guardados»).
                known.setdefault(did, s.get("camera_name") or "")
            elif did and not did.startswith("wifi:"):
                known.setdefault(did, s.get("camera_name") or "")
        return [{"id": did, "name": known[did] or did}
                for did in sorted(known) if did.startswith("ftp:") or did not in current]

    def _register_device_source_from_picker(self, device_id, device_folder,
                                            device_name, backend):
        """Registra un origen de dispositivo (MTP o FTP) elegido en el diálogo unificado."""
        if self.current_project_id is None:
            QMessageBox.information(
                self, self.tr("Sin proyecto"),
                self.tr("Selecciona o crea un proyecto antes de elegir un dispositivo.")
            )
            return
        cache_dir = mtp.device_cache_dir(device_id, device_folder)
        try:
            os.makedirs(cache_dir, exist_ok=True)
        except OSError:
            cache_dir = mtp.device_cache_dir(device_id, "")
            os.makedirs(cache_dir, exist_ok=True)
        self._register_device_source(
            cache_dir, device_id, device_folder, device_name, backend=backend)

    def _assign_folder_source(self, path):
        """Asigna un folder real como nuevo origen (nunca una caché gestionada)."""
        if self._is_managed_source_path(path):
            self._warn_managed_source(path)
            return
        if path not in self._source_paths:
            self._source_paths.append(path)
            self.source_input.setCurrentText("")
            if self.current_project_id:
                sessions = db.get_sessions(self.current_project_id)
                if not any(s.get("source_path") == path for s in sessions):
                    base = self._drive_label(path)
                    no_source = [s for s in sessions if not s.get("source_path")]
                    if no_source:
                        db.update_session_config(
                            no_source[0]["id"], source_path=path, name=f"Auto ({base})")
                        sid = no_source[0]["id"]
                    else:
                        sid = db.create_session(
                            self.current_project_id, f"Auto ({base})",
                            QDate.currentDate().toString("yyyy-MM-dd"), "active",
                            source_path=path)
                    self._detect_camera_for_session(sid, path)
        self._refresh_source_list()
        self._refresh_sessions_combo()
        self.update_start_button_state()

    def _assign_session_folder(self, session_id, path):
        """Asigna un folder real como origen de una sesión concreta.

        Si la sesión estaba ligada a un dispositivo gestionado (WiFi/FTP/MTP),
        se desliga primero: pasa a ser un origen manual.
        """
        if self._is_managed_source_path(path):
            self._warn_managed_source(path)
            return
        session = db.get_session(session_id)
        if session is None:
            return
        if session.get("source_path") != path:
            if path not in self._source_paths:
                self._source_paths.append(path)
            base = self._drive_label(path)
            db.update_session_config(session_id, source_path=path, name=f"Auto ({base})")
        if session.get("device_id"):
            db.update_session_config(session_id, device_id="", device_folder="")
            self._detect_camera_for_session(session_id, path)
        self._refresh_sessions_combo()
        self.update_start_button_state()

    def _warn_managed_source(self, path):
        sessions = (db.get_sessions(self.current_project_id)
                    if self.current_project_id else [])
        owner = next((s for s in sessions
                      if s.get("source_path")
                      and os.path.normpath(s["source_path"]) == os.path.normpath(path)),
                     None)
        if owner is not None:
            QMessageBox.information(
                self, self.tr("Origen gestionado"),
                self.tr("Ese origen ya está asignado a la sesión #%1.").arg(owner["id"]))
        else:
            QMessageBox.warning(
                self, self.tr("Origen gestionado"),
                self.tr("No puedes usar una caché gestionada como origen manual."))

    def _bind_wifi_sender(self, sender_name, session_id=None):
        """Convierte una sesión en la sesión gestionada de un remitente WiFi.

        El binding es aditivo: el mismo remitente puede volcar en varias
        sesiones del proyecto (cada una con su propio destino/configuración).
        Con ``session_id`` (selector de sesión) convierte esa sesión concreta;
        sin él (origen nuevo) reutiliza una sesión sin origen o crea la WiFi.
        """
        if self.current_project_id is None:
            return
        if sender_name not in {s["name"] for s in db.list_inbox_senders()}:
            return
        alias = inboxmod.sanitize_alias(sender_name)
        cache = inboxmod.wifi_cache_dir(sender_name)
        sessions = db.get_sessions(self.current_project_id)

        def _wifi_sessions():
            return [s for s in db.get_sessions(self.current_project_id)
                    if (s.get("device_id") or "").startswith("wifi:")
                    and s.get("device_folder") == alias]

        existing = _wifi_sessions()
        if session_id is None:
            if existing:
                session_id = existing[0]["id"]
            else:
                no_source = next((s for s in sessions if not s.get("source_path")), None)
                if no_source is not None:
                    session_id = no_source["id"]
                else:
                    session_id = db.get_or_create_wifi_session(
                        self.current_project_id, sender_name, cache, "")
                    self._after_bind(session_id)
                    return
        target = next((s for s in sessions if s["id"] == session_id), None)
        if target is None:
            return
        # Cambio de origen: si la sesión estaba ligada a OTRO remitente, se
        # desliga de él (sus demás sesiones no se tocan) antes de ligar el nuevo.
        cur_did = target.get("device_id") or ""
        cur_folder = target.get("device_folder") or ""
        if cur_did.startswith("wifi:") and cur_folder and cur_folder != alias:
            db.update_session_config(session_id, device_id="", device_folder="",
                                     camera_name=None)
        other = next((s for s in _wifi_sessions() if s["id"] != session_id), None)
        if other is not None:
            QMessageBox.information(
                self, self.tr("Origen compartido"),
                self.tr("El remitente '%1' ya está asignado a la sesión #%2.\n"
                        "Se añadirá también a la sesión #%3.")
                .arg(sender_name).arg(other["id"]).arg(session_id))
        db.update_session_config(
            session_id, device_id=WIFI_DEVICE_ID, device_folder=alias,
            camera_name=sender_name, source_path=cache, enabled=1)
        self._after_bind(session_id)

    def _after_bind(self, session_id):
        self._populate_source_paths_from_sessions()
        self._refresh_source_list()
        self._refresh_sessions_combo()
        idx = self.sessions_combo.findData(session_id)
        if idx >= 0:
            self.sessions_combo.setCurrentIndex(idx)
        self.update_start_button_state()
        self.ingest_status_label.setText(
            self.tr("Origen WiFi asignado a la sesión #%1").arg(session_id))

    def _pick_wifi_source(self):
        # Import local: los tests parchean app.ui.wifi_picker.WifiMethodDialog.
        from app.ui.wifi_picker import WifiMethodDialog
        dialog = WifiMethodDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return
        if dialog.method == "ftp":
            self._pick_ftp_source()
        elif dialog.method == "pairdrop":
            self._open_wifi_panel(force_new_sender=True)

    # -- WiFi / PairDrop: origen en la tabla + ventana flotante QR --------

    def _open_wifi_panel(self, force_new_sender: bool = False):
        """Configura un QR (nuevo remitente) y abre la ventana flotante.

        Con ``force_new_sender`` (botón WiFi…) siempre pide crear un nuevo
        remitente (un QR nuevo), en vez de reabrir el existente.
        """
        if self.current_project_id is None:
            return
        if not self._ensure_wifi_server():
            return
        if force_new_sender:
            sender = self._prompt_wifi_sender()
            if sender is None:
                return
        elif not db.list_inbox_senders():
            # Si no hay remitentes, pide crear el primero (un origen WiFi más).
            if self._prompt_wifi_sender() is None:
                return
            sender = db.list_inbox_senders()[-1]["name"]
        else:
            sender = None
        self._sync_wifi_sessions()
        self._show_wifi_panel()
        if self._wifi_panel is not None and sender:
            self._wifi_panel.select_sender(sender)
        self._ensure_wifi_ingestion()

    def _prompt_wifi_sender(self):
        """Abre el diálogo de nuevo remitente; devuelve su nombre o None."""
        if self.current_project_id is None:
            QMessageBox.information(
                self, self.tr("Sin proyecto"),
                self.tr("Selecciona un proyecto primero."))
            return None
        dlg = SenderEditDialog(
            self,
            title=self.tr("Añadir dispositivo WiFi"),
            name_label=self.tr(
                "Nombre del dispositivo (aparecerá en el código QR):"),
            name_hint=self.tr("Ej.: Móvil de Joan"),
        )
        if dlg.exec() != QDialog.Accepted:
            return None
        name = dlg.name_edit.text().strip()
        if not name:
            return None
        db.add_inbox_sender(name)
        self._sync_wifi_sessions()
        return name

    def _ensure_wifi_server(self) -> bool:
        if self._wifi_server is not None and self._wifi_server.running:
            return True
        folder_mode = self._get_wifi_folder_mode()
        self._wifi_server = inboxmod.ShootInboxServer(
            page_dark=(theme.get_theme() != "light"),
            folder_mode=folder_mode)
        try:
            self._wifi_server.start()
        except OSError as e:
            QMessageBox.warning(
                self, self.tr("WiFi"),
                self.tr("No se pudo iniciar el servidor: %1").arg(str(e)))
            self._wifi_server = None
            return False
        return True

    def _get_wifi_folder_mode(self) -> bool:
        if self.current_project_id is None:
            return False
        sessions = [s for s in db.get_sessions(self.current_project_id)
                    if s.get("device_id") == "wifi:pairdrop"]
        for s in sessions:
            if s.get("folder_mode"):
                return True
        return False

    def _show_wifi_panel(self):
        if self._wifi_panel is None:
            self._wifi_panel = ShootInboxPanel(self)
            self._wifi_panel.received.connect(self._on_wifi_file_received)
            self._wifi_panel.stop_requested.connect(self._stop_wifi_reception)
            self._wifi_panel.resume_requested.connect(self._resume_wifi_reception)
        if self._wifi_server is not None and self._wifi_server.running:
            self._wifi_panel.attach_server(self._wifi_server)
        self._wifi_panel.refresh()
        self._wifi_panel.show()
        self._wifi_panel.raise_()
        self._wifi_panel.activateWindow()

    def _sync_wifi_sessions(self):
        """Crea/elimina las sesiones fuente WiFi del proyecto (una por remitente)
        y refresca la tabla de orígenes."""
        if self.current_project_id is None:
            return
        senders = db.list_inbox_senders()
        existing = [(s["device_folder"], s["id"])
                    for s in db.list_wifi_sessions(self.current_project_id)]
        keep = set()
        for s in senders:
            folder = inboxmod.sanitize_alias(s["name"])
            cache = inboxmod.wifi_cache_dir(s["name"])
            # La ubicación/destino del dispositivo NO se propaga entre
            # proyectos: cada proyecto vuelca a su propia ruta maestra.
            sid = db.get_or_create_wifi_session(
                self.current_project_id, s["name"], cache, "")
            keep.add(folder)
            if cache not in self._source_paths:
                self._source_paths.append(cache)
        # Elimina TODAS las sesiones de remitentes que ya no existen (un
        # remitente puede estar compartido por varias sesiones del proyecto).
        for folder, sid in existing:
            if folder not in keep:
                db.delete_session(sid)
                ing = self._wifi_ingestors.pop(sid, None)
                if ing is not None:
                    ing.stop()
        self._populate_source_paths_from_sessions()
        self._refresh_source_list()
        self._refresh_sessions_combo()
        self.update_start_button_state()

    def _ingestor_for_wifi_session(self, session) -> "Ingestor":
        """Construye un Ingestor configurado para una sesión WiFi concreta."""
        sid = session["id"]
        s_folder = session.get("folder_name") or self.project_folder_name or "Footage"
        s_org_raw = session.get("organization_type")
        s_org = self.project_organization_type if s_org_raw is None else s_org_raw
        s_dur = session.get("duration_type")
        s_dur = self.project_duration_type if s_dur is None else s_dur
        s_cam = session.get("default_camera")
        s_cam = self.project_default_camera if s_cam is None else s_cam
        s_use_meta = session.get("use_metadata_date")
        s_use_meta = self.project_use_metadata_date if s_use_meta is None else s_use_meta
        device_key = session.get("device_id") or session.get("source_path") or ""
        dev_delicate = db.get_device_delicate(device_key)
        if dev_delicate is not None:
            s_delicate = bool(dev_delicate)
        else:
            s_delicate = self.project_delicate_mode
        s_content_filter = None
        try:
            raw_filter = session.get("content_filter")
            if raw_filter:
                s_content_filter = json.loads(raw_filter)
        except (TypeError, ValueError):
            s_content_filter = None
        dest_root = session.get("destination_override") or self.dest_root
        sess_targets = None
        if not session.get("destination_override"):
            sess_targets = [DumpTarget(l["id"], l["path"], l["include_date"], l["include_camera"])
                            for l in db.dump_locations(self.current_project_id)
                            if l["path"] and os.path.isdir(l["path"])] or None
        camera_map = getattr(self, "_current_camera_map", None) or {}
        camera_map = dict(camera_map)
        # El origen WiFi se etiqueta con la cámara del remitente (su nombre),
        # aunque nunca se haya pulsado «Iniciar Ingesta» (que es donde se
        # construye el mapa global). Así los subdirectorios de la caché del
        # remitente no caen en "Unknown".
        sp = session.get("source_path")
        cn = session.get("camera_name")
        if sp and cn:
            camera_map[os.path.normpath(sp)] = cn
        ing = Ingestor(
            self.current_project_id, dest_root,
            folder_name=s_folder, use_metadata_date=bool(s_use_meta),
            order_type=ORG_TYPE_MAP.get(s_org, "camera_first"),
            duration_type=s_dur, default_camera=s_cam,
            delicate_mode=bool(s_delicate), session_id=sid,
            camera_map=camera_map,
            manual_date=self.project_date.toString("yyyy-MM-dd"),
            dump_targets=sess_targets, project_master_root=self.dest_root,
            content_filter=s_content_filter,
        )
        ing.file_started.connect(
            lambda sp, i=ing: self.on_file_started(sp, ingestor=i)
        )
        ing.copy_progress.connect(
            lambda sp, cb, tb, i=ing: self.on_copy_progress(sp, cb, tb, ingestor=i)
        )
        ing.file_finished.connect(
            lambda sp, dp, ok, md, i=ing: self.on_file_finished(sp, dp, ok, md, ingestor=i)
        )
        ing.ingest_complete.connect(
            lambda stats, i=ing: self._on_wifi_ingestor_complete(stats, i)
        )
        ing.camera_rename_needed.connect(self._on_camera_rename_needed)
        return ing

    def _on_wifi_ingestor_complete(self, stats, ingestor):
        """Al terminar la ingesta WiFi de un remitente sin errores, vacía la
        caché que quede (archivos ya ingeridos en pasadas anteriores).

        Solo se vacía cuando es el último ingestor activo del remitente: con
        el mismo origen compartido por varias sesiones, la primera en terminar
        no puede borrar la caché antes de que las demás la hayan ingerido.
        """
        if ingestor.session_id is not None and (stats.get("errors") or 0) == 0:
            if self._wifi_cache_safe_to_clear(ingestor):
                self._clear_wifi_cache(ingestor.session_id)

    def _wifi_cache_safe_to_clear(self, ingestor):
        """True si ningún otro ingestor del mismo remitente sigue activo."""
        sid = ingestor.session_id
        if sid is None or self.current_project_id is None:
            return True
        session = next((s for s in db.list_wifi_sessions(self.current_project_id)
                        if s["id"] == sid), None)
        if not session:
            return True
        folder = session["device_folder"]
        for s in db.list_wifi_sessions(self.current_project_id):
            if s["device_folder"] != folder or s["id"] == sid:
                continue
            other = self._wifi_ingestors.get(s["id"])
            if other is not None and not other.is_idle():
                return False
        return True

    def _start_wifi_ingestor(self, sid):
        if sid in self._wifi_ingestors:
            return self._wifi_ingestors[sid]
        session = db.get_session(sid)
        if not session or not session.get("source_path"):
            return None
        if not session.get("enabled", True):
            return None
        ing = self._ingestor_for_wifi_session(session)
        self._wifi_ingestors[sid] = ing
        self._scan_wifi_cache(sid, session["source_path"])
        return ing

    def _scan_wifi_cache(self, sid, cache_dir):
        """Ingiere los archivos ya presentes en la caché del remitente."""
        if not cache_dir or not os.path.isdir(cache_dir):
            return
        ing = self._wifi_ingestors.get(sid)
        if ing is None:
            return
        for root, dirs, files in os.walk(cache_dir):
            dirs[:] = [d for d in dirs if not _is_system_entry(d)]
            for f in files:
                if _is_system_entry(f) or f.startswith("."):
                    continue
                ing.handle_new_file(os.path.join(root, f))

    def _ensure_wifi_ingestion(self):
        """Arranca un Ingestor por cada sesión WiFi y escanea la caché."""
        if self.current_project_id is None:
            return
        for s in db.list_wifi_sessions(self.current_project_id):
            self._start_wifi_ingestor(s["id"])

    def _is_inbox_cache_path(self, path):
        """True si ``path`` está dentro de la caché WiFi (``data/inbox``)."""
        root = os.path.abspath(inboxmod.inbox_root(db))
        npath = os.path.abspath(path)
        return npath != root and npath.startswith(root + os.sep)

    def _remove_ingested_wifi_source(self, source_path):
        """Borra de la caché un archivo recibido por WiFi ya ingerido y poda
        las carpetas vacías hasta la caché de su remitente."""
        if not self._is_inbox_cache_path(source_path):
            return
        try:
            if os.path.isfile(source_path):
                os.remove(source_path)
        except OSError:
            return
        root = os.path.abspath(inboxmod.inbox_root(db))
        parent = os.path.dirname(os.path.abspath(source_path))
        while parent and parent != root and os.path.isdir(parent):
            try:
                os.rmdir(parent)
            except OSError:
                break
            parent = os.path.dirname(parent)

    def _clear_wifi_cache(self, session_id):
        """Borra los archivos restantes de la caché de un remitente (ya
        ingeridos en una pasada anterior) y poda sus directorios vacíos."""
        sessions = db.list_wifi_sessions(self.current_project_id) \
            if self.current_project_id is not None else []
        session = next((s for s in sessions if s["id"] == session_id), None)
        cache = (session or {}).get("source_path")
        if not cache or not os.path.isdir(cache):
            return
        root = os.path.abspath(cache)
        for base, dirs, files in os.walk(root, topdown=False):
            for f in files:
                try:
                    os.remove(os.path.join(base, f))
                except OSError:
                    pass
            try:
                os.rmdir(base)
            except OSError:
                pass

    def _on_wifi_file_received(self, alias, path, size):
        if self.current_project_id is None:
            return
        for s in db.list_wifi_sessions(self.current_project_id):
            if s["device_folder"] != alias:
                continue
            if s["id"] not in self._wifi_ingestors:
                self._start_wifi_ingestor(s["id"])
            ing = self._wifi_ingestors.get(s["id"])
            if ing is not None:
                ing.handle_new_file(path)

    def _stop_wifi_reception(self):
        for ing in self._wifi_ingestors.values():
            try:
                ing.stop()
            except Exception:
                pass
        self._wifi_ingestors = {}
        if self._wifi_server is not None:
            try:
                self._wifi_server.stop()
            except Exception:
                pass
            self._wifi_server = None
        if self._wifi_panel is not None:
            self._wifi_panel.refresh()
            self._wifi_panel.set_server_status(
                self.tr("Recepción detenida. Pulsa «Reanudar» para continuar."))
        self.ingest_status_label.setText(self.tr("Recepción WiFi detenida."))

    def _resume_wifi_reception(self):
        if self.current_project_id is None:
            return
        if not self._ensure_wifi_server():
            return
        self._show_wifi_panel()
        self._ensure_wifi_ingestion()
        if self._wifi_panel is not None:
            self._wifi_panel.refresh()
            self._wifi_panel.set_server_status(
                self.tr("Recepción WiFi reanudada."))
        self.ingest_status_label.setText(self.tr("Recepción WiFi reanudada."))

    def _reset_wifi_ingestors(self):
        for ing in self._wifi_ingestors.values():
            try:
                ing.stop()
            except Exception:
                pass
        self._wifi_ingestors = {}


    def _pick_ftp_source(self, preset_profile_id=None):
        dialog = FtpPickerDialog(self, preset_profile_id=preset_profile_id)
        if dialog.exec() != QDialog.Accepted:
            return
        if not dialog.device_id or not dialog.device_folder:
            return
        if self.current_project_id is None:
            QMessageBox.information(
                self, self.tr("Sin proyecto"),
                self.tr("Selecciona o crea un proyecto antes de elegir un dispositivo.")
            )
            return
        cache_dir = mtp.device_cache_dir(dialog.device_id, dialog.device_folder)
        try:
            os.makedirs(cache_dir, exist_ok=True)
        except OSError:
            cache_dir = mtp.device_cache_dir(dialog.device_id, "")
            os.makedirs(cache_dir, exist_ok=True)
        self._register_device_source(
            cache_dir, dialog.device_id, dialog.device_folder, dialog.device_name,
            backend=ftp.FtpBackend(),
        )

    def _register_device_source(self, cache_dir, device_id, device_folder, device_name, backend=None):
        if cache_dir not in self._source_paths:
            self._source_paths.append(cache_dir)
            self.source_input.setCurrentText("")
        sessions = db.get_sessions(self.current_project_id)
        existing = next((s for s in sessions if s.get("source_path") == cache_dir), None)
        if existing:
            db.update_session_config(
                existing["id"],
                device_id=device_id, device_folder=device_folder,
                source_path=cache_dir,
            )
            sid = existing["id"]
        else:
            base = device_name or self._drive_label(cache_dir)
            no_source = [s for s in sessions if not s.get("source_path")]
            if no_source:
                sid = no_source[0]["id"]
                db.update_session_config(
                    sid, source_path=cache_dir, name=f"Auto ({base})",
                    device_id=device_id, device_folder=device_folder,
                )
            else:
                sid = db.create_session(
                    self.current_project_id, f"Auto ({base})",
                    QDate.currentDate().toString("yyyy-MM-dd"), "active",
                    source_path=cache_dir,
                )
                db.update_session_config(sid, device_id=device_id, device_folder=device_folder)
        self._refresh_source_list()
        self._refresh_sessions_combo()
        self.update_start_button_state()
        self._stage_device_in_background(device_id, device_folder, sid, cache_dir, backend=backend)

    def _stage_device_in_background(self, device_id, device_folder, session_id, cache_dir,
                                    backend=None, silent=False):
        backend = backend or mtp.WpdBackend()
        worker = _StageWorker(backend, device_id, device_folder)
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self._on_stage_progress)
        worker.done.connect(lambda ok, res, w=worker, t=thread, sid=session_id, cdir=cache_dir, sil=silent:
                            self._on_stage_done(ok, res, w, t, sid, cdir, silent=sil))
        thread.finished.connect(thread.deleteLater)
        self._stage_thread = thread
        self._stage_worker = worker
        self.ingest_status_label.setText(
            self.tr("Sincronizando dispositivo (primera pasada)…")
        )
        thread.start()

    def _on_stage_progress(self, message):
        self.ingest_status_label.setText(message)

    def _on_stage_done(self, ok, res, worker, thread, session_id, cache_dir, silent=False):
        if not ok:
            if silent:
                self.ingest_status_label.setText(self.tr("Dispositivo no disponible"))
            else:
                QMessageBox.warning(
                    self, self.tr("Dispositivo"),
                    self.tr("No se pudo sincronizar el dispositivo: %1").arg(str(res)),
                )
                self.ingest_status_label.setText(self.tr("Listo"))
            thread.quit()
            return
        staged = res.get("staged", 0)
        skipped = res.get("skipped", 0)
        errors = res.get("errors", 0)
        self._refresh_source_list()
        self._refresh_sessions_combo()
        self.update_start_button_state()
        self.ingest_status_label.setText(
            self.tr("Dispositivo sincronizado: %1 nuevos, %2 sin cambios, %3 errores.")
            .arg(staged).arg(skipped).arg(errors)
        )
        self._detect_camera_for_session(session_id, cache_dir)
        thread.quit()

    def select_dest_path(self):
        if self.current_project_id is None:
            QMessageBox.information(
                self, self.tr("Sin proyecto"),
                self.tr("Selecciona o crea un proyecto antes de cambiar su destino.")
            )
            return
        path = QFileDialog.getExistingDirectory(
            self, self.tr("Seleccionar carpeta maestra del proyecto"),
            self.dest_root or os.path.expanduser("~")
        )
        if path:
            if os.path.abspath(path) == os.path.abspath(self.dest_root or ""):
                return
            self._save_project_root(path)

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

        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM dump_locations WHERE project_id = ?', (self.current_project_id,))
            cursor.execute('DELETE FROM files WHERE session_id IN (SELECT id FROM sessions WHERE project_id = ?)', (self.current_project_id,))
            cursor.execute('DELETE FROM sessions WHERE project_id = ?', (self.current_project_id,))
            cursor.execute('DELETE FROM cameras WHERE project_id = ?', (self.current_project_id,))
            cursor.execute('DELETE FROM projects WHERE id = ?', (self.current_project_id,))
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

        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM dump_locations')
            cursor.execute('DELETE FROM files')
            cursor.execute('DELETE FROM sessions')
            cursor.execute('DELETE FROM cameras')
            cursor.execute('DELETE FROM projects')
            cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('projects', 'sessions', 'cameras', 'files', 'dump_locations')")
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

    def _open_selective_dump(self):
        if self.current_project_id is None:
            QMessageBox.information(
                self, self.tr("Sin proyecto"),
                self.tr("Selecciona o crea un proyecto antes de hacer un volcado selectivo."))
            return
        source = self.source_input.currentText().strip() or (self._source_paths[0] if self._source_paths else "")
        project_config = {
            "dest_root": self.dest_root or "",
            "folder_name": self.project_folder_name or "Footage",
            "organization_type": self.project_organization_type,
            "default_camera": self.project_default_camera or "",
            "project_id": self.current_project_id,
            "use_metadata_date": self.project_use_metadata_date,
        }
        dialog = SelectiveDumpAssistant(self, source_path=source, project_config=project_config)
        dialog.exec()

    def _open_content_filter(self, row):
        if self.current_project_id is None:
            return
        if row < 0 or row >= len(self._source_paths):
            return
        path = self._source_paths[row]
        session = next((s for s in db.get_sessions(self.current_project_id)
                        if s.get("source_path") == path), None)
        if not session:
            QMessageBox.information(
                self, self.tr("Aviso"),
                self.tr("Activa el origen para configurar su contenido."))
            return
        dialog = SelectiveDumpAssistant(self, source_path=path, mode="filter")
        if dialog.exec() == QDialog.Accepted:
            filt = dialog.content_filter
            db.update_session_config(
                session["id"], content_filter=json.dumps(filt) if filt else None)
            self._refresh_source_list()
            self.ingest_status_label.setText(
                self.tr("Contenido del origen %1: %2").arg(path).arg(dialog.content_text))

    def _check_for_updates(self):
        AboutDialog(self, check_updates=True).exec()

    def _run_startup_update_check(self):
        self._run_background(lambda progress: updater.check_for_updates(), self._on_startup_update_check)

    def _on_startup_update_check(self, success, payload):
        if not success or not payload.get("update_available"):
            return
        reply = QMessageBox.question(
            self, self.tr("Actualización disponible"),
            self.tr("Hay una nueva versión de CosechaMedia disponible: %1. ¿Quieres ver los detalles?")
            .arg(payload["latest_version"]),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes,
        )
        if reply == QMessageBox.Yes:
            self._check_for_updates()

    def _detect_sd_card(self):
        if not self._source_paths and not self.source_input.currentText().strip():
            QMessageBox.information(self, self.tr("Sin origen"), self.tr("Selecciona o añade una ruta de tarjeta SD primero."))
            return
        path = self._source_paths[0] if self._source_paths else self.source_input.currentText().strip()
        info = sd_reader.detect_card_info(path)
        lines = []
        if info["brand"]:
            lines.append(self.tr("Marca: %1").arg(info["brand"]))
        if info["model"]:
            lines.append(self.tr("Modelo: %1").arg(info["model"]))
        if info["serial"]:
            lines.append(self.tr("Serie: %1").arg(info["serial"]))
        if info["capacity_gb"]:
            lines.append(self.tr("Capacidad: %1 GB").arg(info["capacity_gb"]))
        if info["file_system"]:
            lines.append(self.tr("Sistema: %1").arg(info["file_system"]))
        if info["total_space"] > 0:
            used_pct = (info["used_space"] / info["total_space"]) * 100
            lines.append(self.tr("Uso: %1%").arg(f"{used_pct:.1f}"))
        if info["errors"]:
            lines.append(self.tr("Errores: %1").arg(", ".join(info["errors"])))
        text = "\n".join(lines) if lines else self.tr("No se pudo detectar información de la tarjeta.")
        QMessageBox.information(self, self.tr("Información de Tarjeta SD"), text)

    def _on_auto_detect_toggled(self, checked):
        settings = QSettings("Audiovisual Production", "CosechaMedia")
        settings.setValue("autoDetectDrives", bool(checked))
        if checked:
            self._auto_detect_removable_drives()

    def _auto_detect_removable_drives(self):
        try:
            drives = get_mounted_drives()
        except Exception as e:
            print(f"Error detecting drives: {e}")
            return
        if not drives:
            self.ingest_status_label.setText(self.tr("No se detectaron unidades extraíbles."))
            return
        added = []
        for d in drives:
            dp = d.get("path")
            if not dp:
                continue
            dcim = os.path.join(dp, "DCIM")
            candidate = dcim if os.path.isdir(dcim) else dp
            if candidate in self._source_paths:
                continue
            self._source_paths.append(candidate)
            added.append(candidate)
        if added:
            for p in added:
                if self.current_project_id:
                    sessions = db.get_sessions(self.current_project_id)
                    if not any(s.get("source_path") == p for s in sessions):
                        base = self._drive_label(p)
                        no_source = [s for s in sessions if not s.get("source_path")]
                        if no_source:
                            db.update_session_config(no_source[0]["id"], source_path=p, name=f"Auto ({base})")
                            sid = no_source[0]["id"]
                        else:
                            sid = db.create_session(
                                self.current_project_id, f"Auto ({base})",
                                QDate.currentDate().toString("yyyy-MM-dd"), "active",
                                source_path=p
                            )
                        self._detect_camera_for_session(sid, p)
            self._refresh_source_list()
            self._refresh_sessions_combo()
            self.update_start_button_state()
            self.ingest_status_label.setText(self.tr("Auto-detect: %1 unidad(es) añadida(s).").arg(len(added)))
        else:
            self._refresh_source_list()
            self.ingest_status_label.setText(self.tr("Auto-detect: ninguna unidad nueva."))

    def _reorganize_by_metadata(self):
        if not self._ingestors:
            QMessageBox.information(self, self.tr("Sin ingesta"), self.tr("Realiza una ingesta primero."))
            return
        reply = QMessageBox.question(
            self, self.tr("Reorganizar"),
            self.tr("¿Reorganizar archivos en 'Unknown_Camera' detectando su cámara por metadatos?"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        ingestors = list(self._ingestors)
        self.btn_start.setEnabled(False)
        self.btn_start.setText(self.tr("Reorganizando..."))
        self._run_background(_reorganize_worker, self._on_reorganize_finished, ingestors)

    def _on_reorganize_finished(self, success, payload):
        self.btn_start.setText(self.tr("Iniciar Ingesta"))
        self.btn_start.setEnabled(True)
        if not success:
            QMessageBox.warning(self, self.tr("Reorganizar"), self.tr("No se pudo reorganizar:\n%1").arg(payload))
            return
        QMessageBox.information(self, self.tr("Hecho"), self.tr("Archivos reorganizados."))

    def _proxy_resolution_height(self) -> int:
        return int(self.project_proxy_resolution.replace("p", "")) if self.project_proxy_resolution else 720

    def _generate_proxies_after_ingest(self) -> bool:
        videos = list(dict.fromkeys(self._ingested_videos))
        if not videos:
            QMessageBox.information(self, self.tr("Proxies"), self.tr("No se encontraron clips de video en la ingesta."))
            return False
        height = self._proxy_resolution_height()
        reply = QMessageBox.question(
            self, self.tr("Generar proxies"),
            self.tr("Generar proxies %1p para %2 clips de video?").arg(height).arg(len(videos)),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return False
        jobs = []
        for item in videos:
            path, root = item if isinstance(item, tuple) else (item, self.dest_root)
            jobs.append((path, root))
        self.btn_start.setEnabled(False)
        self.btn_start.setText(self.tr("Generando proxies..."))
        self._run_background(
            _generate_proxies_worker, self._on_proxies_finished,
            jobs, height
        )
        return True

    def _on_proxies_finished(self, success, payload):
        if not success:
            QMessageBox.critical(self, self.tr("Proxies"), self.tr("No se pudieron generar los proxies:\n%1").arg(payload))
        else:
            QMessageBox.information(self, self.tr("Proxies"), self.tr("Proxies generados: %1").arg(payload))
        self._run_next_post_ingest_action()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

