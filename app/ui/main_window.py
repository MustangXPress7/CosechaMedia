import sys
import os
from datetime import datetime
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QLineEdit, QProgressBar, QTableWidget,
                             QTableWidgetItem, QHeaderView, QFrame, QStackedWidget, QDateEdit,
                             QComboBox, QMessageBox, QFileDialog, QMenuBar, QMenu, QCheckBox,
                             QGroupBox, QGridLayout, QSplashScreen, QSystemTrayIcon,
                             QListWidget, QListWidgetItem, QInputDialog, QScrollArea, QFormLayout, QDialog,
                             QTextEdit, QSpinBox)
from PySide6.QtGui import QAction, QActionGroup, QIcon, QFont, QColor, QPixmap, QPainter
from PySide6.QtCore import Qt, QThread, QObject, Signal, QDate, QTimer, QSize, QPropertyAnimation, QSettings, QByteArray
from app.core.ingestor import Ingestor, DumpTarget
from app.core.watcher import FileSystemWatcher
from app.core.db import db
from app.core.notifications import NotificationManager
from app.core.sd_reader import sd_reader
from app.core.ffmpeg_utils import ffmpeg
from app.core.utils import create_folder_structure, get_mounted_drives, is_removable_drive, resource_path
from app.core.metadata_engine import metadata_engine
from app.core import translator
from app.core.translator import QtString
from app.ui import theme
from app.ui.wheat_field import paint_wheat_field
import app.ui.wheat_field as wheat_field

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

        self.notification_manager = NotificationManager()

        self.build_menu()
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.setup_views()

        settings = QSettings("Audiovisual Production", "CosechaMedia")
        settings.setValue("camera_detection_mode", "manual")
        self.project_camera_detection_mode = "manual"
        self.project_camera_detection_timeout = settings.value("camera_detection_timeout", 5, type=int)
        self._update_detect_button_state()
        geometry = settings.value("geometry", type=QByteArray)
        if geometry:
            self.restoreGeometry(geometry)
        state = settings.value("windowState", type=QByteArray)
        if state:
            self.restoreState(state)

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

        for btn, txt, tip in [
            ("btn_refresh_projects", "⟳", self.tr("Actualizar proyectos")),
            ("btn_new_project", "+", self.tr("Nuevo proyecto")),
            ("btn_delete_project", "×", self.tr("Eliminar proyecto")),
            ("btn_rename_project", "✎", self.tr("Renombrar proyecto")),
            ("btn_duplicate_project", "⧉", self.tr("Duplicar proyecto")),
            ("btn_browse_root", "📁", self.tr("Cambiar ruta maestra del proyecto")),
        ]:
            b = QPushButton(txt)
            b.setObjectName("IconButton")
            b.setFixedSize(28, 28)
            b.setToolTip(tip)
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
        hb.addWidget(self.project_path_label)

        hb.addStretch()

        for btn, txt, tip, cb in [
            ("btn_show_metadata", "⚙", self.tr("Configuración"), "_show_metadata_dialog"),
        ]:
            b = QPushButton(txt)
            b.setObjectName("IconButton")
            b.setFixedSize(28, 28)
            b.setToolTip(tip)
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

        # === MAIN CONTENT ===
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setObjectName("DashboardScrollArea")

        scroll_content = QWidget()
        two_col = QHBoxLayout(scroll_content)
        two_col.setContentsMargins(10, 6, 10, 6)
        two_col.setSpacing(10)

        left_col = QVBoxLayout()
        left_col.setSpacing(6)

        # --- Sources ---
        src_label = QLabel(self.tr("Orígenes:"))
        src_label.setStyleSheet(f"font-weight: 600; font-size: 11px; color: {theme.color('text_secondary')};")
        left_col.addWidget(src_label)

        src_top = QHBoxLayout()
        self.source_input = QComboBox()
        self.source_input.setEditable(True)
        self.source_input.setPlaceholderText(self.tr("E:\\DCIM..."))
        self.source_input.currentTextChanged.connect(self.update_start_button_state)
        src_top.addWidget(self.source_input, 1)

        self.btn_browse_source = QPushButton(self.tr("Examinar"))
        self.btn_browse_source.clicked.connect(self.select_source_path)
        src_top.addWidget(self.btn_browse_source)

        left_col.addLayout(src_top)

        self.source_list = QTableWidget()
        self.source_list.setColumnCount(2)
        self.source_list.setHorizontalHeaderLabels([self.tr("Ruta de origen"), self.tr("Cámara")])
        self.source_list.horizontalHeader().setStretchLastSection(False)
        self.source_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.source_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.source_list.horizontalHeader().resizeSection(1, 140)
        self.source_list.verticalHeader().setVisible(False)
        self.source_list.setSelectionBehavior(QTableWidget.SelectRows)
        self.source_list.setSelectionMode(QTableWidget.SingleSelection)
        self.source_list.setMinimumHeight(60)
        self.source_list.setMaximumHeight(120)
        self.source_list.itemChanged.connect(self._on_source_check_changed)
        self.source_list.itemDoubleClicked.connect(self._on_source_double_clicked)
        left_col.addWidget(self.source_list)

        src_scan_row = QHBoxLayout()
        self.btn_detect_drives = QPushButton(self.tr("⟳ Detectar"))
        self.btn_detect_drives.setToolTip(self.tr("Detectar unidades extraíbles"))
        self.btn_detect_drives.clicked.connect(self._auto_detect_removable_drives)
        src_scan_row.addWidget(self.btn_detect_drives)
        self.btn_guided_mode = QPushButton(self.tr("Modo guiado"))
        self.btn_guided_mode.setToolTip(self.tr("Asistente guiado para volcados rápidos (próximamente)"))
        self.btn_guided_mode.clicked.connect(self._show_guided_mode_stub)
        src_scan_row.addWidget(self.btn_guided_mode)
        self.btn_scan_cameras = QPushButton(self.tr("📷 Escanear cámaras"))
        self.btn_scan_cameras.setToolTip(self.tr("Escanear cámaras de todos los orígenes checkeados"))
        self.btn_scan_cameras.clicked.connect(self._scan_all_cameras)
        src_scan_row.addWidget(self.btn_scan_cameras)
        src_scan_row.addStretch()
        left_col.addLayout(src_scan_row)

        # --- Sessions ---
        sess_label = QLabel(self.tr("Sesiones:"))
        sess_label.setStyleSheet(f"font-weight: 600; font-size: 11px; color: {theme.color('text_secondary')};")
        left_col.addWidget(sess_label)

        sess_row = QHBoxLayout()
        self.sessions_combo = QComboBox()
        self.sessions_combo.setMinimumWidth(160)
        self.sessions_combo.setMaximumWidth(360)
        self.sessions_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.sessions_combo.currentIndexChanged.connect(self._on_session_selected)
        sess_row.addWidget(self.sessions_combo)

        self.btn_new_session = QPushButton("+")
        self.btn_new_session.setObjectName("IconButton")
        self.btn_new_session.setFixedSize(28, 28)
        self.btn_new_session.setToolTip(self.tr("Nueva sesión"))
        self.btn_new_session.clicked.connect(self._add_manual_session)
        sess_row.addWidget(self.btn_new_session)

        self.btn_delete_session = QPushButton("−")
        self.btn_delete_session.setObjectName("IconButton")
        self.btn_delete_session.setFixedSize(28, 28)
        self.btn_delete_session.setToolTip(self.tr("Eliminar sesión"))
        self.btn_delete_session.setEnabled(False)
        self.btn_delete_session.clicked.connect(self._delete_current_session)
        sess_row.addWidget(self.btn_delete_session)

        self.session_src_label = QLabel("")
        self.session_src_label.setStyleSheet(f"color: {theme.color('text_secondary')}; font-size: 11px;")
        self.session_src_label.setMaximumWidth(240)
        sess_row.addWidget(self.session_src_label)

        self._btn_browse_sess_src = QPushButton("📁")
        self._btn_browse_sess_src.setObjectName("IconButton")
        self._btn_browse_sess_src.setFixedSize(28, 28)
        self._btn_browse_sess_src.setToolTip(self.tr("Examinar origen de sesión…"))
        self._btn_browse_sess_src.clicked.connect(self._browse_session_src)
        sess_row.addWidget(self._btn_browse_sess_src)

        sess_row.addSpacing(8)
        sess_row.addWidget(QLabel(self.tr("Destino:")))
        self.session_dest_combo = QComboBox()
        self.session_dest_combo.addItems([self.tr("Por defecto"), self.tr("Personalizado")])
        self.session_dest_combo.setFixedWidth(110)
        self.session_dest_combo.activated.connect(self._on_session_dest_type_changed)
        sess_row.addWidget(self.session_dest_combo)

        self.session_dest_path = QLineEdit()
        self.session_dest_path.setPlaceholderText(self.tr("Ruta..."))
        self.session_dest_path.setFixedWidth(200)
        self.session_dest_path.editingFinished.connect(self._save_session_override)
        self.session_dest_path.setVisible(False)
        sess_row.addWidget(self.session_dest_path)

        self._btn_browse_sess_dest = QPushButton("📁")
        self._btn_browse_sess_dest.setObjectName("IconButton")
        self._btn_browse_sess_dest.setFixedSize(28, 28)
        self._btn_browse_sess_dest.setToolTip(self.tr("Examinar..."))
        self._btn_browse_sess_dest.clicked.connect(self._browse_session_dest)
        self._btn_browse_sess_dest.setVisible(False)
        sess_row.addWidget(self._btn_browse_sess_dest)

        self.chk_session_delicate = QCheckBox(self.tr("Modo delicado"))
        self.chk_session_delicate.stateChanged.connect(self._save_session_override)
        sess_row.addWidget(self.chk_session_delicate)

        sess_row.addStretch()
        left_col.addLayout(sess_row)

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
        self.ingest_status_label.setStyleSheet(f"color: {theme.color('text_secondary')}; font-style: italic; font-size: 10px;")
        left_col.addWidget(self.ingest_status_label)

        # --- Progress ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setMinimumHeight(18)
        self.progress_bar.setFormat(self.tr("%v / %m archivos"))
        left_col.addWidget(self.progress_bar)

        proxy_row = QHBoxLayout()
        proxy_row.setSpacing(6)
        self.chk_generate_proxies = QCheckBox(self.tr("Generar proxies"))
        self.chk_generate_proxies.setToolTip(self.tr("Genera proxies de los clips de video tras la ingesta"))
        proxy_row.addWidget(self.chk_generate_proxies)
        self.proxy_resolution = QComboBox()
        self.proxy_resolution.addItem("720p", 720)
        self.proxy_resolution.addItem("1080p", 1080)
        self.proxy_resolution.setEnabled(False)
        proxy_row.addWidget(self.proxy_resolution)
        proxy_row.addStretch()
        left_col.addLayout(proxy_row)

        self.chk_generate_proxies.toggled.connect(self.proxy_resolution.setEnabled)

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

        # --- Post-ingest actions ---
        post_row = QHBoxLayout()
        post_row.setSpacing(6)

        self.btn_reorganize = QPushButton(self.tr("Reorganizar por metadatos"))
        self.btn_reorganize.setToolTip(self.tr("Reorganiza los archivos en 'Unknown_Camera' detectando su cámara por metadatos"))
        self.btn_reorganize.clicked.connect(self._reorganize_by_metadata)
        post_row.addWidget(self.btn_reorganize)

        post_row.addStretch()

        self.chk_format_sources = QCheckBox(self.tr("Formatear orígenes al acabar:"))
        self.chk_format_sources.setToolTip(self.tr("Formatea las unidades de origen al acabar el volcado y la comprobación"))
        post_row.addWidget(self.chk_format_sources)
        self.combo_format_mode = QComboBox()
        self.combo_format_mode.addItems([self.tr("Rápido"), self.tr("Completo")])
        self.combo_format_mode.setFixedWidth(100)
        self.combo_format_mode.setEnabled(False)
        post_row.addWidget(self.combo_format_mode)
        self.chk_format_sources.toggled.connect(self.combo_format_mode.setEnabled)

        post_row.addSpacing(8)

        self.chk_shutdown = QCheckBox(self.tr("Apagar al acabar"))
        self.chk_shutdown.setToolTip(self.tr("Apaga el ordenador al finalizar todas las tareas de ingesta"))
        post_row.addWidget(self.chk_shutdown)

        left_col.addLayout(post_row)

        left_col.addStretch()

        # --- Files table ---
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([self.tr("Archivo"), self.tr("Cámara"), self.tr("Estado"), self.tr("Destino")])
        th = self.table.horizontalHeader()
        th.setSectionResizeMode(QHeaderView.Interactive)
        th.setStretchLastSection(True)
        th.resizeSection(0, 280)
        th.resizeSection(1, 130)
        th.resizeSection(2, 110)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_table_context_menu)
        self._style_table_viewports()

        two_col.addLayout(left_col, 0)
        two_col.addWidget(self.table, 1)

        scroll.setWidget(scroll_content)
        dash_layout.addWidget(scroll)

        self.main_layout.addWidget(self.dashboard_view)

        self.load_existing_projects()
        self._refresh_recent_paths()

        settings = QSettings("Audiovisual Production", "CosechaMedia")
        if settings.value("autoDetectDrives", False, type=bool):
            QTimer.singleShot(200, self._auto_detect_removable_drives)

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
            if self.current_project_id is not None:
                db.add_footage_folder(self.project_folder_name)
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    'UPDATE projects SET folder_name=?, organization_type=?, duration_type=?, use_metadata_date=? WHERE id=?',
                    (self.project_folder_name, self.project_organization_type, self.project_duration_type, int(self.project_use_metadata_date), self.current_project_id)
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
        mode_combo.addItems([self.tr("Manual"), self.tr("Automático (próximamente)")])
        mode_combo.setCurrentIndex(0)
        mode_model = mode_combo.model()
        mode_model.item(1).setEnabled(False)
        mode_combo.setToolTip(self.tr("El modo automático estará disponible próximamente."))
        mode_layout.addWidget(mode_combo)
        layout.addWidget(mode_group)

        timeout_group = QGroupBox(self.tr("Tiempo máximo de escaneo"))
        timeout_layout = QHBoxLayout(timeout_group)
        timeout_spin = QSpinBox()
        timeout_spin.setRange(5, 30)
        timeout_spin.setValue(settings.value("camera_detection_timeout", 5, type=int))
        timeout_spin.setEnabled(False)
        timeout_spin.setToolTip(self.tr("Solo aplica al modo automático, disponible próximamente."))
        timeout_layout.addWidget(timeout_spin)
        timeout_layout.addStretch()
        layout.addWidget(timeout_group)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton(self.tr("Cancelar"))
        btn_cancel.clicked.connect(dialog.reject)
        btn_save = QPushButton(self.tr("Guardar"))
        btn_save.setObjectName("PrimaryAction")
        def _save():
            settings.setValue("camera_detection_mode", "manual")
            settings.setValue("camera_detection_timeout", timeout_spin.value())
            self.project_camera_detection_mode = "manual"
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
        settings = QSettings("Audiovisual Production", "CosechaMedia")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
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
        project_id = self.project_combo.itemData(index)
        if project_id is None:
            self.current_project_id = None
            self.dest_root = ""
            self.current_session_id = None
            self.project_path_label.setText("")
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
            'SELECT name, root_path, organization_type, duration_type, default_camera, '
            'folder_name, delicate_mode, use_metadata_date FROM projects WHERE id = ?',
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

        name = res["name"]
        root = self.dest_root or self.tr("(sin ruta)")
        self.project_path_label.setText(f"→ {root}")
        self._set_status_color("success")
        self.status_text.setText(self.tr("Proyecto: %1").arg(name))

        self._populate_source_paths_from_sessions()
        self._refresh_sessions_combo()
        self._refresh_source_list()
        self._update_detect_button_state()

    def _show_create_project(self):
        name, ok = QInputDialog.getText(self, self.tr("Nuevo proyecto"), self.tr("Nombre del proyecto:"))
        if not ok or not name.strip():
            return
        name = name.strip()
        desc, ok = QInputDialog.getText(self, self.tr("Nuevo proyecto"), self.tr("Descripción (opcional):"))
        if not ok:
            desc = ""
        else:
            desc = desc.strip()
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO projects (name, root_path, description) VALUES (?, ?, ?)',
                (name, "", desc)
            )
            project_id = cursor.lastrowid
            conn.commit()
            conn.close()

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
        except Exception as e:
            QMessageBox.critical(self, self.tr("Error"), self.tr("No se pudo crear el proyecto: %1").arg(str(e)))

    def _update_detect_button_state(self):
        is_auto = self.project_camera_detection_mode == "auto"
        self.btn_detect_drives.setEnabled(True)
        self.btn_scan_cameras.setEnabled(is_auto)
        self.btn_reorganize.setVisible(is_auto)

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
        self._style_table_viewports()
        self.dashboard_view.update()
        if getattr(self, "_status_color_key", None):
            self._set_status_color(self._status_color_key, self._status_color_radius)

    def _switch_accent(self, name):
        theme.set_accent(name)
        theme.apply_theme()
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
            any(s.get("source_path") and os.path.isdir(s["source_path"]) for s in sessions)
        )

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
            s_delicate = sess.get("delicate_mode")
            s_delicate = self.project_delicate_mode if s_delicate is None else s_delicate

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
            )
            ing.file_started.connect(self.on_file_started)
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
        self.ingest_status_label.setText(self.tr("Ingesta detenida por el usuario"))
        self._set_status_color("danger", 6)
        self.status_text.setText(self.tr("Detenido"))

        self.notification_manager.notify_ingest_stopped()

    def on_file_started(self, source_path):
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

        dest_item = QTableWidgetItem("")
        dest_item.setFlags(dest_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, 3, dest_item)

        self._file_row_map[source_path] = row
        self._total_files += 1
        self.progress_bar.setMaximum(self._total_files)
        self.ingest_status_label.setText(self.tr("Procesando: %1").arg(os.path.basename(source_path)))

    def on_file_finished(self, source_path, dest_path, success, metadata=None, ingestor=None):
        row = self._file_row_map.get(source_path)
        if row is not None:
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

            if dest_path:
                dest_item = QTableWidgetItem(dest_path)
                self.table.setItem(row, 3, dest_item)

        if success and dest_path:
            ftype = metadata_engine.get_file_type_info(dest_path)
            if ftype.get("type") == "video":
                root = ingestor.destination_root if ingestor else self.dest_root
                self._ingested_videos.append((dest_path, root))

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
            if self.chk_generate_proxies.isChecked():
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
        removable = [p for p in self._source_paths if is_removable_drive(p)]
        skipped = [p for p in self._source_paths if not is_removable_drive(p)]
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
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
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
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        context_menu = QMenu(self)
        rename_action = context_menu.addAction(self.tr("Renombrar cámara..."))
        rename_action.triggered.connect(lambda: self._rename_camera_dialog(row))
        context_menu.exec(self.table.viewport().mapToGlobal(pos))

    def _rename_camera_dialog(self, row):
        old_name_item = self.table.item(row, 1)
        if not old_name_item:
            return
        old_name = old_name_item.text()
        if old_name in ("Detectando...", "Unknown_Camera", ""):
            QMessageBox.information(self, self.tr("Sin cámara"), self.tr("No se detectó cámara para renombrar."))
            return
        new_name, ok = QInputDialog.getText(
            self, self.tr("Renombrar cámara"),
            self.tr("Nuevo nombre para '%1':").arg(old_name),
            text=old_name
        )
        if ok and new_name.strip() and new_name.strip() != old_name:
            new_name = new_name.strip()
            for ing in self._ingestors:
                ing.rename_camera(old_name, new_name)
            for r in range(self.table.rowCount()):
                cam_item = self.table.item(r, 1)
                if cam_item and cam_item.text() == old_name:
                    cam_item.setText(new_name)
            self.ingest_status_label.setText(self.tr("Cámara renombrada: %1 → %2").arg(old_name).arg(new_name))

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
                for ing in self._ingestors:
                    ing.rename_camera(old_name, new_name.strip())
                for r in range(self.table.rowCount()):
                    cam_item = self.table.item(r, 1)
                    if cam_item and cam_item.text() == old_name:
                        cam_item.setText(new_name.strip())
                self.ingest_status_label.setText(self.tr("Cámara renombrada: %1 → %2").arg(old_name).arg(new_name.strip()))

    def _on_source_double_clicked(self, item):
        if item.column() == 1:
            self._prompt_rename_camera(item.row())

    def _prompt_rename_camera(self, row):
        if self.current_project_id is None:
            return
        path_item = self.source_list.item(row, 0)
        if not path_item:
            return
        path = path_item.text()
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
        auto_sources = {s["source_path"]: s for s in sessions if s.get("source_path")}
        for row, path in enumerate(self._source_paths):
            self.source_list.insertRow(row)
            # Column 0: source path with checkbox
            item = QTableWidgetItem(path)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if path in auto_sources else Qt.Unchecked)
            self.source_list.setItem(row, 0, item)
            # Column 1: camera name
            s = auto_sources.get(path)
            cam = s.get("camera_name") if s else None
            cam_text = cam if cam else (self.tr("Sin nombre") if self.project_camera_detection_mode == "manual" else "—")
            cam_item = QTableWidgetItem(cam_text)
            if self.project_camera_detection_mode != "manual":
                cam_item.setFlags(cam_item.flags() & ~Qt.ItemIsEditable)
            self.source_list.setItem(row, 1, cam_item)
        self.source_list.blockSignals(False)

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
            path_item = self.source_list.item(row, 0)
            if path_item and path_item.text() == source_path:
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
        if self.project_camera_detection_mode == "manual":
            db.update_session_config(session_id, camera_name=None)
            self._refresh_source_list()
            self._refresh_sessions_combo()
            self.ingest_status_label.setText(self.tr("Cámara: Sin nombre (manual)"))
            return
        self._set_camera_cell_text(source_path, "🔄 Escaneando…")
        import threading
        self._cam_timer = QTimer(self)
        self._cam_timer.setSingleShot(True)
        def on_timeout():
            if getattr(self, '_cam_done', False):
                return
            self._set_camera_cell_text(source_path, self.tr("Sin nombre"))
            QTimer.singleShot(0, lambda: self._prompt_unknown_camera(session_id, source_path))
        self._cam_timer.timeout.connect(on_timeout)
        self._cam_timer.start(self.project_camera_detection_timeout * 1000)
        def scan():
            smallest = self._find_smallest_media(source_path)
            if smallest is None:
                self._set_camera_cell_text(source_path, self.tr("Sin nombre"))
                QTimer.singleShot(0, lambda: self._prompt_unknown_camera(session_id, source_path))
                return
            try:
                meta = metadata_engine.get_video_metadata(smallest)
                cam = meta.get("camera_model", "") or ""
                if cam and cam.strip() and cam != "Unknown":
                    cam = cam.strip()
                    self._cam_done = True
                    self._set_camera_cell_text(source_path, cam)
                    db.update_session_config(session_id, camera_name=cam)
                    QTimer.singleShot(0, self._refresh_source_list)
                    QTimer.singleShot(0, self._refresh_sessions_combo)
                    QTimer.singleShot(0, lambda c=cam: self.ingest_status_label.setText(self.tr("Cámara detectada: %1").arg(c)))
                    return
            except Exception:
                pass
            self._set_camera_cell_text(source_path, self.tr("Sin nombre"))
            QTimer.singleShot(0, lambda: self._prompt_unknown_camera(session_id, source_path))
        self._cam_done = False
        t = threading.Thread(target=scan, daemon=True)
        t.start()

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

    def _prompt_unknown_camera(self, session_id, source_path):
        base = self._drive_label(source_path)
        msg = QMessageBox(self)
        msg.setWindowTitle(self.tr("Cámara no detectada"))
        msg.setText(self.tr("No se pudo detectar la cámara en %1.").arg(base))
        msg.setInformativeText(self.tr("¿Qué nombre quieres darle a esta cámara?"))
        btn_sin = msg.addButton(self.tr("Sin nombre"), QMessageBox.ActionRole)
        btn_rename = msg.addButton(self.tr("Renombrar…"), QMessageBox.ActionRole)
        msg.setDefaultButton(btn_sin)
        msg.exec()
        if msg.clickedButton() == btn_rename:
            name, ok = QInputDialog.getText(
                self, self.tr("Nombre de cámara"),
                self.tr("Introduce el nombre de la cámara:")
            )
            if ok and name.strip():
                db.update_session_config(session_id, camera_name=name.strip())
                self.ingest_status_label.setText(self.tr("Cámara: %1").arg(name.strip()))
        else:
            db.update_session_config(session_id, camera_name=None)
            self.ingest_status_label.setText(self.tr("Cámara: Sin nombre"))
        self._refresh_source_list()
        self._refresh_sessions_combo()
        self.update_start_button_state()

    def _on_camera_cell_edited(self, item):
        row = item.row()
        path_item = self.source_list.item(row, 0)
        if not path_item:
            return
        path = path_item.text()
        sessions = db.get_sessions(self.current_project_id)
        session = next((s for s in sessions if s.get("source_path") == path), None)
        if not session:
            return
        new_name = item.text().strip()
        db.update_session_config(session["id"], camera_name=new_name or None)
        self._refresh_sessions_combo()
        self.ingest_status_label.setText(self.tr("Cámara: %1").arg(new_name or self.tr("Sin nombre")))

    def _on_source_check_changed(self, item):
        if self.current_project_id is None:
            return
        if item.column() == 1:
            self._on_camera_cell_edited(item)
            return
        if item.column() != 0:
            return
        path = item.text()
        checked = item.checkState() == Qt.Checked
        if checked:
            existing = db.get_sessions(self.current_project_id)
            already = any(s.get("source_path") == path for s in existing)
            if not already:
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
            sessions = db.get_sessions(self.current_project_id)
            for s in sessions:
                if s.get("source_path") == path:
                    if s["id"] == self.current_session_id:
                        self.current_session_id = None
                    db.delete_session(s["id"])
                    self.ingest_status_label.setText(self.tr("Sesión de %1 eliminada.").arg(path))
                    break
        self._refresh_sessions_combo()
        self.update_start_button_state()

    def _refresh_sessions_combo(self):
        prev_id = self.sessions_combo.currentData()
        self.sessions_combo.blockSignals(True)
        self.sessions_combo.clear()
        if self.current_project_id is None:
            self.sessions_combo.blockSignals(False)
            self.btn_delete_session.setEnabled(False)
            self.session_src_label.setText("")
            self._btn_browse_sess_src.setVisible(False)
            self.session_dest_combo.setVisible(False)
            self._btn_browse_sess_dest.setVisible(False)
            self.chk_session_delicate.setVisible(False)
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
        self.sessions_combo.blockSignals(False)
        self.btn_delete_session.setEnabled(True)

    def _on_session_selected(self, index):
        session_id = self.sessions_combo.itemData(index)
        if session_id is None:
            self.current_session_id = None
            self.btn_delete_session.setEnabled(False)
            self.session_src_label.setText("")
            self._btn_browse_sess_src.setVisible(False)
            self.session_dest_combo.setVisible(False)
            self._btn_browse_sess_dest.setVisible(False)
            self.chk_session_delicate.setVisible(False)
            return
        self.current_session_id = session_id
        self.btn_delete_session.setEnabled(True)
        self._btn_browse_sess_src.setVisible(True)
        self.session_dest_combo.setVisible(True)
        session = db.get_session(session_id)
        if not session:
            return
        src = session.get("source_path") or ""
        text = (self.tr("Origen: %1").arg(src) if src
                else self.tr("Origen: sin origen (no se ejecutará)"))
        from PySide6.QtGui import QFontMetrics
        fm = QFontMetrics(self.session_src_label.font())
        self.session_src_label.setText(fm.elidedText(text, Qt.ElideMiddle, 240))
        self.session_src_label.setToolTip(text)
        self.session_dest_combo.blockSignals(True)
        dest = session.get("destination_override")
        if dest:
            self.session_dest_combo.setCurrentIndex(1)
            self.session_dest_path.setText(dest)
            self.session_dest_path.setVisible(True)
            self._btn_browse_sess_dest.setVisible(True)
        else:
            self.session_dest_combo.setCurrentIndex(0)
            self.session_dest_path.setText("")
            self.session_dest_path.setVisible(False)
            self._btn_browse_sess_dest.setVisible(False)
        self.session_dest_combo.blockSignals(False)
        self.chk_session_delicate.blockSignals(True)
        if session.get("delicate_mode") is not None:
            self.chk_session_delicate.setChecked(bool(session["delicate_mode"]))
        else:
            self.chk_session_delicate.setChecked(self.project_delicate_mode)
        self.chk_session_delicate.blockSignals(False)

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
            self.tr("¿Eliminar la sesión #%1 y todos sus archivos?\n"
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
        is_alt = index == 1
        self.session_dest_path.setVisible(is_alt)
        self._btn_browse_sess_dest.setVisible(is_alt)
        if not is_alt:
            if self.current_session_id is not None:
                db.update_session_config(self.current_session_id, destination_override=None)
        elif self.session_dest_path.text().strip():
            self._save_session_override()

    def _save_session_override(self):
        if self.current_session_id is None:
            return
        kw = {}
        if self.session_dest_combo.currentIndex() == 1:
            alt = self.session_dest_path.text().strip()
            kw["destination_override"] = alt if alt else None
        else:
            kw["destination_override"] = None
        kw["delicate_mode"] = int(self.chk_session_delicate.isChecked())
        db.update_session_config(self.current_session_id, **kw)

    def _browse_session_dest(self):
        path = QFileDialog.getExistingDirectory(
            self, self.tr("Seleccionar destino de sesión"),
            self.session_dest_path.text().strip() or self.dest_root or os.path.expanduser("~")
        )
        if path:
            self.session_dest_path.setText(path)
            self._save_session_override()

    def _browse_session_src(self):
        if self.current_session_id is None:
            return
        path = QFileDialog.getExistingDirectory(
            self, self.tr("Seleccionar origen de sesión"),
            os.path.expanduser("~")
        )
        if path:
            session = db.get_session(self.current_session_id)
            if session and session.get("source_path") != path:
                base = self._drive_label(path)
                db.update_session_config(
                    self.current_session_id,
                    source_path=path,
                    name=f"Auto ({base})"
                )
            self._refresh_sessions_combo()
            self.update_start_button_state()

    def build_menu(self):
        menu_bar = self.menuBar()

        m_file = menu_bar.addMenu(self.tr("&Archivo"))

        act_new = QAction(self.tr("&Nuevo Proyecto..."), self)
        act_new.setShortcut("Ctrl+N")
        act_new.triggered.connect(self._show_create_project)
        m_file.addAction(act_new)

        act_refresh = QAction(self.tr("&Recargar proyectos"), self)
        act_refresh.setShortcut("F5")
        act_refresh.triggered.connect(self.load_existing_projects)
        m_file.addAction(act_refresh)

        act_delete_all = QAction(self.tr("&Eliminar todos los proyectos..."), self)
        act_delete_all.triggered.connect(self.delete_all_projects)
        m_file.addAction(act_delete_all)

        m_file.addSeparator()

        act_quit = QAction(self.tr("&Salir"), self)
        act_quit.setShortcut("Ctrl+Q")
        act_quit.triggered.connect(self.close)
        m_file.addAction(act_quit)

        m_routes = menu_bar.addMenu(self.tr("&Rutas"))

        act_pick_source = QAction(self.tr("Seleccionar &origen (SD)..."), self)
        act_pick_source.setShortcut("Ctrl+O")
        act_pick_source.triggered.connect(self.select_source_path)
        m_routes.addAction(act_pick_source)

        act_pick_dest = QAction(self.tr("Seleccionar &destino del proyecto..."), self)
        act_pick_dest.setShortcut("Ctrl+D")
        act_pick_dest.triggered.connect(self.select_dest_path)
        m_routes.addAction(act_pick_dest)

        m_routes.addSeparator()

        self.act_auto_detect = QAction(self.tr("Auto-detectar &unidades extraíbles al inicio"), self)
        self.act_auto_detect.setCheckable(True)
        settings = QSettings("Audiovisual Production", "CosechaMedia")
        self.act_auto_detect.setChecked(
            settings.value("autoDetectDrives", False, type=bool)
        )
        self.act_auto_detect.triggered.connect(self._on_auto_detect_toggled)
        m_routes.addAction(self.act_auto_detect)

        act_detect_now = QAction(self.tr("&Detectar unidades extraíbles ahora"), self)
        act_detect_now.triggered.connect(self._auto_detect_removable_drives)
        m_routes.addAction(act_detect_now)

        m_routes.addSeparator()

        act_open_data = QAction(self.tr("Abrir carpeta &datos..."), self)
        act_open_data.triggered.connect(self.open_data_folder)
        m_routes.addAction(act_open_data)

        m_routes.addSeparator()

        act_dump_targets = QAction(self.tr("Gestionar &destinos de volcado..."), self)
        act_dump_targets.triggered.connect(self._manage_dump_locations)
        m_routes.addAction(act_dump_targets)

        m_detection = menu_bar.addMenu(self.tr("&Detección"))
        act_cam_detect = QAction(self.tr("Configurar detección de &cámara..."), self)
        act_cam_detect.triggered.connect(self._show_camera_detection_dialog)
        m_detection.addAction(act_cam_detect)
        act_detect_sd = QAction(self.tr("Detectar &información de tarjeta SD..."), self)
        act_detect_sd.triggered.connect(self._detect_sd_card)
        m_detection.addAction(act_detect_sd)

        m_custom = menu_bar.addMenu(self.tr("&Personalizado"))
        act_footage = QAction(self.tr("Personalizar &carpeta de footage..."), self)
        act_footage.triggered.connect(self._manage_footage_folders)
        m_custom.addAction(act_footage)
        act_containers = QAction(self.tr("Personalizar &contenedores de archivos..."), self)
        act_containers.triggered.connect(self._manage_containers)
        m_custom.addAction(act_containers)

        self._view_menu = menu_bar.addMenu(self.tr("&Vista"))
        self._theme_menu = self._view_menu.addMenu(self.tr("Tema"))
        self._theme_group = QActionGroup(self)
        self._theme_group.setExclusive(True)
        current_theme = theme.get_theme()
        for key, palette in theme.THEMES.items():
            act = QAction(self.tr(palette["name"]), self)
            act.setCheckable(True)
            act.setChecked(key == current_theme)
            act.triggered.connect(lambda checked=False, k=key: self._switch_theme(k))
            self._theme_group.addAction(act)
            self._theme_menu.addAction(act)

        self._accent_menu = self._view_menu.addMenu(self.tr("Acento"))
        self._accent_group = QActionGroup(self)
        self._accent_group.setExclusive(True)
        current_accent = theme.get_accent()
        for key, acc in theme.ACCENTS.items():
            act = QAction(self.tr(acc["name"]), self)
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
        act_check_updates = QAction(self.tr("&Búsqueda de actualizaciones..."), self)
        act_check_updates.triggered.connect(self._check_for_updates)
        m_help.addAction(act_check_updates)
        m_help.addSeparator()
        act_about = QAction(self.tr("&Acerca de..."), self)
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

    def select_source_path(self):
        start_dir = self.source_input.currentText().strip() or os.path.expanduser("~")
        path = QFileDialog.getExistingDirectory(
            self, self.tr("Seleccionar carpeta de la Tarjeta SD"), start_dir
        )
        if path:
            if path not in self._source_paths:
                self._source_paths.append(path)
                self.source_input.setCurrentText("")
                if self.current_project_id:
                    sessions = db.get_sessions(self.current_project_id)
                    if not any(s.get("source_path") == path for s in sessions):
                        base = self._drive_label(path)
                        no_source = [s for s in sessions if not s.get("source_path")]
                        if no_source:
                            db.update_session_config(no_source[0]["id"], source_path=path, name=f"Auto ({base})")
                            sid = no_source[0]["id"]
                        else:
                            sid = db.create_session(
                                self.current_project_id, f"Auto ({base})",
                                QDate.currentDate().toString("yyyy-MM-dd"), "active",
                                source_path=path
                            )
                        self._detect_camera_for_session(sid, path)
            self._refresh_source_list()
            self._refresh_sessions_combo()
            self.update_start_button_state()

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
            self._save_project_root(path)

    def _save_project_root(self, new_root):
        if self.current_project_id is None:
            return
        try:
            os.makedirs(new_root, exist_ok=True)
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE projects SET root_path = ? WHERE id = ?',
                (os.path.abspath(new_root), self.current_project_id)
            )
            conn.commit()
            conn.close()
            self.dest_root = os.path.abspath(new_root)
            self.project_path_label.setText(f"→ {self.dest_root}")
            self.ingest_status_label.setText(self.tr("Destino maestro actualizado: %1").arg(self.dest_root))
            db.save_recent_path(self.dest_root, "dest")
        except Exception as e:
            QMessageBox.critical(self, self.tr("Error"), self.tr("No se pudo actualizar el destino: %1").arg(str(e)))

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

    def show_about(self):
        QMessageBox.about(
            self,
            self.tr("Acerca de CosechaMedia"),
            "<h2 style='color: {accent};'>CosechaMedia</h2>"
            "<p style='color: {text};'>{desc}</p>"
            "<p style='color: {secondary};'>Versión 2.0 - Tech Innovation Edition</p>"
            "<p style='color: {secondary};'>PySide6 + SQLite + FFmpeg</p>".format(
                accent=theme.color("accent"),
                text=theme.color("text"),
                secondary=theme.color("text_secondary"),
                desc=self.tr("Herramienta de ingesta de tarjetas SD para producción audiovisual."),
            )
        )

    def _show_guided_mode_stub(self):
        QMessageBox.information(
            self, self.tr("Modo guiado"),
            self.tr("El Modo guiado para volcados rápidos estará disponible próximamente.")
        )

    def _check_for_updates(self):
        QMessageBox.information(
            self, self.tr("Búsqueda de actualizaciones"),
            self.tr("La búsqueda de actualizaciones estará disponible próximamente.")
        )

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
        return self.proxy_resolution.currentData() or 720

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
