from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor
from app.core import translator
from app.ui import theme
from app.ui.wheat_field import paint_wheat_field

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
