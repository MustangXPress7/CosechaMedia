"""Volcado selectivo por fecha (tarjetas "sucias" / smartphones).

Diálogo construido como conjunto de páginas (QStackedWidget) para poder
colgarse después como rama "smartphone" del futuro Modo guiado:
origen/destino -> escaneo -> calendario interactivo -> volcado verificado.
"""

import os
from datetime import datetime, timedelta

from PySide6.QtWidgets import (QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QProgressBar, QTableWidget,
                               QTableWidgetItem, QHeaderView, QCalendarWidget,
                               QMessageBox, QStackedWidget, QCheckBox,
                               QAbstractItemView)
from PySide6.QtCore import Qt, Signal, QObject, QThread, QDate, QTimer, QEvent
from PySide6.QtGui import QColor, QFont, QPen

from app.core.db import db
from app.core.metadata_engine import metadata_engine
from app.core.utils import create_folder_structure
from app.core.ingestor import copy_verified
from app.core.translator import QtString
from app.core import translator
from app.ui import theme

ORG_TYPE_MAP = {
    0: "camera_first",
    1: "date_first",
    2: "camera_only",
    3: "flat",
}


def _human_bytes(num: float) -> str:
    num = float(num)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} PB"


def _sanitize_name(name: str) -> str:
    for char in '<>:"/\\|?*':
        name = name.replace(char, "_")
    return name.strip() or "Unknown_Camera"


def _fmt_short_date(date_key: str) -> str:
    """'2025-05-25' -> '25-5-25'."""
    try:
        parts = date_key.split("-")
        if len(parts) == 3:
            return f"{int(parts[2])}-{int(parts[1])}-{int(parts[0]) % 100}"
    except (TypeError, ValueError):
        pass
    return date_key


def _is_next_day(prev: str, cur: str) -> bool:
    try:
        p = datetime.strptime(prev, "%Y-%m-%d").date()
        c = datetime.strptime(cur, "%Y-%m-%d").date()
        return c == p + timedelta(days=1)
    except ValueError:
        return False


def content_summary(content_filter) -> str:
    """Resumen legible de un filtro de contenido para la columna 'Contenido'.

    content_filter: None o dict {"dates": ["YYYY-MM-DD", ...], "include_nodate": bool}.
    """
    if not content_filter:
        return translator.tr("Todo")
    dates = sorted({d for d in content_filter.get("dates") or [] if isinstance(d, str)})
    include_nodate = bool(content_filter.get("include_nodate"))

    segments = []
    for d in dates:
        if segments and _is_next_day(segments[-1][-1], d):
            segments[-1].append(d)
        else:
            segments.append([d])

    text = ""
    if segments:
        if len(segments) == 1 and len(segments[0]) == 1:
            text = translator.tr("el %1").arg(_fmt_short_date(segments[0][0]))
        elif len(segments) == 1:
            first, last = segments[0][0], segments[0][-1]
            text = translator.tr("del %1 al %2").arg(_fmt_short_date(first)).arg(_fmt_short_date(last))
        else:
            text = translator.tr("%1 días").arg(len(dates))
    elif include_nodate:
        return translator.tr("Solo sin fecha")

    if include_nodate and text:
        text = f"{text} · " + translator.tr("sin fecha")
    return text or translator.tr("Todo")


class _AssistantWorker(QObject):
    """Ejecuta una función en un QThread notificando por señales Qt."""
    progress = Signal(int, int)
    message = Signal(str)
    finished = Signal(bool, object)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            result = self._fn(self, *self._args, **self._kwargs)
            self.finished.emit(True, result)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.finished.emit(False, e)


