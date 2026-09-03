"""Reorganizador de footage: mueve archivos de SinClasificar/ a cámara/fecha
con verificación MD5 y re-registro en DB.

Flujo: selector de carpeta → escaneo off-thread → resumen → ejecución off-thread
con shutil.move + calculate_md5 + UPDATE files.
"""

import os
import shutil
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QStackedWidget, QMessageBox, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal, QObject, QThread

from app.core.utils import create_folder_structure, calculate_md5
from app.core.db import db
from app.core.metadata_engine import metadata_engine
from app.core.translator import QtString
from app.ui import theme


def _human_bytes(num: int) -> str:
    """Formato legible de bytes."""
    num = float(num)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} PB"


def _sanitize_name(name: str) -> str:
    """Sanitiza nombre de carpeta (igual que selective_dump)."""
    for char in '<>:"/\\|?*':
        name = name.replace(char, "_")
    return name.strip() or "SinClasificar"


def _unique_dest(dest_dir: str, src_path: str) -> str:
    """Genera ruta destino única aplicando sufijo (n) si hay colisión."""
    base, ext = os.path.splitext(os.path.basename(src_path))
    dest_path = os.path.join(dest_dir, os.path.basename(src_path))
    n = 1
    while os.path.exists(dest_path):
        dest_path = os.path.join(dest_dir, f"{base} ({n}){ext}")
        n += 1
    return dest_path


class _ScanWorker(QObject):
    """Worker para escanear SinClasificar/ off-thread."""
    progress = Signal(str)
    finished = Signal(bool, object)

    def __init__(self, project_root: str):
        super().__init__()
        self.project_root = project_root

    def run(self):
        try:
            result = self._scan()
            self.finished.emit(True, result)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.finished.emit(False, str(e))

    def _scan(self):
        self.progress.emit("Escaneando SinClasificar…")
        sinclasificar = os.path.join(self.project_root, "SinClasificar")
        if not os.path.exists(sinclasificar):
            return {"error": "No existe carpeta SinClasificar"}

        summary = {}
        unclassified = []

        for root, dirs, files in os.walk(sinclasificar):
            # Saltar la propia carpeta SinClasificar como raíz
            if root == sinclasificar and not files:
                continue
            for fname in files:
                file_path = os.path.join(root, fname)
                try:
                    meta = metadata_engine.get_video_metadata(file_path)
                    camera = meta.get("camera_model", "") or ""
                    creation = meta.get("creation_time")

                    if not camera:
                        unclassified.append(file_path)
                        continue

                    camera = _sanitize_name(camera)

                    # Extraer fecha
                    date_key = "sin-fecha"
                    if creation:
                        try:
                            date_key = creation.split("T")[0]
                        except (AttributeError, IndexError):
                            pass

                    summary.setdefault(camera, {}).setdefault(date_key, []).append(file_path)
                except Exception as e:
                    print(f"Error reorganizando {file_path}: {e}")
                    unclassified.append(file_path)

        result = {"summary": summary, "unclassified": unclassified}
        self.progress.emit("Escaneo completado")
        return result


