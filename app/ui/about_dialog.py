"""Dialogo 'Acerca de' con pestanas Acerca de / Actualizaciones."""

import os

from PySide6.QtCore import QCoreApplication, QSettings, Qt, QThread, QObject, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QDialog, QLabel, QMessageBox, QProgressBar,
    QPushButton, QTabWidget, QVBoxLayout, QWidget,
)

from app.core import updater
from app.core.translator import QtString
from app.core.utils import resource_path
from app.ui import theme

STACK_LINE = "PySide6 + SQLite + FFmpeg"
_ORG = "Audiovisual Production"
_APP = "CosechaMedia"


class _CheckWorker(QObject):
    done = Signal(object)
    error = Signal(str)

    def run(self):
        try:
            self.done.emit(updater.check_for_updates())
        except Exception as e:
            self.error.emit(str(e))


class _DownloadWorker(QObject):
    progress = Signal(int, int)
    done = Signal(str)
    error = Signal(str)

    def __init__(self, asset, dest):
        super().__init__()
        self._asset = asset
        self._dest = dest

    def run(self):
        try:
            path = updater.download_asset(self._asset, self._dest, self.progress.emit)
            updater.verify_download(path, self._asset)
            self.done.emit(path)
        except Exception as e:
            self.error.emit(str(e))


