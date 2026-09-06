import sys
import os
import json
import time
from datetime import datetime
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QLabel, QPushButton, QProgressBar, QTableWidget,
                              QTableWidgetItem, QHeaderView, QFrame, QStackedWidget,
                              QComboBox, QMessageBox, QFileDialog, QMenuBar, QMenu, QCheckBox,
                              QGroupBox, QSplashScreen, QSystemTrayIcon,
                              QListWidgetItem, QInputDialog, QFormLayout, QDialog,
                              QTextEdit, QSpinBox, QSizePolicy, QSplitter, QDialogButtonBox)
from PySide6.QtGui import QAction, QActionGroup, QIcon, QFont, QColor, QPixmap
from PySide6.QtCore import Qt, QThread, QObject, Signal, QDate, QTimer, QSize, QPropertyAnimation, QSettings, QByteArray
from app.core.ingestor import Ingestor, DumpTarget
from app.core.watcher import FileSystemWatcher
from app.core.db import db
from app.core.notifications import NotificationManager
from app.core.sd_reader import sd_reader
from app.core.ffmpeg_utils import ffmpeg
from app.core.utils import create_folder_structure, is_removable_drive, resource_path
from app.core.metadata_engine import metadata_engine
from app.core import translator
from app.core import updater
from app.core.translator import QtString
from app.ui import theme
from app.ui import icons
from app.ui.about_dialog import AboutDialog
from app.ui.project_settings_dialog import ProjectSettingsDialog
from app.ui.camera_overrides_dialog import CameraOverridesDialog
from app.ui.names_manager_dialog import NamesManagerDialog
from app.ui.dump_locations_dialog import DumpLocationsDialog
import app.ui.wheat_field as wheat_field
from app.core import ftp, mtp
from app.core import shoot_inbox as inboxmod
from app.core.ftp import FtpBackend
from app.core.metadata_engine import _is_system_entry
from app.ui.ftp_picker import FtpPickerDialog
from app.ui.ftp_status import FtpStatusDialog
from app.ui.selective_dump import SelectiveDumpAssistant, content_summary
from app.ui.add_source_dialog import AddSourceDialog
from app.ui.wifi_panel import SenderEditDialog, ShootInboxPanel
from app.ui.mixins.wifi_mixin import WifiMixin
from app.ui.mixins.camera_mixin import CameraMixin
from app.ui.mixins.sources_mixin import SourcesMixin
from app.ui.mixins.project_mixin import ProjectMixin
from app.ui.mixins.sessions_mixin import SessionsMixin
from app.ui.mixins.workers import _StageWorker, DashboardBackground, _TaskWorker

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
    # La reorganización se mueve al nuevo ReorganizeDialog (Plan 3).
    # El método ingestor.reorganize_by_metadata() se eliminó (D-18); este
    # worker queda como no-op hasta sustituirse por el diálogo nuevo.
    progress.emit(translator.tr("La reorganización por metadatos se ha movido al diálogo 'Reorganizar footage...'."))
    return True


def _probe_device_connectivity(sessions):
    """Verifica la conectividad real de cada dispositivo (Tarea 3).

    Corre en un hilo de fondo (via _run_background): enumera MTP/WPD y
    comprueba el alcance de los perfiles FTP. Devuelve un dict con:
    - mtp_connected: set de device_ids MTP alcanzables
    - ftp_reachable: set de device_ids ftp:<id> alcanzables
    - ftp_backend: backend FTP (para staging posterior)
    Nunca lanza: ante errores de WPD/FTP devuelve sets vacíos. Los orígenes
    wifi se resuelven de forma síncrona en la UI (servidor en marcha).
    """
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