class DateSelectCalendar(QCalendarWidget):
    """Calendario con multiselección y días marcados según archivos.

    Clic simple selecciona un día, Ctrl añade/quita, Shift y arrastre
    seleccionan un rango. Los días con archivos se pintan con el acento del
    tema y su contador se dibuja bajo el número de día."""
    daysChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected = set()      # set[QDate]
        self.day_counts = {}       # QDate -> int
        self._anchor = None
        self._drag_date = None
        self._grid = None
        self._grid_viewport = None
        self.setSelectionMode(QCalendarWidget.SelectionMode.NoSelection)
        self.setGridVisible(True)
        self._grid = self._find_grid()
        if self._grid is not None:
            self._grid_viewport = self._grid.viewport()
            self._grid.installEventFilter(self)
            if self._grid_viewport is not None:
                self._grid_viewport.installEventFilter(self)

    def _find_grid(self):
        """Rejilla interna del calendario (QtPrivate::QCalendarView, un QTableView).

        En PySide6 6.11 QCalendarWidget.hitTest no está expuesto y los clics
        sobre el calendario se entregan al viewport de esa vista hija (no al
        propio widget), así que se filtran viewport y vista, y se hit-test con
        indexAt() en coordenadas del viewport."""
        for view in self.findChildren(QAbstractItemView):
            if view is not self:
                return view
        return None

    def set_day_counts(self, counts):
        self.day_counts = dict(counts)
        self.updateCells()
        if counts:
            dates = sorted(counts.keys())
            self.setMinimumDate(QDate(dates[0].year(), 1, 1))
            self.setMaximumDate(QDate(dates[-1].year(), 12, 31))
            self.setSelectedDate(dates[0])

    def clear_selection(self):
        self.selected = set()
        self.updateCells()
        self.daysChanged.emit()

    def select_all(self):
        self.selected = set(self.day_counts.keys())
        self.updateCells()
        self.daysChanged.emit()

    def paintCell(self, painter, rect, date):
        has_files = date in self.day_counts
        is_selected = date in self.selected
        is_today = date == QDate.currentDate()
        in_month = date.month() == self.monthShown()

        if not in_month:
            painter.fillRect(rect, QColor(theme.color("bg")))
        else:
            painter.fillRect(rect, QColor(theme.color("bg_elevated")))

        if has_files and not is_selected:
            accent = QColor(theme.color("accent"))
            accent.setAlpha(90)
            painter.fillRect(rect, accent)

        if is_selected:
            painter.fillRect(rect, QColor(theme.color("accent_selection")))

        if is_today:
            painter.setPen(QPen(QColor(theme.color("accent")), 2))
            painter.drawRect(rect.adjusted(1, 1, -1, -1))

        text_color = QColor(theme.color("text"))
        if not in_month:
            text_color = QColor(theme.color("text_disabled"))
        if is_selected:
            text_color = QColor(theme.color("on_accent"))

        painter.setPen(text_color)
        painter.setFont(QFont(painter.font().family(), 9, QFont.Normal))
        painter.drawText(rect.adjusted(0, 2, 0, 0), Qt.AlignTop | Qt.AlignHCenter, str(date.day()))

        if has_files:
            painter.setPen(QColor(theme.color("text_secondary")))
            painter.setFont(QFont(painter.font().family(), 8, QFont.Normal))
            painter.drawText(rect.adjusted(0, 0, 0, -2), Qt.AlignBottom | Qt.AlignHCenter,
                             str(self.day_counts.get(date, 0)))

    def _date_at(self, pos):
        """Fecha bajo un punto en coordenadas del viewport de la rejilla.

        Recorre los rects reales de las celdas (los mismos que Qt usa para
        pintar) en lugar de indexAt(): con alturas de fila fraccionarias o
        scroll interno, indexAt puede desviarse una fila del clic."""
        if self._grid is None:
            return None
        try:
            model = self._grid.model()
        except Exception:
            return None
        if model is None:
            return None
        for row in range(1, model.rowCount()):
            for col in range(1, model.columnCount()):
                try:
                    rect = self._grid.visualRect(model.index(row, col))
                except Exception:
                    continue
                if rect is not None and rect.contains(pos):
                    return self._date_for_index(row, col)
        return None

    def _date_for_index(self, row, col):
        # La rejilla es 7 filas x 8 columnas: fila 0 = cabecera de días,
        # col 0 = número de semana, cols 1..7 = lun..dom.
        if row < 1 or col < 1:
            return None
        first = QDate(self.yearShown(), self.monthShown(), 1)
        monday = first.addDays(-(first.dayOfWeek() - 1))
        return monday.addDays((row - 1) * 7 + (col - 1))

    def _viewport_pos(self, obj, pos):
        """Convierte un punto del widget que entregó el evento (vista o
        viewport) a coordenadas del viewport, que es lo que indexAt() espera."""
        if self._grid_viewport is not None and obj is not self._grid_viewport:
            return self._grid_viewport.mapFrom(self._grid, pos)
        return pos

    def eventFilter(self, obj, event):
        if obj is self._grid or obj is self._grid_viewport:
            etype = event.type()
            if etype in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonDblClick):
                if event.button() == Qt.LeftButton:
                    pos = self._viewport_pos(obj, event.position().toPoint())
                    self._handle_press(pos, event.modifiers())
                    return True
            elif etype == QEvent.Type.MouseMove:
                if event.buttons() & Qt.LeftButton:
                    pos = self._viewport_pos(obj, event.position().toPoint())
                    self._handle_drag(pos)
                    return True
            elif etype == QEvent.Type.MouseButtonRelease:
                self._drag_date = None
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._grid_viewport is not None:
            pos = self._grid_viewport.mapFrom(self, event.pos())
            if self._grid_viewport.rect().contains(pos):
                self._handle_press(pos, event.modifiers())
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._grid_viewport is not None and (event.buttons() & Qt.LeftButton):
            pos = self._grid_viewport.mapFrom(self, event.pos())
            self._handle_drag(pos)
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_date = None
        super().mouseReleaseEvent(event)

    def _handle_press(self, pos, modifiers):
        date = self._date_at(pos)
        if date is None:
            return
        if modifiers & Qt.ShiftModifier and self._anchor:
            self._select_range(self._anchor, date)
        elif modifiers & Qt.ControlModifier:
            self._toggle(date)
        else:
            self.selected = {date}
            self._anchor = date
        self._drag_date = date
        self.updateCells()
        self.daysChanged.emit()

    def _handle_drag(self, pos):
        if self._drag_date is None:
            return
        date = self._date_at(pos)
        if date is None:
            return
        self._select_range(self._drag_date, date)
        self.updateCells()
        self.daysChanged.emit()

    def _toggle(self, date):
        if date in self.selected:
            self.selected.discard(date)
        else:
            self.selected.add(date)

    def _select_range(self, d1, d2):
        start, end = min(d1, d2), max(d1, d2)
        self.selected = set()
        day = start
        while day <= end:
            self.selected.add(day)
            day = day.addDays(1)


