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
from PySide6.QtGui import QIcon, QFont, QColor, QPixmap
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
from app.ui.mixins.menu_mixin import MenuMixin
from app.ui.mixins.sources_mixin import SourcesMixin
from app.ui.mixins.project_mixin import ProjectMixin
from app.ui.mixins.sessions_mixin import SessionsMixin
from app.ui.mixins.devices_mixin import DevicesMixin
from app.ui.mixins.ingest_mixin import IngestMixin
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

class MainWindow(QMainWindow, WifiMixin, CameraMixin, MenuMixin, DevicesMixin, SourcesMixin, ProjectMixin, SessionsMixin, IngestMixin):
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

    # --- UI Construction Helpers (extracted from setup_views) ---
    def _build_dashboard(self):
        """Construye dashboard_view, dash_layout y desc_box (descripción)."""
        self.dashboard_view = DashboardBackground()
        self.dashboard_view.setObjectName("DashboardView")
        self.dash_layout = QVBoxLayout(self.dashboard_view)
        self.dash_layout.setContentsMargins(0, 0, 0, 0)
        self.dash_layout.setSpacing(0)

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

    def _build_header(self):
        """Construye header_bar: app_label, project_combo, botones proyecto, path_label, btn_show_metadata, status_indicator/text."""
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

        self.dash_layout.addWidget(header_bar)

    def _build_sources_table(self):
        """Construye source_label_row, src_top (source_input + btn_add_source), source_list (4 cols, eventFilter)."""
        # --- Sources ---
        src_label_row = QHBoxLayout()
        src_label = QLabel(self.tr("Orígenes:"))
        src_label.setStyleSheet(f"font-weight: 600; font-size: 11px; color: {theme.color('text_secondary')};")
        src_label_row.addWidget(src_label)
        src_label_row.addStretch()
        self.left_col.addLayout(src_label_row)

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

        self.left_col.addLayout(src_top)

        self.source_list = QTableWidget()
        self.source_list.setColumnCount(4)
        self.source_list.setHorizontalHeaderLabels(
            [self.tr("Ruta de origen"), self.tr("Dispositivo"),
             self.tr("Estado"), self.tr("Opciones")])
        header = self.source_list.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.setMinimumSectionSize(40)
        header.resizeSection(1, 120)
        header.resizeSection(2, 90)
        header.resizeSection(3, 110)
        self.source_list.setMinimumWidth(300)
        self.source_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.source_list.verticalHeader().setVisible(False)
        self.source_list.setSelectionBehavior(QTableWidget.SelectRows)
        self.source_list.setSelectionMode(QTableWidget.SingleSelection)
        self.source_list.setSizePolicy(
            QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))
        self.source_list.itemChanged.connect(self._on_source_check_changed)
        self.source_list.itemDoubleClicked.connect(self._on_source_double_clicked)
        self.source_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.source_list.customContextMenuRequested.connect(
            self._show_source_context_menu)
        self.source_list.installEventFilter(self)
        self.left_col.addWidget(self.source_list)

    def _build_sessions_box(self):
        """Construye sess_box: sessions_combo, botones new/delete, src/dest rows, dump mode switch (rotativo + config)."""
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

        self.btn_rename_session = QPushButton()
        self.btn_rename_session.setObjectName("IconButton")
        self.btn_rename_session.setFixedSize(28, 28)
        self.btn_rename_session.setToolTip(self.tr("Renombrar sesión"))
        icons.apply(self.btn_rename_session, "pencil", size=18)
        self.btn_rename_session.clicked.connect(self._rename_current_session)
        sess_top.addWidget(self.btn_rename_session)

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

        self._sess_box = sess_box

    def _build_post_actions(self):
        """Construye post_box: 'Al terminar' (format, CSV, shutdown) + 'Operaciones' (reorganize, clear_completed)."""
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

        self._post_box = post_box

    def _build_action_buttons(self):
        """Construye action_row: btn_start (PrimaryAction), btn_stop (DangerAction)."""
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
        self._action_row = action_row  # guardamos para ensamblar abajo

        self.ingest_status_label = QLabel("")
        self.ingest_status_label.setStyleSheet(f"color: {theme.color('text_secondary')}; font-style: italic; font-size: 10px; padding: 4px 10px;")

    def _build_progress_area(self):
        """Construye progress_bar (sin texto), stats_row (processed/pending/errors labels)."""
        # --- Progress ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setMinimumHeight(18)
        # Sin texto hasta que la ingesta termina (el total solo se conoce al final).
        self.progress_bar.setFormat("")

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
        self._stats_row = stats_row  # guardamos para ensamblar abajo

    def _build_files_table(self):
        """Construye table (6 cols, sorting, context menu, styled viewport)."""
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

    def _assemble_layout(self):
        """Ensambla el splitter, tamaños, restore_btn, y añade splitter a dash_layout."""
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(4)
        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        left_widget = QWidget()
        left_widget.setContentsMargins(10, 6, 6, 6)
        self.left_col = QVBoxLayout(left_widget)
        self.left_col.setContentsMargins(0, 0, 0, 0)
        self.left_col.setSpacing(6)

        # Add description box first
        self.left_col.addWidget(self._desc_box)

        # Build all left column sections
        self._build_sources_table()
        self._build_sessions_box()
        self._build_post_actions()

        # Sesiones + Acciones post-ingesta justo debajo de la tabla de orígenes
        sess_post_row = QHBoxLayout()
        sess_post_row.setSpacing(10)
        self._sess_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        sess_post_row.addWidget(self._sess_box, 1)
        self._post_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        sess_post_row.addWidget(self._post_box, 1)
        self.left_col.addLayout(sess_post_row)

        self._build_files_table()

        self.left_col.addStretch(5)  # mucho espacio arriba → controles pegados a la parte inferior

        # Barra inferior izquierda: botones acción, progreso, stats, estado
        self._build_action_buttons()
        self._build_progress_area()
        self.left_col.addLayout(self._action_row)
        self.left_col.addWidget(self.progress_bar)
        self.left_col.addLayout(self._stats_row)
        self.left_col.addWidget(self.ingest_status_label)

        self.left_col.addStretch(1)  # pequeño margen final

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

        self.dash_layout.addWidget(splitter, 1)
        self.dash_layout.addWidget(self.ingest_status_label)

        self.main_layout.addWidget(self.dashboard_view)

    def _connect_signals(self):
        """Conecta todas las señales UI → slots (project_combo, source_list, table, botones, etc.)."""
        # project_combo ya conectado en _build_header
        # source_list signals ya conectados en _build_sources_table
        # sessions_combo ya conectado en _build_sessions_box
        # btn_session_dump_mode, btn_session_dump_config ya conectados en _build_sessions_box
        # chk_format_sources, btn_reorganize, btn_clear_completed ya conectados en _build_post_actions
        # btn_start, btn_stop ya conectados en _build_action_buttons
        # table context menu ya conectado en _build_files_table
        # splitterMoved ya conectado en _assemble_layout
        # source_input.currentTextChanged ya conectado en _build_sources_table
        # btn_add_source.clicked ya conectado en _build_sources_table
        # btn_new_session, btn_delete_session ya conectados en _build_sessions_box
        # _btn_browse_sess_src, _btn_browse_sess_dest ya conectados en _build_sessions_box
        # chk_format_sources.toggled ya conectado en _build_post_actions
        # btn_edit_description.clicked ya conectado en _build_dashboard
        # btn_show_metadata.clicked ya conectado en _build_header
        # Los botones de proyecto (btn_refresh_projects, etc.) ya conectados en _build_header

        # Cargar proyectos y rutas recientes
        self.load_existing_projects()
        self._refresh_recent_paths()

        settings = QSettings("Audiovisual Production", "CosechaMedia")
        if settings.value("autoDetectDrives", False, type=bool):
            QTimer.singleShot(200, self._auto_detect_removable_drives)

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
        self._build_dashboard()
        self._build_header()
        self._assemble_layout()
        self._connect_signals()

    
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
        # Fuerza recálculo del header Stretch de source_list al mover el splitter
        if hasattr(self, 'source_list') and self.source_list:
            try:
                self.source_list.horizontalHeader().updateGeometries()
                # asegura que la columna 0 ocupa el espacio disponible
                hdr = self.source_list.horizontalHeader()
                fixed = hdr.sectionSize(1) + hdr.sectionSize(2) + hdr.sectionSize(3)
                avail = max(40, self.source_list.viewport().width() - fixed - 2)
                hdr.resizeSection(0, avail)
            except Exception:
                pass

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

    def eventFilter(self, obj, ev):
        result = self._source_list_event_filter(obj, ev)
        if result:
            return True
        return super().eventFilter(obj, ev)

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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