class MainWindow(QMainWindow, WifiMixin, CameraMixin, SourcesMixin, ProjectMixin, SessionsMixin):
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
        self.project_default_dispositivo = ""
        self.project_folder_name = "Footage"
        self.project_delicate_mode = False
        self.project_use_metadata_date = True
        self.project_generate_proxies = False
        self.project_proxy_resolution = "720p"
        self.project_date = QDate.currentDate()
        self.project_date_mode = "auto"
        self.project_manual_date = QDate.currentDate()
        self.project_camera_date_overrides = "{}"
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
        self._connectivity = {}  # device_id -> bool (Tarea 3: estado real)
        self._connectivity_ts = 0.0  # cache de la última verificación

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
            # Reutiliza la sonda compartida de conectividad (Tarea 3)
            return _probe_device_connectivity(sessions)

        def _on_poll_done(ok, result):
            self._poll_in_progress = False
            if not ok:
                return
            # Alimentar el cache de conectividad usado por la columna Estado
            self._connectivity_ts = time.time()
            for s in sessions:
                did = s["device_id"]
                if did and not str(did).startswith("wifi:"):
                    self._connectivity[did] = (
                        did in result.get("mtp_connected", set())
                        or did in result.get("ftp_reachable", set()))
            self._process_device_poll(result, sessions)
            self._update_source_status_cells()

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

        self.app_label = QLabel("CosechaMedia")
        self.app_label.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {theme.color('accent')};")
        hb.addWidget(self.app_label)
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
            QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred))
        hb.addWidget(self.project_path_label)

        hb.addStretch()

        for btn, icon_name, tip, cb in [
            ("btn_show_metadata", "wrench", self.tr("Configuración"), "_show_metadata_dialog"),
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
            [self.tr("Ruta de origen"), self.tr("Dispositivo"),
             self.tr("Estado"), self.tr("Opciones")])
        header = self.source_list.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        header.setSectionResizeMode(3, QHeaderView.Interactive)
        header.setMinimumSectionSize(32)
        header.resizeSection(1, 70)
        header.resizeSection(2, 90)
        header.resizeSection(3, 110)
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
        self.source_list.installEventFilter(self)
        left_col.addWidget(self.source_list)

        # --- Sessions ---
        sess_box = QGroupBox(self.tr("Sesiones"))
        sess_box.setObjectName("SessionsBox")
        sess_box_layout = QVBoxLayout(sess_box)
        sess_box_layout.setContentsMargins(8, 6, 8, 6)
        sess_box_layout.setSpacing(4)

        sess_top = QHBoxLayout()
        sess_top.setSpacing(4)
        self.sessions_combo = QComboBox()
        self.sessions_combo.setMinimumWidth(100)
        self.sessions_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
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

        # Sin stretch final: el combo absorbe el hueco y los botones quedan
        # pegados al borde derecho de la caja.
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

        # I-15/I-18: botón rotativo de modo (icono según modo) + botón de menú
        sess_dump_row = QHBoxLayout()
        sess_dump_row.addWidget(QLabel(self.tr("Volcado:")))
        self.btn_session_dump_mode = QPushButton()
        self.btn_session_dump_mode.setCursor(Qt.PointingHandCursor)
        self.btn_session_dump_mode.setToolTip(self.tr(
            "Cambiar el volcado de esta sesión: todo / intervalo de fechas / últimos N días"))
        self.btn_session_dump_mode.clicked.connect(self._cycle_session_content_mode)
        icons.apply(self.btn_session_dump_mode, "square", size=16)
        sess_dump_row.addWidget(self.btn_session_dump_mode)
        self.btn_session_dump_config = QPushButton()
        self.btn_session_dump_config.setCursor(Qt.PointingHandCursor)
        self.btn_session_dump_config.setToolTip(self.tr(
            "Abrir las opciones del modo de volcado actual"))
        self.btn_session_dump_config.clicked.connect(self._open_session_dump_menu)
        sess_dump_row.addWidget(self.btn_session_dump_config)
        sess_dump_row.addStretch()
        sess_box_layout.addLayout(sess_dump_row)
        self._update_session_dump_switch()

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

        self.chk_generate_report = QCheckBox(self.tr("Generar CSV de integridad al acabar"))
        self.chk_generate_report.setToolTip(self.tr("Exporta un reporte CSV con hashes y estado de cada archivo"))
        post_terminar.addWidget(self.chk_generate_report)

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
        self.btn_reorganize = QPushButton(self.tr("Reorganizar footage…"))
        self.btn_reorganize.setToolTip(self.tr("Abre el reorganizador para escanear el proyecto y organizar archivos de vídeo por cámara/fecha con verificación MD5"))
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
        # Sin texto hasta que la ingesta termina (el total solo se conoce al final).
        self.progress_bar.setFormat("")
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
            self.tr("Archivo"), self.tr("Dispositivo"), self.tr("Estado"),
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
        ProjectSettingsDialog(self, open_overrides_cb=self._show_camera_overrides_dialog).exec()

    def _show_camera_overrides_dialog(self):
        dialog = CameraOverridesDialog(self)
        if dialog.exec():
            # Persistir al proyecto
            if self.current_project_id is not None:
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute('UPDATE projects SET camera_date_overrides=? WHERE id=?',
                               (self.project_camera_date_overrides, self.current_project_id))
                conn.commit()
                conn.close()

    def _manage_footage_folders(self):
        NamesManagerDialog(self, self.tr("Personalizar carpeta de footage"),
                           db.get_footage_folders, db.add_footage_folder,
                           db.rename_footage_folder, db.delete_footage_folder,
                           db.duplicate_footage_folder).exec()

    def _manage_containers(self):
        NamesManagerDialog(self, self.tr("Personalizar contenedores de archivos"),
                           db.get_containers, db.add_container, db.rename_container,
                           db.delete_container, None).exec()
        metadata_engine.refresh_file_types()

    def _manage_dump_locations(self):
        if self.current_project_id is None:
            QMessageBox.information(self, self.tr("Sin proyecto"), self.tr("Selecciona un proyecto primero."))
            return
        DumpLocationsDialog(self).exec()

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

    def _refresh_accent_labels(self):
        """Re-tinta las etiquetas persistentes con color de acento inline.

        Los setStyleSheet con theme.color() se hornean al construir el
        widget; sin esto no siguen al acento hasta reiniciar la app.
        """
        self.app_label.setStyleSheet(
            f"font-weight: bold; font-size: 13px; color: {theme.color('accent')};")
        self.project_path_label.setStyleSheet(
            f"color: {theme.color('accent')}; font-size: 11px; font-weight: bold;")

    def _switch_theme(self, name):
        theme.set_theme(name)
        theme.apply_theme()
        icons.refresh_all()
        self._style_table_viewports()
        self._refresh_accent_labels()
        self.dashboard_view.update()
        if getattr(self, "_status_color_key", None):
            self._set_status_color(self._status_color_key, self._status_color_radius)

    def _switch_accent(self, name):
        theme.set_accent(name)
        theme.apply_theme()
        icons.refresh_all()
        self._style_table_viewports()
        self._refresh_accent_labels()
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
                "default_dispositivo": None,
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
        self.progress_bar.setFormat("")
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
            cn = s.get("nombre_dispositivo")
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
            s_cam = sess.get("default_dispositivo")
            s_cam = self.project_default_dispositivo if s_cam is None else s_cam
            s_date_mode = sess.get("date_mode") or self.project_date_mode or "auto"
            s_use_meta = s_date_mode == "auto"
            s_manual_date = sess.get("manual_date") or (self.project_manual_date if s_date_mode == "manual" else None)
            device_key = sess.get("device_id") or sess.get("source_path") or ""
            dev_delicate = db.get_device_delicate(device_key)
            if dev_delicate is not None:
                s_delicate = bool(dev_delicate)
            else:
                s_delicate = False

            # I-18: Modo de contenido desde la sesión, con WiFi/FTP default a "all"
            s_content_mode = sess.get("content_mode", "all")
            # WiFi y FTP siempre usan "all" (todo el contenido) por compatibilidad
            is_ftp = str(device_key).startswith("ftp:")
            if is_ftp or device_key.startswith("wifi:"):
                s_content_mode = "all"

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

            cam_overrides = {}
            try:
                raw_overrides = json.loads(self.project_camera_date_overrides or "{}")
                # Normalizar a dict cam -> fecha para modos manual
                for cam, val in raw_overrides.items():
                    if isinstance(val, dict):
                        if str(val.get("mode", "manual")).lower() == "manual":
                            date_str = val.get("date")
                            if date_str:
                                cam_overrides[cam] = date_str
                    elif isinstance(val, str) and val:
                        cam_overrides[cam] = val
            except Exception:
                cam_overrides = {}
            ing = Ingestor(
                self.current_project_id,
                dest_root,
                folder_name=s_folder,
                use_metadata_date=bool(s_use_meta),
                order_type=order_val,
                duration_type=s_dur,
                default_dispositivo=s_cam,
                delicate_mode=bool(s_delicate),
                session_id=sid,
                camera_map=camera_map,
                manual_date=s_manual_date,
                dump_targets=sess_targets,
                project_master_root=self.dest_root,
                content_filter=s_content_filter,
                content_mode=s_content_mode,
                camera_date_overrides=cam_overrides,
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

        # Esperar y limpiar el thread de staging para no dejar un hilo con
        # referencias COM corruptas tras detener la ingesta (D-25).
        if hasattr(self, '_stage_thread') and self._stage_thread and self._stage_thread.isRunning():
            self._stage_thread.quit()
            self._stage_thread.wait(2000)
            self._stage_thread = None
        if hasattr(self, '_stage_worker'):
            self._stage_worker = None

        self.btn_start.setText(self.tr("Iniciar Ingesta"))
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.table.setSortingEnabled(True)
        self.ingest_status_label.setText(self.tr("Ingesta detenida por el usuario"))
        self._set_status_color("danger", 6)
        self.status_text.setText(self.tr("Detenido"))

        self.notification_manager.notify_ingest_stopped()

    def prepare_for_update(self):
        """Stop all background work (ingest, watchers, wifi, polling) before an update.
        Called from AboutDialog before spawning the update helper."""
        # Stop any active ingestion
        self.stop_ingest()
        # Stop WiFi reception
        self._stop_wifi_reception()
        # Stop device polling timer
        if hasattr(self, '_sync_timer') and self._sync_timer.isActive():
            self._sync_timer.stop()
        # Cancel any background staging threads
        if hasattr(self, '_stage_thread') and self._stage_thread and self._stage_thread.isRunning():
            self._stage_thread.quit()
            self._stage_thread.wait(2000)

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
            if self.project_camera_detection_mode != "manual" and metadata:
                if metadata.get("metadata_verified") is False:
                    camera_item = QTableWidgetItem(self.tr("⛔ Metadatos no verificados"))
                    camera_item.setToolTip(self.tr("ffprobe no respondió; metadatos no verificados"))
                elif metadata.get("camera_model") != "Unknown":
                    camera_item = QTableWidgetItem(metadata["camera_model"])
                else:
                    # camera_model "Unknown" con metadatos verificados: no
                    # sobreescribir con "Unknown"; conservar el valor que ya
                    # mostraba la celda (nombre/Detectando...) para que
                    # camera_item SIEMPRE esté enlazado (evita UnboundLocalError).
                    existing = self.table.item(row, 1)
                    camera_item = existing if existing is not None else QTableWidgetItem("")
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
            self.progress_bar.setFormat(self.tr("%v / %m archivos"))
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
            if self.chk_generate_report.isChecked():
                self._pending_actions.append("report")
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
            elif action == "report":
                self._pending_actions.pop(0)
                self._generate_report_after_ingest()
                continue
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

    def _generate_report_after_ingest(self):
        """Genera CSV de integridad para todas las sesiones de la ingesta."""
        from app.core.ingestor import generate_integrity_report
        if self.current_project_id is None:
            return
        sessions = db.get_sessions(self.current_project_id)
        active = [s for s in sessions if s.get("source_path")]
        if not active:
            return
        import os
        for session in active:
            default_name = f"integridad_{session.get('name', 'sesion')}.csv"
            dest = os.path.join(session.get("source_path", ""), default_name)
            # Si no se puede escribir en el origen, usar el home
            if not os.access(os.path.dirname(dest) or os.path.expanduser("~"), os.W_OK):
                dest = os.path.join(os.path.expanduser("~"), default_name)
            generate_integrity_report(session["id"], dest)
        self.ingest_status_label.setText(self.tr("Reporte CSV generado."))

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


    def _show_table_context_menu(self, pos):
        context_menu = QMenu(self)
        clear_action = context_menu.addAction(self.tr("Eliminar completados"))
        clear_action.triggered.connect(self._clear_completed_rows)
        context_menu.addSeparator()
        integrity_action = context_menu.addAction(self.tr("Exportar reporte de integridad (CSV)"))
        integrity_action.triggered.connect(self._export_integrity_report)
        source_path = self._current_source_path()
        if source_path and os.path.isdir(source_path):
            content_action = context_menu.addAction(self.tr("Exportar contenido de tarjeta (CSV)"))
            content_action.triggered.connect(self._export_card_content_report)
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

    def _export_integrity_report(self):
        """Exporta CSV de integridad (post-dump) para la sesión activa."""
        if self.current_project_id is None:
            return
        sessions = db.get_sessions(self.current_project_id)
        active = [s for s in sessions if s.get("source_path")]
        if not active:
            QMessageBox.information(self, self.tr("Reporte"),
                                    self.tr("No hay sesiones con origen para exportar."))
            return
        session = active[0]
        default_name = f"integridad_{session.get('name', 'sesion')}.csv"
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Guardar reporte de integridad"),
            os.path.join(os.path.expanduser("~"), default_name),
            "CSV (*.csv)")
        if not path:
            return
        from app.core.ingestor import generate_integrity_report
        ok = generate_integrity_report(session["id"], path)
        if ok:
            QMessageBox.information(self, self.tr("Reporte"),
                                    self.tr("Reporte guardado en:\n%1").arg(path))
        else:
            QMessageBox.warning(self, self.tr("Reporte"),
                                self.tr("No se pudo generar el reporte."))

    def _export_card_content_report(self):
        """Exporta CSV de contenido de tarjeta (pre-dump) para el origen activo."""
        source_path = self._current_source_path()
        if not source_path or not os.path.isdir(source_path):
            QMessageBox.information(self, self.tr("Reporte"),
                                    self.tr("No se detectó una ruta de origen válida."))
            return
        base = os.path.basename(os.path.normpath(source_path)) or "tarjeta"
        default_name = f"contenido_{base}.csv"
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Guardar contenido de tarjeta"),
            os.path.join(os.path.expanduser("~"), default_name),
            "CSV (*.csv)")
        if not path:
            return
        from app.core.ingestor import generate_card_content_report
        ok = generate_card_content_report(source_path, path)
        if ok:
            QMessageBox.information(self, self.tr("Reporte"),
                                    self.tr("Contenido exportado en:\n%1").arg(path))
        else:
            QMessageBox.warning(self, self.tr("Reporte"),
                                self.tr("No se pudo exportar el contenido."))

    def eventFilter(self, obj, ev):
        result = self._source_list_event_filter(obj, ev)
        if result:
            return True
        return super().eventFilter(obj, ev)

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

        m_ingest.addSeparator()

        act_reorganize = QAction(self.tr("Reorganizar &footage…"), self)
        act_reorganize.triggered.connect(self._reorganize_by_metadata)
        m_ingest.addAction(act_reorganize)

        act_open_data = QAction(self.tr("Abrir carpeta &datos…"), self)
        act_open_data.triggered.connect(self.open_data_folder)
        m_ingest.addAction(act_open_data)

        m_config = menu_bar.addMenu(self.tr("&Configuración"))

        act_cam_detect = QAction(self.tr("Configuración del proyecto…"), self)
        act_cam_detect.triggered.connect(self._show_metadata_dialog)
        m_config.addAction(act_cam_detect)

        m_config.addSeparator()

        act_footage = QAction(self.tr("Personalizar &carpeta de footage…"), self)
        act_footage.triggered.connect(self._manage_footage_folders)
        m_config.addAction(act_footage)

        act_containers = QAction(self.tr("Personalizar &contenedores de archivos…"), self)
        act_containers.triggered.connect(self._manage_containers)
        m_config.addAction(act_containers)

        m_tools = menu_bar.addMenu(self.tr("&Herramientas"))

        act_known_devices = QAction(self.tr("Dispositivos &conocidos…"), self)
        act_known_devices.triggered.connect(self._open_known_devices)
        m_tools.addAction(act_known_devices)

        act_del_devices = QAction(self.tr("Borrar dispositivos &guardados…"), self)
        act_del_devices.triggered.connect(self._delete_all_saved_devices)
        m_tools.addAction(act_del_devices)

        act_del_cameras = QAction(self.tr("Borrar dispositivos &conocidos…"), self)
        act_del_cameras.triggered.connect(self._delete_all_known_cameras)
        m_tools.addAction(act_del_cameras)

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

    def _delete_all_saved_devices(self):
        """Borra todos los dispositivos guardados (known_devices, inbox_senders, perfiles FTP)."""
        reply = QMessageBox.question(
            self, self.tr("Borrar dispositivos guardados"),
            self.tr("Esto eliminará todos los dispositivos conocidos, "
                    "remitentes WiFi y perfiles FTP guardados.\n"
                    "Esta acción no se puede deshacer.\n\n"
                    "¿Continuar?"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        db.delete_all_saved_devices()
        self._populate_source_paths_from_sessions()
        self._refresh_source_list()
        self._refresh_sessions_combo()
        self.update_start_button_state()
        self.ingest_status_label.setText(
            self.tr("Todos los dispositivos guardados han sido eliminados."))

    def _delete_all_known_cameras(self):
        """Borra la cache de dispositivos conocidos y nombres en DB."""
        reply = QMessageBox.question(
            self, self.tr("Borrar dispositivos conocidos"),
            self.tr("Esto limpiará la cache de detección de dispositivos y "
                    "los nombres de dispositivo guardados en archivos.\n"
                    "La próxima ingesta volverá a detectar dispositivos automáticamente.\n\n"
                    "¿Continuar?"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        metadata_engine.clear_cache()
        db.delete_all_known_cameras()
        self.ingest_status_label.setText(
            self.tr("Dispositivos conocidos eliminados. La detección se reiniciará."))

    def _open_known_devices(self):
        """Abre el diálogo de dispositivos conocidos (Herramientas → Dispositivos conocidos)."""
        from app.ui.device_registry import DeviceRegistryDialog
        dlg = DeviceRegistryDialog(self)
        dlg.exec()
        # Al cerrar, refrescar la lista de orígenes por si cambió algo
        self._refresh_source_list()

    def _disconnected_devices(self):
        """Dispositivos MTP/FTP desconectados y perfiles FTP con sesiones en el
        proyecto, para poder borrarlos desde el diálogo unificado (D-12).
        También incluye dispositivos guardados globalmente (device_settings) que
        no tienen sesiones en el proyecto actual, para que permanezcan visibles
        en 'Añadir origen' aunque se borren todas las sesiones del proyecto."""
        if self.current_project_id is None:
            return []
        try:
            current = {dev.device_id for dev in mtp.WpdBackend().list_devices()}
        except Exception:
            current = set()
        known = {}
        # 1. Dispositivos con sesiones en el proyecto actual
        for s in db.get_sessions(self.current_project_id):
            did = s.get("device_id") or ""
            if did.startswith("ftp:"):
                known.setdefault(did, s.get("nombre_dispositivo") or "")
            elif did and not did.startswith("wifi:"):
                known.setdefault(did, s.get("nombre_dispositivo") or "")
        # 2. Dispositivos guardados globalmente (device_settings) que no están
        # en el proyecto actual pero deberían seguir apareciendo
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT device_key, nombre_dispositivo FROM device_settings')
            for row in cursor.fetchall():
                did = row["device_key"]
                name = row["nombre_dispositivo"] or did
                if did not in known:
                    known[did] = name
        finally:
            conn.close()
        # Devolver solo los que están desconectados (o FTP que siempre se listan)
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
                        # Para unidades USB extraíbles, asignar device_id basado en la ruta
                        device_id = ""
                        if is_removable_drive(path):
                            device_id = f"usb:{path}"
                        sid = db.create_session(
                            self.current_project_id, f"Auto ({base})",
                            QDate.currentDate().toString("yyyy-MM-dd"), "active",
                            source_path=path, device_id=device_id)
                        self._detect_camera_for_session(sid, path, force_prompt=True)
        self._repair_folder_device_id(path)
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
        self._repair_folder_device_id(path)
        self._refresh_sessions_combo()
        self.update_start_button_state()

    def _repair_folder_device_id(self, path):
        """Repara el device_id de una sesión ligada a una carpeta/tarjeta.

        Un bug anterior (bug 2) podía dejar sesiones con device_id ``usbstor``
        (unidades USB de almacenamiento masivo que WPD enumera). Esos NO son
        dispositivos MTP reales: un device_id así rompe la asociación por
        serial, de modo que la sesión «no pilla el dispositivo». Lo limpiamos
        para que la tarjeta se identifique por su serial de volumen (sd_cards),
        tanto al asignar de nuevo un origen como al detectar la cámara.
        """
        if not is_removable_drive(path):
            return
        if self.current_project_id is None:
            return
        for s in db.get_sessions(self.current_project_id):
            if s.get("source_path") != path:
                continue
            did = str(s.get("device_id") or "")
            if "usbstor" in did.lower():
                db.update_session_config(s["id"], device_id="", device_folder="")
                # Limpiar también el mapeo cámara huérfano guardado bajo ese id fake
                db.delete_device_settings_by_key(did)

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

    def _show_ftp_status(self):
        dlg = FtpStatusDialog(self)
        dlg.exec()

    def _show_ftp_status_for_device(self, device_id):
        dlg = FtpStatusDialog(self, device_id=device_id)
        dlg.exec()

    def _reset_mtp_thread_local(self):
        """Reinicia el thread-local COM del MTP para evitar referencias corruptas."""
        try:
            from app.core import mtp
            import threading
            if hasattr(mtp, '_manager_local'):
                mtp._manager_local = threading.local()
        except Exception:
            pass
        # Detener thread de staging si existe
        if hasattr(self, '_stage_thread') and self._stage_thread and self._stage_thread.isRunning():
            self._stage_thread.quit()
            self._stage_thread.wait(2000)
            self._stage_thread = None
        if hasattr(self, '_stage_worker'):
            self._stage_worker = None

    def _reset_ingestors(self):
        """Limpia los ingestors vivos."""
        # Detener timers y watchers
        if hasattr(self, '_sync_timer') and self._sync_timer.isActive():
            self._sync_timer.stop()
        if hasattr(self, '_cam_timer') and self._cam_timer.isActive():
            self._cam_timer.stop()
        for watcher in self.watchers[:]:
            try:
                watcher.stop()
            except Exception:
                pass
        self.watchers = []
        # Detener ingestors
        for ing in self._ingestors[:]:
            try:
                ing.stop()
            except Exception:
                pass
        self._ingestors = []


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
        name = dialog.device_name or ""
        cache_dir = mtp.device_cache_dir(dialog.device_id, dialog.device_folder)
        try:
            os.makedirs(cache_dir, exist_ok=True)
        except OSError:
            cache_dir = mtp.device_cache_dir(dialog.device_id, "")
            os.makedirs(cache_dir, exist_ok=True)
        self._register_device_source(
            cache_dir, dialog.device_id, dialog.device_folder, name,
            backend=ftp.FtpBackend(),
        )

    def _register_device_source(self, cache_dir, device_id, device_folder, device_name, backend=None):
        if cache_dir not in self._source_paths:
            self._source_paths.append(cache_dir)
            self.source_input.setCurrentText("")
        # Guardar nombre del dispositivo para recordarlo en futuros proyectos
        if device_id and device_name:
            try:
                db.save_dispositivo_config(device_id, device_name)
                # Upsert a known_devices para persistencia cross-proyecto (REQ-09)
                device_type = "ftp" if str(device_id).startswith("ftp:") else "mtp"
                db.upsert_known_device(device_id, device_type, name=device_name, last_camera=device_name)
            except Exception:
                pass
        sessions = db.get_sessions(self.current_project_id)
        existing = next((s for s in sessions if s.get("source_path") == cache_dir), None)
        if existing:
            db.update_session_config(
                existing["id"],
                device_id=device_id, device_folder=device_folder,
                source_path=cache_dir,
                nombre_dispositivo=device_name,
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
                    nombre_dispositivo=device_name,
                )
            else:
                sid = db.create_session(
                    self.current_project_id, f"Auto ({base})",
                    QDate.currentDate().toString("yyyy-MM-dd"), "active",
                    source_path=cache_dir,
                )
                db.update_session_config(sid, device_id=device_id, device_folder=device_folder,
                                          nombre_dispositivo=device_name)
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


    def _reorganize_by_metadata(self):
        """Abre el diálogo ReorganizeDialog para escanear y reorganizar footage del proyecto."""
        if self.current_project_id is None:
            QMessageBox.information(self, self.tr("Sin proyecto"), self.tr("Seleccione o cree un proyecto primero."))
            return

        project_root = self.dest_root
        if not project_root:
            QMessageBox.information(self, self.tr("Sin destino"), self.tr("Configure un destino de proyecto primero."))
            return

        # Lazy import para evitar ciclos
        from app.ui.reorganize_dialog import ReorganizeDialog
        dialog = ReorganizeDialog(self, project_root=project_root)
        dialog.exec()  # El diálogo maneja todo el flujo internamente

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