class SelectiveDumpAssistant(QDialog):
    def tr(self, text, *args, **kwargs):
        return QtString(super().tr(text, *args, **kwargs))

    def __init__(self, parent=None, source_path=None, project_config=None, mode="dump", auto_scan=True):
        super().__init__(parent)
        self._mode = mode
        if mode == "filter":
            self.setWindowTitle(self.tr("Seleccionar contenido del origen"))
        else:
            self.setWindowTitle(self.tr("Volcado selectivo por fecha"))
        self.setMinimumSize(880, 600)
        self.setModal(True)

        self._source = source_path or ""
        cfg = project_config or {}
        self._dest_root = cfg.get("dest_root") or ""
        self._folder_name = cfg.get("folder_name") or "Footage"
        self._order_type = ORG_TYPE_MAP.get(cfg.get("organization_type", 0), "camera_first")
        self._default_camera = cfg.get("default_camera") or ""
        self._project_id = cfg.get("project_id")

        self.content_filter = None
        self.content_text = None
        self._cancel_flag = False
        self._close_when_done = False
        self._thread = None
        self._worker = None
        self._scan_result = None
        self._jobs = []

        self._build_ui()

        if mode == "filter" and auto_scan:
            QTimer.singleShot(0, self._start_scan)

    def _build_ui(self):
        self._stack = QStackedWidget(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(self._stack)

        self._setup_page = self._build_setup_page()
        self._scan_page = self._build_scan_page()
        self._select_page = self._build_select_page()
        self._dump_page = self._build_dump_page()
        self._stack.addWidget(self._setup_page)
        self._stack.addWidget(self._scan_page)
        self._stack.addWidget(self._select_page)
        self._stack.addWidget(self._dump_page)

    # ---- Página 0: configuración ----
    def _build_setup_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(8)

        title = QLabel(self.tr("Volcado selectivo por fecha"))
        title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {theme.color('accent')};")
        layout.addWidget(title)

        desc = QLabel(self.tr(
            "Para tarjetas que acumulan grabaciones de distintos días (p. ej. smartphones). "
            "Escanea el origen, agrupa los archivos por día de grabación y te deja elegir "
            "qué días volcar. La copia es verificada por MD5."))
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {theme.color('text_secondary')};")
        layout.addWidget(desc)

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton(self.tr("Cancelar"))
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)
        btn_row.addStretch()
        self.btn_scan = QPushButton(self.tr("Escanear"))
        self.btn_scan.setObjectName("PrimaryAction")
        self.btn_scan.clicked.connect(self._start_scan)
        btn_row.addWidget(self.btn_scan)
        layout.addLayout(btn_row)

        return page

    # ---- Página 1: escaneo ----
    def _build_scan_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addStretch(1)

        title = QLabel(self.tr("Escaneando..."))
        title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {theme.color('accent')};")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self.scan_progress = QProgressBar()
        self.scan_progress.setMinimumHeight(22)
        layout.addWidget(self.scan_progress)

        self.scan_status = QLabel("")
        self.scan_status.setAlignment(Qt.AlignCenter)
        self.scan_status.setStyleSheet(f"color: {theme.color('text_secondary')};")
        layout.addWidget(self.scan_status)

        layout.addStretch(1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_scan_cancel = QPushButton(self.tr("Cancelar"))
        self.btn_scan_cancel.clicked.connect(self._cancel_current_work)
        btn_row.addWidget(self.btn_scan_cancel)
        layout.addLayout(btn_row)

        return page

    # ---- Página 2: calendario + previsualización ----
    def _build_select_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(8)

        self.sel_header = QLabel("")
        self.sel_header.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {theme.color('accent')};")
        layout.addWidget(self.sel_header)

        content = QHBoxLayout()
        content.setSpacing(10)

        # Columna izquierda: calendario
        left = QVBoxLayout()
        left.setSpacing(6)
        self.calendar = DateSelectCalendar()
        self.calendar.daysChanged.connect(self._update_preview)
        left.addWidget(self.calendar, 1)

        legend = QHBoxLayout()
        legend.setSpacing(8)
        for color_name, label in [("accent", self.tr("con archivos")),
                                  ("accent_selection", self.tr("seleccionado"))]:
            swatch = QLabel("   ")
            swatch.setFixedWidth(18)
            swatch.setStyleSheet(
                f"background-color: {theme.color(color_name)}; border-radius: 3px;")
            legend.addWidget(swatch)
            legend.addWidget(QLabel(label))
            legend.addSpacing(6)
        legend.addStretch()
        left.addLayout(legend)

        cal_buttons = QHBoxLayout()
        self.btn_select_all = QPushButton(self.tr("Seleccionar todo"))
        self.btn_select_all.clicked.connect(self.calendar.select_all)
        cal_buttons.addWidget(self.btn_select_all)
        self.btn_clear = QPushButton(self.tr("Limpiar"))
        self.btn_clear.clicked.connect(self.calendar.clear_selection)
        cal_buttons.addWidget(self.btn_clear)
        cal_buttons.addStretch()
        left.addLayout(cal_buttons)

        hint = QLabel(self.tr("Clic: seleccionar · Ctrl: añadir/quitar · Shift o arrastre: rango"))
        hint.setStyleSheet(f"color: {theme.color('text_secondary')}; font-size: 10px;")
        left.addWidget(hint)
        content.addLayout(left, 3)

        # Columna derecha: previsualización
        right = QVBoxLayout()
        right.setSpacing(6)
        preview_label = QLabel(self.tr("Archivos de los días seleccionados:"))
        right.addWidget(preview_label)

        self.preview_table = QTableWidget(0, 4)
        self.preview_table.setHorizontalHeaderLabels(
            [self.tr("Archivo"), self.tr("Fecha"), self.tr("Tamaño"), self.tr("Tipo")])
        header = self.preview_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.preview_table.verticalHeader().setVisible(False)
        self.preview_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        right.addWidget(self.preview_table, 1)

        self.lbl_selected = QLabel("")
        self.lbl_selected.setStyleSheet(f"color: {theme.color('text_secondary')};")
        right.addWidget(self.lbl_selected)

        self.chk_include_nodate = QCheckBox(self.tr("Incluir archivos sin fecha (se volcarán con la fecha de hoy)"))
        right.addWidget(self.chk_include_nodate)

        content.addLayout(right, 4)
        layout.addLayout(content, 1)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton(self.tr("Cancelar"))
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)
        btn_row.addStretch()
        self.btn_dump = QPushButton(
            self.tr("Volcar selección") if self._mode == "dump" else self.tr("Aplicar selección"))
        self.btn_dump.setObjectName("PrimaryAction")
        if self._mode == "dump":
            self.btn_dump.clicked.connect(self._start_dump)
        else:
            self.btn_dump.clicked.connect(self._apply_selection)
        btn_row.addWidget(self.btn_dump)
        layout.addLayout(btn_row)

        return page

    # ---- Página 3: volcado ----
    def _build_dump_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addStretch(1)

        title = QLabel(self.tr("Volcando..."))
        title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {theme.color('accent')};")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self.dump_progress = QProgressBar()
        self.dump_progress.setMinimumHeight(22)
        layout.addWidget(self.dump_progress)

        self.dump_status = QLabel("")
        self.dump_status.setAlignment(Qt.AlignCenter)
        self.dump_status.setStyleSheet(f"color: {theme.color('text_secondary')};")
        layout.addWidget(self.dump_status)

        layout.addStretch(1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_dump_cancel = QPushButton(self.tr("Detener"))
        self.btn_dump_cancel.clicked.connect(self._cancel_current_work)
        btn_row.addWidget(self.btn_dump_cancel)
        layout.addLayout(btn_row)

        return page

    # ---- Navegación ----
    def _start_scan(self):
        source = self._source.strip()
        if not source or not os.path.isdir(source):
            QMessageBox.warning(self, self.tr("Origen inválido"),
                                self.tr("No hay un origen configurado para el proyecto."))
            return
        if self._mode != "filter" and not self._dest_root:
            QMessageBox.warning(self, self.tr("Destino inválido"),
                                self.tr("No hay ruta maestra configurada para el proyecto."))
            return
        self._stack.setCurrentWidget(self._scan_page)
        self.scan_progress.setValue(0)
        self.scan_status.setText("")
        self.btn_scan_cancel.setEnabled(True)
        self._start_work(self._scan_work, self._on_scan_done)

    def _scan_work(self, worker):
        source = self._source.strip()
        return {
            "source": source,
            "result": metadata_engine.scan_source_for_dates(
                source,
                progress_cb=lambda done, total: worker.progress.emit(done, total),
                cancel_cb=lambda: self._cancel_flag,
            ),
        }

    def _on_scan_done(self, ok, payload):
        self.btn_scan_cancel.setEnabled(False)
        if self._close_when_done:
            self._close_when_done = False
            self._cancel_flag = False
            super().reject()
            return
        if not ok:
            QMessageBox.critical(self, self.tr("Error"),
                                 self.tr("No se pudo escanear el origen: %1").arg(str(payload)))
            self._stack.setCurrentWidget(self._setup_page)
            return
        if self._cancel_flag:
            self._cancel_flag = False
            self._stack.setCurrentWidget(self._setup_page)
            return
        self._source = payload["source"]
        result = payload["result"]
        self._scan_result = result
        self._jobs = []
        self._populate_calendar(result)
        self._stack.setCurrentWidget(self._select_page)

    def _populate_calendar(self, result):
        counts = {}
        for date_key, files in result.get("by_date", {}).items():
            parts = date_key.split("-")
            if len(parts) == 3:
                qdate = QDate(int(parts[0]), int(parts[1]), int(parts[2]))
                if qdate.isValid():
                    counts[qdate] = len(files)
        self.calendar.set_day_counts(counts)
        self.calendar.select_all()

        total_files = sum(len(v) for v in result.get("by_date", {}).values())
        total_days = len(result.get("by_date", {}))
        no_date = len(result.get("no_date", []))
        if no_date:
            header = self.tr("%1 archivos en %2 día(s) de grabación · %3 sin fecha") \
                .arg(total_files).arg(total_days).arg(no_date)
        else:
            header = self.tr("%1 archivos en %2 día(s) de grabación") \
                .arg(total_files).arg(total_days)
        self.sel_header.setText(header)
        self.chk_include_nodate.setChecked(no_date > 0)

    def _update_preview(self):
        by_date = (self._scan_result or {}).get("by_date", {})
        rows = []
        for qdate in sorted(self.calendar.selected):
            key = qdate.toString("yyyy-MM-dd")
            for path in by_date.get(key, []):
                rows.append((key, path))

        self.preview_table.setRowCount(0)
        total_size = 0
        for key, path in sorted(rows, key=lambda r: (r[0], os.path.basename(r[1]))):
            try:
                size = os.path.getsize(path)
            except OSError:
                size = 0
            total_size += size
            row = self.preview_table.rowCount()
            self.preview_table.insertRow(row)
            self.preview_table.setItem(row, 0, QTableWidgetItem(os.path.basename(path)))
            self.preview_table.setItem(row, 1, QTableWidgetItem(key))
            self.preview_table.setItem(row, 2, QTableWidgetItem(_human_bytes(size)))
            info = metadata_engine.get_file_type_info(path)
            self.preview_table.setItem(row, 3, QTableWidgetItem(info.get("type", "")))

        text = self.tr("%1 archivos · %2 · %3 día(s) seleccionado(s)") \
            .arg(len(rows)).arg(_human_bytes(total_size)).arg(len(self.calendar.selected))
        summary = content_summary({
            "dates": sorted(qdate.toString("yyyy-MM-dd") for qdate in self.calendar.selected),
            "include_nodate": self.chk_include_nodate.isChecked(),
        })
        if summary:
            text = f"{text} · {summary}"
        self.lbl_selected.setText(text)

    # ---- Volcado ----
    def _apply_selection(self):
        by_date = (self._scan_result or {}).get("by_date", {})
        dates = sorted(qdate.toString("yyyy-MM-dd") for qdate in self.calendar.selected)
        include_nodate = self.chk_include_nodate.isChecked()
        no_date = (self._scan_result or {}).get("no_date", [])
        full = set(by_date.keys()).issubset(set(dates)) and (include_nodate or not no_date)
        if full:
            self.content_filter = None
        else:
            self.content_filter = {"dates": dates, "include_nodate": include_nodate}
        self.content_text = content_summary(self.content_filter)
        self.accept()

    def _camera_for(self, path):
        meta = metadata_engine.get_video_metadata(path)
        cam = meta.get("camera_model") if meta else None
        if not cam or cam in ("Unknown", "Unknown_Camera", ""):
            cam = self._default_camera or "Unknown_Camera"
        return _sanitize_name(cam)

    def _build_jobs(self):
        by_date = (self._scan_result or {}).get("by_date", {})
        jobs = []
        for qdate in sorted(self.calendar.selected):
            key = qdate.toString("yyyy-MM-dd")
            for path in by_date.get(key, []):
                jobs.append({"path": path, "camera": self._camera_for(path), "date": key})
        if self.chk_include_nodate.isChecked():
            today = datetime.now().strftime("%Y-%m-%d")
            for path in (self._scan_result or {}).get("no_date", []):
                jobs.append({"path": path, "camera": self._camera_for(path), "date": today})
        return jobs

    @staticmethod
    def _unique_dest(dest_dir, src):
        base, ext = os.path.splitext(os.path.basename(src))
        dest_path = os.path.join(dest_dir, os.path.basename(src))
        n = 1
        while os.path.exists(dest_path):
            dest_path = os.path.join(dest_dir, f"{base} ({n}){ext}")
            n += 1
        return dest_path

    def _start_dump(self):
        jobs = self._build_jobs()
        if not jobs:
            QMessageBox.warning(self, self.tr("Sin archivos"),
                                self.tr("No hay archivos seleccionados para volcar."))
            return
        self._jobs = jobs
        self._stack.setCurrentWidget(self._dump_page)
        self.dump_progress.setValue(0)
        self.dump_status.setText("")
        self.btn_dump_cancel.setEnabled(True)
        self._start_work(self._dump_work, self._on_dump_done)

    def _dump_work(self, worker):
        jobs = self._jobs
        total = len(jobs)
        processed = 0
        errors = 0

        sid = None
        if self._project_id is not None:
            sid = db.create_session(
                self._project_id,
                self.tr("Volcado selectivo %1").arg(datetime.now().strftime("%Y-%m-%d %H:%M")),
                shoot_date=None,
                status="active",
                source_path=self._source,
            )

        conn = db.get_connection()
        try:
            for i, job in enumerate(jobs, start=1):
                if self._cancel_flag:
                    break
                worker.progress.emit(i, total)
                worker.message.emit(os.path.basename(job["path"]))
                try:
                    dest_dir = create_folder_structure(
                        self._dest_root, job["camera"], job["date"],
                        self._order_type, self._folder_name)
                    dest_path = self._unique_dest(dest_dir, job["path"])
                    md5 = copy_verified(job["path"], dest_path)
                    if md5 is None:
                        errors += 1
                        continue
                    size = os.path.getsize(dest_path)
                    if sid is not None:
                        cursor = conn.cursor()
                        cursor.execute(
                            '''INSERT INTO files (session_id, source_path, dest_path, file_size,
                                                  md5_hash, status, verified_at)
                               VALUES (?, ?, ?, ?, ?, 'completed', CURRENT_TIMESTAMP)''',
                            (str(sid), job["path"], dest_path, size, md5))
                        conn.commit()
                    processed += 1
                except Exception as e:
                    print(f"Error volcando {job['path']}: {e}")
                    errors += 1
        finally:
            conn.close()

        if sid is not None:
            db.update_session_config(
                sid, status="completed" if not self._cancel_flag else "cancelled",
                shoot_date=None)

        return {"processed": processed, "errors": errors, "total": total,
                "cancelled": self._cancel_flag, "session_id": sid}

    def _on_dump_done(self, ok, payload):
        self.btn_dump_cancel.setEnabled(False)
        if self._close_when_done:
            self._close_when_done = False
            self._cancel_flag = False
            super().reject()
            return
        if not ok:
            QMessageBox.critical(self, self.tr("Error"),
                                 self.tr("El volcado no pudo completarse: %1").arg(str(payload)))
            self._stack.setCurrentWidget(self._select_page)
            return
        if payload.get("cancelled"):
            QMessageBox.information(
                self, self.tr("Volcado detenido"),
                self.tr("Volcado detenido por el usuario.\n%1 procesados, %2 errores.")
                .arg(payload["processed"]).arg(payload["errors"]))
            self._stack.setCurrentWidget(self._select_page)
            return
        QMessageBox.information(
            self, self.tr("Volcado completado"),
            self.tr("Volcado selectivo finalizado.\n\n%1 archivos volcados correctamente.\n%2 errores.")
            .arg(payload["processed"]).arg(payload["errors"]))
        self.accept()

    # ---- Hilos ----
    def _start_work(self, fn, on_done):
        self._cancel_flag = False
        self._close_when_done = False
        thread = QThread(self)
        worker = _AssistantWorker(fn)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self._on_progress)
        worker.message.connect(self._on_message)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        ref = [thread, worker]
        thread.finished.connect(lambda t=thread, w=worker: self._on_thread_finished(t, w))
        thread.finished.connect(thread.deleteLater)
        worker.finished.connect(on_done)
        self._thread = thread
        self._worker = worker
        thread.start()

    def _on_thread_finished(self, thread, worker):
        if self._thread is thread:
            self._thread = None
        if self._worker is worker:
            self._worker = None

    def _on_progress(self, done, total):
        current = self._stack.currentWidget()
        if current is self._scan_page:
            bar = self.scan_progress
        elif current is self._dump_page:
            bar = self.dump_progress
        else:
            return
        bar.setMaximum(max(total, 1))
        bar.setValue(done)

    def _on_message(self, text):
        current = self._stack.currentWidget()
        if current is self._scan_page:
            self.scan_status.setText(text)
        elif current is self._dump_page:
            self.dump_status.setText(text)

    def _cancel_current_work(self):
        self._cancel_flag = True
        current = self._stack.currentWidget()
        if current is self._scan_page:
            self.scan_status.setText(self.tr("Cancelando…"))
            self.btn_scan_cancel.setEnabled(False)
        elif current is self._dump_page:
            self.dump_status.setText(self.tr("Cancelando…"))
            self.btn_dump_cancel.setEnabled(False)

    def reject(self):
        thread = self._thread
        if thread is not None:
            running = False
            try:
                running = thread.isRunning()
            except RuntimeError:
                # El QThread ya fue borrado (deleteLater) tras terminar.
                self._thread = None
            if running:
                self._close_when_done = True
                self._cancel_current_work()
                return
        super().reject()
