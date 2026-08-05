"""Selector de carpetas de servidores FTP para ingesta por WiFi.

Al aceptar expone ``device_id`` (``ftp:<id_perfil>``), ``device_name`` y
``device_folder`` (ruta relativa con "/" a la carpeta base del servidor).
"""

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout, QInputDialog,
    QLabel, QLineEdit, QPushButton, QSpinBox, QTextEdit, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout,
)

from app.core import ftp as ftpmod
from app.core.db import db
from app.core.translator import QtString
from app.ui import theme

_DCIM_HINTS = ("dcim", "picture", "foto", "cámara", "camara", "100dci", "100media")

GUIDE_TEXT = (
    "Android — Primitive FTPd (recomendada):\n"
    "1. Instala Primitive FTPd desde F-Droid o github.com/wolpi/prim-ftpd "
    "(gratis, código abierto; ya no está en Google Play).\n"
    "2. Ábrela y pulsa ▶ para iniciar el servidor. Concede el acceso a los "
    "archivos si el sistema lo pide.\n"
    "3. La pantalla principal muestra la dirección, p. ej. "
    "ftp://192.168.1.5:2221, y el usuario (por defecto «user»).\n"
    "4. Para poner contraseña, ajústala en los ajustes (engranaje) antes de "
    "iniciar el servidor.\n\n"
    "iOS — GoFTP Server (App Store):\n"
    "1. Instala GoFTP Server desde la App Store y ábrela.\n"
    "2. Pulsa Start. Anota la dirección, el puerto, el usuario y la "
    "contraseña que muestra.\n\n"
    "En CosechaMedia:\n"
    "• Pulsa 'Detectar en la red…' para encontrar el servidor, o escribe la "
    "IP y el puerto.\n"
    "• Introduce usuario y contraseña y pulsa Conectar.\n"
    "• Elige la carpeta (p. ej. DCIM) y pulsa Aceptar.\n"
    "Mantén la pantalla del dispositivo encendida durante la transferencia."
)


class _ScanWorker(QObject):
    """Escanea la red local buscando servidores FTP fuera del hilo de UI."""

    done = Signal(object)

    def run(self):
        self.done.emit(ftpmod.scan_network_ftp())


