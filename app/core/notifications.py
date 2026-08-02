import os
import sys
import shutil
import threading
import platform
from typing import Dict, Optional
from PySide6.QtWidgets import QMessageBox, QApplication, QDialog
from app.ui import theme
from app.core.utils import resource_path

class _SilentMessageBox(QMessageBox):
    """QMessageBox que no reproduce el sonido de sistema al mostrarse.

    En Windows, QMessageBox::showEvent llama a playMessageBoxSound() según el
    icono (ej. Information -> sonido de notificacion del sistema), que suena a
    la vez que el wav custom de la app. Aqui se evita llamando directamente a
    QDialog.showEvent.
    """

    def showEvent(self, event):
        QDialog.showEvent(self, event)

def play_sound_file(sound_file: str):
    def _play():
        try:
            if platform.system() == "Windows":
                import winsound
                winsound.PlaySound(sound_file, winsound.SND_FILENAME | winsound.SND_ASYNC)
            elif platform.system() == "Darwin":
                os.system(f'afplay "{sound_file}" &')
            else:
                os.system(f'aplay "{sound_file}" &')
        except Exception as e:
            print(f"Error playing sound: {e}")
    t = threading.Thread(target=_play, name="sound-player", daemon=True)
    t.start()

class NotificationManager:
    def __init__(self):
        self.sounds_enabled = True
        self.visual_enabled = True
        if getattr(sys, "frozen", False):
            self._sound_dir = os.path.join(os.path.dirname(sys.executable), "sounds")
        else:
            self._sound_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sounds"
            )
        os.makedirs(self._sound_dir, exist_ok=True)
        self._bundled_sound_dir = resource_path(os.path.join("app", "sounds"))
    
    def notify_ingest_complete(self, stats: Dict):
        if self.sounds_enabled:
            self._ensure_and_play("complete.wav", 800, 0.5)

        if self.visual_enabled:
            self._show_complete_dialog(stats)

    def notify_ingest_stopped(self):
        if self.sounds_enabled:
            self._ensure_and_play("stop.wav", 440, 0.35)

    def notify_ingest_failed(self, stats: Dict = None):
        if self.sounds_enabled:
            self._ensure_and_play("error.wav", 220, 0.6)

        if self.visual_enabled:
            self._show_failed_dialog(stats or {})
    
    def _show_complete_dialog(self, stats: Dict):
        app = QApplication.instance()
        if app is None:
            return
        
        msg = _SilentMessageBox()
        msg.setWindowTitle("Ingesta Completada")
        msg.setIcon(QMessageBox.Information)
        
        processed = stats.get("processed", 0)
        errors = stats.get("errors", 0)
        skipped = stats.get("skipped", 0)
        duration = stats.get("duration", 0)
        
        minutes = int(duration // 60)
        seconds = int(duration % 60)

        success = theme.color("success")
        danger = theme.color("danger")

        text = f"""
        <h2 style='color: {success};'>✓ Ingesta completada</h2>
        <p><b>Archivos procesados:</b> {processed}</p>
        <p><b>Errores:</b> {errors}</p>
        <p><b>Omitidos:</b> {skipped}</p>
        <p><b>Tiempo total:</b> {minutes}m {seconds}s</p>
        """
        
        if errors > 0:
            text += f"<p style='color: {danger};'>Algunos archivos tuvieron errores. Revisa la tabla para más detalles.</p>"
        
        msg.setText(text)
        msg.exec()

    def _show_failed_dialog(self, stats: Dict):
        app = QApplication.instance()
        if app is None:
            return

        msg = _SilentMessageBox()
        msg.setWindowTitle("Ingesta con errores")
        msg.setIcon(QMessageBox.Warning)

        processed = stats.get("processed", 0)
        errors = stats.get("errors", 0)
        skipped = stats.get("skipped", 0)

        danger = theme.color("danger")

        text = f"""
        <h2 style='color: {danger};'>✗ Ingesta no completada</h2>
        <p><b>Archivos procesados:</b> {processed}</p>
        <p><b>Errores:</b> {errors}</p>
        <p><b>Omitidos:</b> {skipped}</p>
        <p style='color: {danger};'>Hubo errores durante el volcado. Revisa la tabla para más detalles.</p>
        """

        msg.setText(text)
        msg.exec()

    def _ensure_and_play(self, filename: str, frequency: int, duration: float):
        sound_file = os.path.join(self._sound_dir, filename)
        bundled = os.path.join(self._bundled_sound_dir, filename)
        if not os.path.exists(sound_file) and os.path.exists(bundled):
            try:
                shutil.copyfile(bundled, sound_file)
            except Exception:
                pass
        if not os.path.exists(sound_file):
            self._create_sound_file(sound_file, frequency, duration)
        if os.path.exists(sound_file):
            play_sound_file(sound_file)

    def _create_sound_file(self, path: str, frequency: int, duration: float):
        try:
            import wave
            import struct

            sample_rate = 44100
            num_samples = int(sample_rate * duration)

            with wave.open(path, 'w') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)

                for i in range(num_samples):
                    t = float(i) / sample_rate
                    value = int(32767.0 * 0.5 * (1 if (t * frequency * 2) % 1 < 0.5 else -1))
                    data = struct.pack('<h', value)
                    wav_file.writeframes(data)
        except Exception as e:
            print(f"Error creating sound: {e}")