class AboutDialog(QDialog):
    def tr(self, text, *args, **kwargs):
        return QtString(super().tr(text, *args, **kwargs))

    def __init__(self, parent=None, check_updates=False):
        super().__init__(parent)
        self._threads = []
        self._info = None
        self._download_path = None

        self.setWindowTitle(self.tr("Acerca de CosechaMedia"))
        self.setMinimumSize(480, 440)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_about_tab(), self.tr("Acerca de"))
        self.tabs.addTab(self._build_updates_tab(), self.tr("Actualizaciones"))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.addWidget(self.tabs)

        if check_updates:
            self.tabs.setCurrentIndex(1)
            QTimer.singleShot(0, self._check_now)

    def _build_about_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        logo_path = resource_path(os.path.join("app", "ui", "logo.png"))
        if os.path.exists(logo_path):
            logo = QLabel()
            logo.setAlignment(Qt.AlignCenter)
            logo.setPixmap(QPixmap(logo_path).scaledToHeight(96, Qt.SmoothTransformation))
            layout.addWidget(logo)

        name = QLabel("CosechaMedia")
        name.setAlignment(Qt.AlignCenter)
        name.setStyleSheet("font-size: 22px; font-weight: bold; color: {0};".format(theme.color("accent")))
        layout.addWidget(name)

        version = QLabel(
            self.tr("Versión: %1").arg(QCoreApplication.applicationVersion() or "0.0.0")
        )
        version.setAlignment(Qt.AlignCenter)
        version.setStyleSheet("color: {0}; font-size: 12px;".format(theme.color("text_secondary")))
        layout.addWidget(version)

        desc = QLabel(self.tr("Herramienta de ingesta de tarjetas SD para producción audiovisual."))
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        desc.setStyleSheet("color: {0}; font-size: 12px;".format(theme.color("text")))
        layout.addWidget(desc)

        stack = QLabel(STACK_LINE)
        stack.setAlignment(Qt.AlignCenter)
        stack.setStyleSheet("color: {0}; font-size: 11px;".format(theme.color("text_secondary")))
        layout.addWidget(stack)

        credit = QLabel(self.tr("Desarrollado por %1").arg("JMW Studio / Joan Ramon Viñas"))
        credit.setAlignment(Qt.AlignCenter)
        credit.setStyleSheet("color: {0}; font-size: 11px;".format(theme.color("text_secondary")))
        layout.addWidget(credit)

        link = QLabel(
            '<a href="{url}" style="color: {accent};">{url}</a>'.format(
                url=updater.HTML_URL, accent=theme.color("accent")
            )
        )
        link.setAlignment(Qt.AlignCenter)
        link.setOpenExternalLinks(True)
        layout.addWidget(link)

        layout.addStretch()
        return page

    def _build_updates_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        self.lbl_current = QLabel(
            self.tr("Versión instalada: %1").arg(QCoreApplication.applicationVersion() or "0.0.0")
        )
        layout.addWidget(self.lbl_current)

        self.lbl_status = QLabel("")
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setStyleSheet("color: {0}; font-size: 12px;".format(theme.color("text_secondary")))
        layout.addWidget(self.lbl_status)

        self.btn_check = QPushButton(self.tr("Comprobar ahora"))
        self.btn_check.clicked.connect(self._check_now)
        layout.addWidget(self.btn_check)

        self.btn_download = QPushButton(self.tr("Descargar e instalar"))
        self.btn_download.setObjectName("PrimaryAction")
        self.btn_download.setVisible(False)
        self.btn_download.clicked.connect(self._start_download)
        layout.addWidget(self.btn_download)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        settings = QSettings(_ORG, _APP)
        self.chk_auto = QCheckBox(self.tr("Buscar actualizaciones al inicio"))
        self.chk_auto.setChecked(settings.value("checkUpdatesOnStart", True, type=bool))
        self.chk_auto.toggled.connect(self._on_auto_toggled)
        layout.addWidget(self.chk_auto)

        layout.addStretch()
        return page

    def _on_auto_toggled(self, checked):
        QSettings(_ORG, _APP).setValue("checkUpdatesOnStart", bool(checked))

    def _set_status(self, text, ok=False, error=False):
        if ok:
            color = theme.color("success")
        elif error:
            color = theme.color("danger")
        else:
            color = theme.color("text_secondary")
        self.lbl_status.setText(text)
        self.lbl_status.setStyleSheet("color: {0}; font-size: 12px;".format(color))

    def _check_now(self):
        self.btn_check.setEnabled(False)
        self.btn_download.setVisible(False)
        self._set_status(self.tr("Comprobando actualizaciones..."))
        worker = _CheckWorker()
        worker.done.connect(self._on_check_done)
        worker.error.connect(self._on_check_error)
        self._start_worker(worker)

    def _on_check_done(self, info):
        self.btn_check.setEnabled(True)
        self._info = info
        if not info["update_available"]:
            self._set_status(
                self.tr("Tienes la última versión instalada (%1).").arg(info["current_version"]),
                ok=True,
            )
            return
        if not info["asset"]:
            self._set_status(self.tr("No hay un paquete de actualización para tu sistema."), error=True)
            return
        self.btn_download.setVisible(True)
        self._set_status(
            self.tr("Nueva versión disponible: %1 (actual: %2).")
            .arg(info["latest_version"])
            .arg(info["current_version"]),
            ok=True,
        )

    def _on_check_error(self, message):
        self.btn_check.setEnabled(True)
        self._set_status(
            self.tr("No se pudo comprobar las actualizaciones: %1").arg(message), error=True
        )

    def _start_download(self):
        asset = self._info["asset"]
        self.btn_download.setEnabled(False)
        self._set_status(self.tr("Descargando %1...").arg(asset["name"]))
        self.progress.setVisible(True)
        self.progress.setValue(0)
        worker = _DownloadWorker(asset, updater.download_path_for(asset))
        worker.progress.connect(self._on_progress)
        worker.done.connect(self._on_download_done)
        worker.error.connect(self._on_download_error)
        self._start_worker(worker)

    def _on_progress(self, done, total):
        if total:
            self.progress.setValue(int(done * 100 / total))

    def _on_download_done(self, path):
        self.btn_download.setEnabled(True)
        self._download_path = path
        self.progress.setVisible(False)
        self._set_status(
            self.tr("Descarga completada y verificada. La actualización se instalará al reiniciar."),
            ok=True,
        )
        self._prompt_install()

    def _on_download_error(self, message):
        self.btn_download.setEnabled(True)
        self.progress.setVisible(False)
        self._set_status(
            self.tr("No se pudo descargar la actualización: %1").arg(message), error=True
        )

    def _prompt_install(self):
        reply = QMessageBox.question(
            self,
            self.tr("Instalar actualización"),
            self.tr("La aplicación se cerrará para instalar la nueva versión. ¿Continuar?"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            updater.install_update(self._info["asset"], self._download_path)
        except Exception as e:
            QMessageBox.critical(
                self, self.tr("Error"),
                self.tr("No se pudo instalar la actualización: %1").arg(str(e)),
            )
            return
        QApplication.quit()

    def _start_worker(self, worker):
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.done.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(thread.deleteLater)
        self._threads.append(thread)
        thread.start()