class FtpPickerDialog(QDialog):
    """Diálogo para elegir la carpeta de un servidor FTP."""

    def tr(self, text, *args, **kwargs):
        return QtString(super().tr(text, *args, **kwargs))

    def __init__(self, parent=None, backend=None):
        super().__init__(parent)
        self._backend = backend or ftpmod.FtpBackend()
        self._profiles = []
        self._current_profile_id = None
        self._detect_thread = None
        self.profile_id = None
        self.device_id = ""
        self.device_name = ""
        self.device_folder = ""

        self.setWindowTitle(self.tr("Importar por WiFi (FTP)"))
        self.resize(720, 640)
        self._build_ui()
        self._load_profiles()

    # -- UI --------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        hint = QLabel(
            self.tr("Conecta el móvil o la cámara al mismo WiFi que el ordenador, "
                    "inicia el servidor FTP en el dispositivo y configura la conexión.")
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(
            "color: {}; font-size: 12px;".format(theme.color("text_secondary")))
        layout.addWidget(hint)

        row = QHBoxLayout()
        row.addWidget(QLabel(self.tr("Servidor guardado:")))
        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(240)
        self.profile_combo.currentIndexChanged.connect(self._on_profile_changed)
        row.addWidget(self.profile_combo, 1)
        layout.addLayout(row)

        form = QFormLayout()
        form.setSpacing(6)
        self.name_edit = QLineEdit()
        form.addRow(self.tr("Nombre:"), self.name_edit)
        host_row = QHBoxLayout()
        self.host_edit = QLineEdit()
        self.host_edit.setPlaceholderText("192.168.1.5")
        host_row.addWidget(self.host_edit, 1)
        self.detect_btn = QPushButton(self.tr("Detectar en la red…"))
        self.detect_btn.setToolTip(self.tr("Busca servidores FTP en tu red WiFi"))
        self.detect_btn.clicked.connect(self._detect_network)
        host_row.addWidget(self.detect_btn)
        form.addRow(self.tr("Servidor (IP):"), host_row)
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(2221)
        form.addRow(self.tr("Puerto:"), self.port_spin)
        self.user_edit = QLineEdit("user")
        form.addRow(self.tr("Usuario:"), self.user_edit)
        self.pass_edit = QLineEdit()
        self.pass_edit.setEchoMode(QLineEdit.Password)
        form.addRow(self.tr("Contraseña:"), self.pass_edit)
        self.base_edit = QLineEdit()
        self.base_edit.setPlaceholderText(self.tr("(opcional)"))
        form.addRow(self.tr("Carpeta base:"), self.base_edit)
        self.passive_check = QCheckBox(self.tr("Modo pasivo (recomendado)"))
        self.passive_check.setChecked(True)
        form.addRow("", self.passive_check)
        layout.addLayout(form)

        conn_row = QHBoxLayout()
        self.connect_btn = QPushButton(self.tr("Conectar"))
        self.connect_btn.setObjectName("PrimaryAction")
        self.connect_btn.clicked.connect(self._do_connect)
        conn_row.addWidget(self.connect_btn)
        self.conn_status = QLabel("")
        self.conn_status.setStyleSheet(
            "color: {}; font-size: 11px;".format(theme.color("text_secondary")))
        conn_row.addWidget(self.conn_status, 1)
        layout.addLayout(conn_row)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.itemExpanded.connect(self._on_item_expanded)
        self.tree.itemSelectionChanged.connect(self._update_ok_state)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.tree, 1)

        self.guide_btn = QPushButton(self.tr("Cómo conectar (guía paso a paso)"))
        self.guide_btn.setCheckable(True)
        self.guide_btn.setChecked(False)
        self.guide_btn.clicked.connect(self._toggle_guide)
        layout.addWidget(self.guide_btn)
        self.guide_text = QTextEdit()
        self.guide_text.setReadOnly(True)
        self.guide_text.setStyleSheet(
            "color: {}; font-size: 11px;".format(theme.color("text_secondary")))
        self.guide_text.setPlainText(self.tr(GUIDE_TEXT))
        self.guide_text.setVisible(False)
        self.guide_text.setMaximumHeight(180)
        layout.addWidget(self.guide_text)

        self.selection_label = QLabel("")
        self.selection_label.setStyleSheet(
            "color: {}; font-size: 11px;".format(theme.color("text_secondary")))
        layout.addWidget(self.selection_label)

        buttons = QHBoxLayout()
        self.ok_btn = QPushButton(self.tr("Aceptar"))
        self.ok_btn.setObjectName("PrimaryAction")
        self.ok_btn.setEnabled(False)
        self.ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton(self.tr("Cancelar"))
        cancel_btn.clicked.connect(self.reject)
        buttons.addStretch()
        buttons.addWidget(self.ok_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

    def _toggle_guide(self, checked):
        self.guide_text.setVisible(checked)

    # -- perfiles ---------------------------------------------------------

    def _load_profiles(self):
        self._profiles = db.list_ftp_profiles()
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItem(self.tr("— Añadir nuevo servidor —"), None)
        for p in self._profiles:
            label = p["name"] or f"{p['host']}:{p['port']}"
            self.profile_combo.addItem(label, p["id"])
        self.profile_combo.blockSignals(False)
        self._on_profile_changed()

    def _on_profile_changed(self, *_):
        idx = self.profile_combo.currentIndex()
        if 0 <= idx < len(self._profiles) + 1 and self.profile_combo.itemData(idx) is not None:
            pid = self.profile_combo.itemData(idx)
            p = next((x for x in self._profiles if x["id"] == pid), None)
            if p is not None:
                self._current_profile_id = pid
                self.name_edit.setText(p["name"] or "")
                self.host_edit.setText(p["host"] or "")
                self.port_spin.setValue(int(p["port"] or 21))
                self.user_edit.setText(p["username"] or "")
                self.pass_edit.setText(p["password"] or "")
                self.base_edit.setText(p["base_folder"] or "")
                self.passive_check.setChecked(bool(p.get("passive", 1)))
                return
        self._current_profile_id = None
        self.name_edit.clear()
        self.host_edit.clear()
        self.port_spin.setValue(2221)
        self.user_edit.setText("user")
        self.pass_edit.clear()
        self.base_edit.clear()
        self.passive_check.setChecked(True)

    def _form_profile(self):
        return ftpmod.FtpProfile(
            name=self.name_edit.text().strip(),
            host=self.host_edit.text().strip(),
            port=self.port_spin.value(),
            username=self.user_edit.text().strip(),
            password=self.pass_edit.text(),
            base_folder=self.base_edit.text().strip(),
            passive=self.passive_check.isChecked(),
            timeout=15,
        )

    def _save_profile(self, profile):
        kwargs = dict(
            name=profile.name,
            host=profile.host,
            port=profile.port,
            username=profile.username,
            password=profile.password,
            base_folder=profile.base_folder,
            passive=profile.passive,
            timeout=profile.timeout,
        )
        if self._current_profile_id is not None:
            db.update_ftp_profile(self._current_profile_id, **kwargs)
            return self._current_profile_id
        return db.add_ftp_profile(**kwargs)

    # -- conexión ---------------------------------------------------------

    def _detect_network(self):
        if getattr(self, "_detect_thread", None) and self._detect_thread.isRunning():
            return
        self.detect_btn.setEnabled(False)
        self.conn_status.setText(self.tr("Escaneando la red…"))
        worker = _ScanWorker()
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.done.connect(self._on_scan_done)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self._detect_thread = thread
        thread.start()

    def _on_scan_done(self, results):
        self.detect_btn.setEnabled(True)
        self.conn_status.setText("")
        results = results or []
        if not results:
            self.conn_status.setText(
                self.tr("No se encontraron servidores FTP en la red. "
                        "Comprueba que el servidor está iniciado."))
            return
        if len(results) == 1:
            self._apply_scan_result(results[0])
            return
        labels = [self._scan_label(r) for r in results]
        choice, ok = QInputDialog.getItem(
            self, self.tr("Servidores FTP encontrados"),
            self.tr("Elige tu dispositivo:"), labels, 0, False)
        if ok and choice:
            self._apply_scan_result(results[labels.index(choice)])

    def _scan_label(self, r):
        banner = (r.get("banner") or "").strip()
        if banner:
            return f"{r['host']}:{r['port']} — {banner[:48]}"
        return f"{r['host']}:{r['port']}"

    def _apply_scan_result(self, r):
        self.profile_combo.setCurrentIndex(0)
        self.host_edit.setText(r["host"])
        self.port_spin.setValue(int(r["port"]))
        banner = (r.get("banner") or "").strip()
        if banner:
            self.conn_status.setText(self.tr("Servidor encontrado: %1").arg(banner[:48]))

    def _do_connect(self):
        profile = self._form_profile()
        if not profile.host:
            self.conn_status.setText(self.tr("Introduce la IP o nombre del servidor."))
            return
        try:
            pid = self._save_profile(profile)
        except Exception as e:
            self.conn_status.setText(self.tr("No se pudo guardar el perfil: %1").arg(str(e)))
            return
        self._current_profile_id = pid
        self.device_id = ftpmod.device_key(pid)
        self.device_name = profile.display_name()
        self.conn_status.setText(self.tr("Conectando…"))
        try:
            self._backend.list_children(self.device_id, "")
        except Exception as e:
            self.tree.clear()
            self.conn_status.setText(self.tr("No se pudo conectar: %1").arg(str(e)))
            self.ok_btn.setEnabled(False)
            return
        self._load_storages()
        row = db.get_ftp_profile(pid) if pid is not None else None
        if row is not None:
            worked = bool(row["passive"])
            self.passive_check.setChecked(worked)
            if worked != bool(profile.passive):
                self.conn_status.setText(
                    self.tr("Conectado en modo activo. Elige la carpeta a importar.")
                    if not worked else
                    self.tr("Conectado en modo pasivo. Elige la carpeta a importar."))
            else:
                self.conn_status.setText(self.tr("Conectado. Elige la carpeta a importar."))
        else:
            self.conn_status.setText(self.tr("Conectado. Elige la carpeta a importar."))
        self._suggest_dcim()

    def _load_storages(self):
        self.tree.clear()
        self._node_path = {}
        if not self.device_id:
            return
        try:
            storages = self._backend.list_children(self.device_id, "")
        except Exception as e:
            self.conn_status.setText(self.tr("No se pudo conectar: %1").arg(str(e)))
            return
        for st in storages:
            if not st.is_dir:
                continue
            item = QTreeWidgetItem([st.name])
            item.setIcon(0, self._folder_icon())
            item.setData(0, Qt.UserRole, {"path": st.name, "loaded": False})
            item.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)
            self.tree.addTopLevelItem(item)
        self._update_ok_state()

    def _folder_icon(self):
        from PySide6.QtWidgets import QStyle
        return self.style().standardIcon(QStyle.SP_DirIcon)

    def _load_children(self, item):
        data = item.data(0, Qt.UserRole) or {}
        if data.get("loaded"):
            return
        if not self.device_id:
            return
        path = data["path"]
        try:
            children = self._backend.list_children(self.device_id, path)
        except Exception:
            children = []
        self._load_children_into(item, children)

    def _load_children_into(self, item, children):
        data = item.data(0, Qt.UserRole) or {}
        data["loaded"] = True
        item.setData(0, Qt.UserRole, data)
        path = data["path"]
        for child in children:
            if not child.is_dir:
                continue
            child_item = QTreeWidgetItem([child.name])
            child_item.setData(0, Qt.UserRole, {"path": path + "/" + child.name, "loaded": False})
            child_item.setIcon(0, self._folder_icon())
            child_item.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)
            item.addChild(child_item)

    def _suggest_dcim(self):
        if not self.device_id:
            return
        for i in range(self.tree.topLevelItemCount()):
            storage_item = self.tree.topLevelItem(i)
            path = storage_item.data(0, Qt.UserRole)["path"]
            try:
                children = self._backend.list_children(self.device_id, path)
            except Exception:
                continue
            for child in children:
                if not child.is_dir:
                    continue
                low = child.name.lower()
                if any(h in low for h in _DCIM_HINTS):
                    self._load_children_into(storage_item, children)
                    target = None
                    for j in range(storage_item.childCount()):
                        cand = storage_item.child(j)
                        if cand.text(0) == child.name:
                            target = cand
                            break
                    if target is not None:
                        storage_item.setExpanded(True)
                        self.tree.setCurrentItem(target)
                    return

    def _on_item_expanded(self, item):
        self._load_children(item)

    def _on_item_double_clicked(self, item, _col):
        if item.childCount() > 0:
            return
        if self.ok_btn.isEnabled():
            self.accept()

    def _selected_path(self):
        items = self.tree.selectedItems()
        if not items:
            return ""
        data = items[0].data(0, Qt.UserRole) or {}
        return data.get("path", "")

    def _update_ok_state(self, *_):
        path = self._selected_path()
        self.ok_btn.setEnabled(bool(path) and bool(self.device_id))
        self.selection_label.setText(path)

    def accept(self):
        path = self._selected_path()
        if not self.device_id or not path:
            return
        profile = self._form_profile()
        try:
            pid = self._save_profile(profile)
        except Exception:
            pid = self._current_profile_id
        self.profile_id = pid
        self.device_id = ftpmod.device_key(pid) if pid is not None else self.device_id
        self.device_name = profile.display_name()
        self.device_folder = path
        super().accept()