class _MoveWorker(QObject):
    """Worker para ejecutar el movimiento y re-registro MD5 off-thread."""
    progress = Signal(str)
    finished = Signal(bool, object)

    def __init__(self, project_root: str, summary: dict, unclassified: list):
        super().__init__()
        self.project_root = project_root
        self.summary = summary
        self.unclassified = unclassified

    def run(self):
        try:
            result = self._execute_move()
            self.finished.emit(True, result)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.finished.emit(False, str(e))

    def _execute_move(self):
        moved = 0
        errors = 0
        error_details = []

        for camera, dates in self.summary.items():
            for date_key, files in dates.items():
                dest_dir = create_folder_structure(self.project_root, camera, date_key)
                for file_path in files:
                    try:
                        new_path = _unique_dest(dest_dir, file_path)
                        shutil.move(file_path, new_path)

                        # D-19/D-20: Recalcular MD5 y re-registrar en DB
                        md5_hash = None
                        try:
                            md5_hash = calculate_md5(new_path)
                        except Exception as e:
                            print(f"Error calculando MD5 de {new_path}: {e}")
                            # Reintento único
                            try:
                                md5_hash = calculate_md5(new_path)
                            except Exception as e2:
                                print(f"Reintento MD5 falló para {new_path}: {e2}")
                                md5_hash = None

                        # Actualizar DB: dest_path SIEMPRE, md5_hash NULL si falló
                        try:
                            conn = db.get_connection()
                            cursor = conn.cursor()
                            cursor.execute(
                                "UPDATE files SET dest_path = ?, md5_hash = ? WHERE dest_path LIKE ?",
                                (new_path, md5_hash, file_path + "%")
                            )
                            conn.commit()
                            conn.close()
                        except Exception as e:
                            print(f"Error actualizando DB para {file_path}: {e}")
                            errors += 1
                            error_details.append(f"{file_path}: DB error")
                            continue

                        moved += 1
                        self.progress.emit(f"Movido: {os.path.basename(file_path)} → {camera}/{date_key}")
                    except Exception as e:
                        print(f"Error moviendo {file_path}: {e}")
                        errors += 1
                        error_details.append(f"{file_path}: {e}")

        result = {
            "moved": moved,
            "unclassified": len(self.unclassified),
            "errors": errors,
            "error_details": error_details,
        }
        self.progress.emit("Reorganización completada")
        return result


class ReorganizeDialog(QDialog):
    """Diálogo principal para reorganizar footage."""

    def tr(self, text, *args, **kwargs):
        return QtString(super().tr(text, *args, **kwargs))

    def __init__(self, parent=None, project_root=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Reorganizar footage…"))
        self.setMinimumSize(700, 500)
        self.project_root = project_root
        self._scan_result = None
        self._thread = None
        self._worker = None

        self._build_ui()
        self._check_initial_sinclasificar()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self._stack = QStackedWidget()
        layout.addWidget(self._stack, 1)

        # Página 1: Selección de carpeta
        self._page_select = self._build_select_page()
        self._stack.addWidget(self._page_select)

        # Página 2: Resumen del escaneo
        self._page_summary = self._build_summary_page()
        self._stack.addWidget(self._page_summary)

        # Página 3: Ejecución y resultado
        self._page_execute = self._build_execute_page()
        self._stack.addWidget(self._page_execute)

    # -------------------------------------------------------------------------
    # Página 1: Selección de carpeta
    # -------------------------------------------------------------------------
    def _build_select_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        self.lbl_info = QLabel(self.tr(
            "Seleccione la carpeta raíz del volcado que contiene la subcarpeta SinClasificar/"
        ))
        self.lbl_info.setWordWrap(True)
        layout.addWidget(self.lbl_info)

        # Selector de carpeta
        folder_layout = QHBoxLayout()
        self.txt_folder = QLabel()
        self.txt_folder.setStyleSheet("font-family: monospace; color: {};".format(
            theme.color("text_secondary")
        ))
        folder_layout.addWidget(self.txt_folder, 1)

        self.btn_browse = QPushButton(self.tr("Examinar…"))
        self.btn_browse.clicked.connect(self._on_browse)
        folder_layout.addWidget(self.btn_browse)

        layout.addLayout(folder_layout)

        # Mensaje rápido si ya existe SinClasificar
        self.lbl_quick = QLabel("")
        self.lbl_quick.setStyleSheet("color: {};".format(
            theme.color("success")
        ))
        self.lbl_quick.setVisible(False)
        layout.addWidget(self.lbl_quick)

        layout.addStretch()

        # Botón Escanear
        self.btn_scan = QPushButton(self.tr("Escanear"))
        self.btn_scan.setObjectName("PrimaryAction")
        self.btn_scan.clicked.connect(self._on_scan)
        self.btn_scan.setEnabled(False)
        layout.addWidget(self.btn_scan)

        return page

    def _check_initial_sinclasificar(self):
        if self.project_root:
            sinclasificar = os.path.join(self.project_root, "SinClasificar")
            if os.path.exists(sinclasificar):
                self.txt_folder.setText(self.project_root)
                self._count_files_quick(sinclasificar)
                self.btn_scan.setEnabled(True)

    def _count_files_quick(self, sinclasificar_path):
        count = 0
        for root, dirs, files in os.walk(sinclasificar_path):
            count += len(files)
        if count > 0:
            self.lbl_quick.setText(self.tr("Se encontraron {0} archivos sin clasificar en SinClasificar/").arg(count))
            self.lbl_quick.setVisible(True)

    def _on_browse(self):
        path = QFileDialog.getExistingDirectory(
            self, self.tr("Seleccionar carpeta raíz del volcado"), self.project_root or ""
        )
        if path:
            self.project_root = path
            self.txt_folder.setText(path)
            sinclasificar = os.path.join(path, "SinClasificar")
            if os.path.exists(sinclasificar):
                self._count_files_quick(sinclasificar)
                self.btn_scan.setEnabled(True)
            else:
                self.lbl_quick.setText(self.tr("No se encontró la carpeta SinClasificar/ en la ubicación seleccionada."))
                self.lbl_quick.setStyleSheet("color: {};".format(
                    theme.color("warning")
                ))
                self.lbl_quick.setVisible(True)
                self.btn_scan.setEnabled(False)

    def _on_scan(self):
        self.btn_scan.setEnabled(False)
        self._start_scan_worker()

    def _start_scan_worker(self):
        self._worker = _ScanWorker(self.project_root)
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_scan_progress)
        self._worker.finished.connect(self._on_scan_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _on_scan_progress(self, msg):
        pass  # Podríamos mostrar en status bar

    def _on_scan_finished(self, success, result):
        if not success:
            QMessageBox.warning(self, self.tr("Error"), self.tr("Error en el escaneo: {0}").arg(result))
            self.btn_scan.setEnabled(True)
            return

        if "error" in result:
            QMessageBox.information(self, self.tr("SinClasificar"), self.tr(result["error"]))
            self.btn_scan.setEnabled(True)
            return

        self._scan_result = result
        self._populate_summary(result)
        self._stack.setCurrentWidget(self._page_summary)

    # -------------------------------------------------------------------------
    # Página 2: Resumen del escaneo
    # -------------------------------------------------------------------------
    def _build_summary_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self.lbl_summary_title = QLabel(self.tr("Resumen del escaneo"))
        self.lbl_summary_title.setStyleSheet("font-weight: 600; font-size: 14px;")
        layout.addWidget(self.lbl_summary_title)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            self.tr("Cámara"), self.tr("Fecha"), self.tr("Nº archivos"), self.tr("Tamaño total")
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table, 1)

        self.lbl_summary_count = QLabel("")
        layout.addWidget(self.lbl_summary_count)

        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel_summary = QPushButton(self.tr("Cancelar"))
        self.btn_cancel_summary.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel_summary)

        self.btn_reorganize = QPushButton(self.tr("Reorganizar"))
        self.btn_reorganize.setObjectName("PrimaryAction")
        self.btn_reorganize.clicked.connect(self._on_reorganize)
        btn_layout.addWidget(self.btn_reorganize)

        layout.addLayout(btn_layout)
        return page

    def _populate_summary(self, result):
        summary = result["summary"]
        unclassified = result["unclassified"]

        rows = []
        total_files = 0
        total_size = 0

        for camera, dates in sorted(summary.items()):
            for date_key, files in sorted(dates.items()):
                size = sum(os.path.getsize(f) for f in files if os.path.exists(f))
                rows.append((camera, date_key, len(files), size))
                total_files += len(files)
                total_size += size

        # Añadir fila de sin clasificar si hay
        if unclassified:
            size = sum(os.path.getsize(f) for f in unclassified if os.path.exists(f))
            rows.append((self.tr("SinClasificar (sin clasificar)"), "—", len(unclassified), size))
            total_files += len(unclassified)
            total_size += size

        self.table.setRowCount(len(rows))
        for i, (cam, date, count, size) in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(cam))
            self.table.setItem(i, 1, QTableWidgetItem(date))
            self.table.setItem(i, 2, QTableWidgetItem(str(count)))
            self.table.setItem(i, 3, QTableWidgetItem(_human_bytes(size)))

        if total_files > 0:
            self.btn_reorganize.setEnabled(True)
            self.lbl_summary_count.setText(
                self.tr("{0} archivos se moverán a sus carpetas correspondientes").arg(total_files)
            )
        else:
            self.btn_reorganize.setEnabled(False)
            self.lbl_summary_count.setText(self.tr("No hay archivos para reorganizar."))

    def _on_reorganize(self):
        self.btn_reorganize.setEnabled(False)
        self.btn_cancel_summary.setEnabled(False)
        self._stack.setCurrentWidget(self._page_execute)
        self._start_move_worker()

    # -------------------------------------------------------------------------
    # Página 3: Ejecución y resultado
    # -------------------------------------------------------------------------
    def _build_execute_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        self.lbl_execute_status = QLabel(self.tr("Reorganizando archivos…"))
        self.lbl_execute_status.setWordWrap(True)
        layout.addWidget(self.lbl_execute_status)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # Indeterminado
        layout.addWidget(self.progress)

        self.lbl_result = QLabel("")
        self.lbl_result.setWordWrap(True)
        self.lbl_result.setVisible(False)
        layout.addWidget(self.lbl_result)

        layout.addStretch()

        self.btn_close = QPushButton(self.tr("Cerrar"))
        self.btn_close.setObjectName("PrimaryAction")
        self.btn_close.clicked.connect(self.accept)
        self.btn_close.setVisible(False)
        layout.addWidget(self.btn_close, alignment=Qt.AlignRight)

        return page

    def _start_move_worker(self):
        if not self._scan_result:
            return

        self._worker = _MoveWorker(
            self.project_root,
            self._scan_result["summary"],
            self._scan_result["unclassified"]
        )
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_move_progress)
        self._worker.finished.connect(self._on_move_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _on_move_progress(self, msg):
        self.lbl_execute_status.setText(msg)

    def _on_move_finished(self, success, result):
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        self.btn_close.setVisible(True)

        if not success:
            self.lbl_result.setText(self.tr("Error durante la reorganización: {0}").arg(result))
            self.lbl_result.setStyleSheet("color: {};".format(
                theme.color("danger")
            ))
            self.lbl_result.setVisible(True)
            return

        moved = result["moved"]
        unclassified = result["unclassified"]
        errors = result["errors"]

        parts = []
        if moved:
            parts.append(self.tr("{0} archivos reorganizados correctamente").arg(moved))
        if unclassified:
            parts.append(self.tr("{0} archivos permanecen en SinClasificar").arg(unclassified))
        if errors:
            parts.append(self.tr("{0} errores").arg(errors))
            if result.get("error_details"):
                parts.append(self.tr("Detalles: {0}").arg("; ".join(result["error_details"][:5])))

        self.lbl_result.setText(". ".join(parts) + ".")
        if errors:
            self.lbl_result.setStyleSheet("color: {};".format(
                theme.color("warning")
            ))
        else:
            self.lbl_result.setStyleSheet("color: {};".format(
                theme.color("success")
            ))
        self.lbl_result.setVisible(True)


# -----------------------------------------------------------------------------
# Métodos públicos para tests
# -----------------------------------------------------------------------------
    def _scan_folder(self, project_root):
        """Escanea SinClasificar/ y retorna resumen (para tests)."""
        worker = _ScanWorker(project_root)
        # Ejecutar síncronamente para tests
        success, result = True, None
        def capture(s, r):
            nonlocal success, result
            success, result = s, r
        worker.finished.connect(capture)
        worker.run()
        # Procesar events para que la señal se entregue
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()
        return result.get("summary", {}) if success and result else {}

    def _execute_move(self, project_root, summary):
        """Ejecuta movimiento (para tests)."""
        unclassified = self._scan_result.get("unclassified", []) if self._scan_result else []
        worker = _MoveWorker(project_root, summary, unclassified)
        success, result = True, None
        def capture(s, r):
            nonlocal success, result
            success, result = s, r
        worker.finished.connect(capture)
        worker.run()
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()
        return result if success else {}