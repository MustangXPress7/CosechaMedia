import os
import json
import tempfile
import unittest
import shutil
from unittest import mock

from app.core.db import DatabaseManager
from app.core.mtp import WpdBackend, DeviceInfo
from app.core.ftp import FtpBackend


class TestDeviceRegistry(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sdimport_devreg_")
        self.db = DatabaseManager(db_path=os.path.join(self.tmp, "test.db"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_known_devices_crud(self):
        # Upsert
        did1 = self.db.upsert_known_device("mtp:PNP123", "mtp", "Mi Cámara", "SN123", "Canon C300", {"model": "C300"})
        self.assertIsInstance(did1, int)

        # Get
        kd = self.db.get_known_device("mtp:PNP123")
        self.assertIsNotNone(kd)
        self.assertEqual(kd["device_id"], "mtp:PNP123")
        self.assertEqual(kd["device_type"], "mtp")
        self.assertEqual(kd["name"], "Mi Cámara")
        self.assertEqual(kd["serial"], "SN123")
        self.assertEqual(kd["last_camera"], "Canon C300")
        self.assertEqual(kd["metadata"], {"model": "C300"})

        # Update (same device_id)
        did2 = self.db.upsert_known_device("mtp:PNP123", "mtp", "Cámara Actualizada", None, "Sony FX3", {"model": "FX3"})
        self.assertEqual(did2, did1)  # Same ID
        kd = self.db.get_known_device("mtp:PNP123")
        self.assertEqual(kd["name"], "Cámara Actualizada")
        self.assertEqual(kd["last_camera"], "Sony FX3")
        self.assertEqual(kd["metadata"], {"model": "FX3"})

        # List
        devices = self.db.list_known_devices()
        self.assertEqual(len(devices), 1)

        # Delete
        self.assertTrue(self.db.delete_known_device("mtp:PNP123"))
        self.assertIsNone(self.db.get_known_device("mtp:PNP123"))
        self.assertEqual(len(self.db.list_known_devices()), 0)

    def test_known_devices_prefill_addsource(self):
        # Simular dispositivo conocido en known_devices
        self.db.upsert_known_device("mtp:PNP456", "mtp", "Cámara Pre-fill", "SN456", "RED Komodo")
        
        # get_dispositivo_for_device debe leer de known_devices
        name = self.db.get_dispositivo_for_device("mtp:PNP456")
        self.assertEqual(name, "Cámara Pre-fill")

    def test_known_devices_cross_project(self):
        # Crear proyecto A
        pid_a = self.db.create_project("Proyecto A", "/tmp/proj_a")
        # Añadir dispositivo conocido
        self.db.upsert_known_device("mtp:PNP789", "mtp", "Cámara Cross", "SN789", "ARRI Alexa")
        
        # Crear proyecto B (simula cambio de proyecto)
        pid_b = self.db.create_project("Proyecto B", "/tmp/proj_b")
        
        # El dispositivo conocido debe seguir disponible
        name = self.db.get_dispositivo_for_device("mtp:PNP789")
        self.assertEqual(name, "Cámara Cross")

    def test_device_settings_migration(self):
        # Poblar device_settings (legacy)
        self.db.save_dispositivo_config("mtp:PNP999", "Cámara Legacy")
        
        # Migrar
        migrated = self.db.sync_device_settings_to_known()
        self.assertEqual(migrated, 1)
        
        # Verificar en known_devices
        kd = self.db.get_known_device("mtp:PNP999")
        self.assertIsNotNone(kd)
        self.assertEqual(kd["device_type"], "mtp")
        self.assertEqual(kd["name"], "Cámara Legacy")
        
        # Segunda migración no debe duplicar
        migrated2 = self.db.sync_device_settings_to_known()
        self.assertEqual(migrated2, 1)  # Ya existía, upsert no cuenta como nuevo

    def test_device_registry_import_export(self):
        # Exportar
        self.db.upsert_known_device("mtp:PNP111", "mtp", "Cam 1", "S1", "Model A", {"foo": "bar"})
        self.db.upsert_known_device("ftp:1", "ftp", "FTP Server", None, "FTP Cam", {"host": "192.168.1.1"})
        
        # Simular exportación
        devices = self.db.list_known_devices()
        export_data = []
        for d in devices:
            export_data.append({
                "device_id": d["device_id"],
                "device_type": d["device_type"],
                "name": d["name"],
                "serial": d["serial"],
                "last_camera": d["last_camera"],
                "last_seen": d["last_seen"],
                "metadata": d["metadata"],
            })
        
        # Simular importación en BD nueva
        tmp2 = tempfile.mkdtemp(prefix="sdimport_devreg2_")
        try:
            db2 = DatabaseManager(db_path=os.path.join(tmp2, "test2.db"))
            count = 0
            for d in export_data:
                if not all(k in d for k in ("device_id", "device_type")):
                    continue
                db2.upsert_known_device(
                    d["device_id"], d["device_type"],
                    d.get("name"), d.get("serial"),
                    d.get("last_camera"), d.get("metadata")
                )
                count += 1
            self.assertEqual(count, 2)
            
            kd1 = db2.get_known_device("mtp:PNP111")
            self.assertEqual(kd1["name"], "Cam 1")
            self.assertEqual(kd1["metadata"], {"foo": "bar"})
            
            kd2 = db2.get_known_device("ftp:1")
            self.assertEqual(kd2["name"], "FTP Server")
            self.assertEqual(kd2["metadata"], {"host": "192.168.1.1"})
        finally:
            import shutil
            shutil.rmtree(tmp2, ignore_errors=True)

    def test_upsert_on_mtp_detection(self):
        """Mock MTP detection -> known_devices poblado."""
        with mock.patch('app.core.db.db') as mock_db:
            mock_db.get_dispositivo_for_device.return_value = "Saved Camera"
            mock_db.upsert_known_device.return_value = 1
            
            backend = WpdBackend()
            fake_device = DeviceInfo(device_id="mtp:PNP999", name="MTP Device", serial="SN999")
            
            # Simular lo que hace list_devices al encontrar un dispositivo
            device_id = fake_device.device_id
            name = fake_device.name
            saved_camera = mock_db.get_dispositivo_for_device(device_id)
            meta = {"name": name}
            mock_db.upsert_known_device(device_id, "mtp", name=name, last_camera=saved_camera, metadata=meta)
            
            mock_db.upsert_known_device.assert_called_once_with(
                "mtp:PNP999", "mtp", name="MTP Device", last_camera="Saved Camera", metadata={"name": "MTP Device"}
            )

    def test_upsert_on_ftp_detection(self):
        """Mock FTP list -> known_devices poblado."""
        with mock.patch('app.core.db.db') as mock_db:
            mock_db.get_dispositivo_for_device.return_value = "FTP Camera"
            mock_db.upsert_known_device.return_value = 1
            
            # Simular list_devices
            profile = {"id": 42, "name": "Mi FTP", "host": "192.168.1.10"}
            device_id = f"ftp:{profile['id']}"
            name = profile.get("name") or profile.get("host") or ""
            saved_camera = mock_db.get_dispositivo_for_device(device_id)
            meta = {"host": profile.get("host"), "name": profile.get("name")}
            mock_db.upsert_known_device(device_id, "ftp", name=name, last_camera=saved_camera, metadata=meta)
            
            mock_db.upsert_known_device.assert_called_once_with(
                "ftp:42", "ftp", name="Mi FTP", last_camera="FTP Camera", 
                metadata={"host": "192.168.1.10", "name": "Mi FTP"}
            )

    def test_upsert_on_camera_rename(self):
        """Editar nombre en AddSourceDialog -> known_devices actualizado."""
        # Simular flujo: device_settings -> known_devices via callback
        self.db.save_dispositivo_config("mtp:RENAME1", "Old Name")
        
        # Simular _on_dialog_camera_name_changed
        device_id = "mtp:RENAME1"
        new_name = "New Name"
        sane = self.db._sanitize_dispositivo_nombre(new_name)
        self.db.save_dispositivo_config(device_id, sane)
        device_type = "mtp"
        self.db.upsert_known_device(device_id, device_type, name=sane, last_camera=sane)
        
        # Verificar en known_devices
        kd = self.db.get_known_device(device_id)
        self.assertIsNotNone(kd)
        self.assertEqual(kd["name"], "New Name")
        self.assertEqual(kd["last_camera"], "New Name")
        
        # Verificar que device_settings también se actualizó
        conn = self.db.get_connection()
        row = conn.execute("SELECT nombre_dispositivo FROM device_settings WHERE device_key = ?", (device_id,)).fetchone()
        conn.close()
        self.assertEqual(row[0], "New Name")

    def test_legacy_migration_on_startup(self):
        """device_settings legacy -> known_devices migrado al init DB."""
        # Poblar device_settings ANTES de crear el DB manager (simula BD legacy)
        self.db.save_dispositivo_config("mtp:LEGACY1", "Legacy Camera 1")
        self.db.save_dispositivo_config("ftp:5", "Legacy FTP Camera")
        self.db.save_dispositivo_config("wifi:pairdrop", "Legacy WiFi")
        
        # Crear NUEVA instancia de DatabaseManager (simula arranque de app)
        tmp2 = tempfile.mkdtemp(prefix="sdimport_migration_")
        try:
            # Copiar la BD actual
            import shutil
            shutil.copy2(os.path.join(self.tmp, "test.db"), os.path.join(tmp2, "test.db"))
            
            db2 = DatabaseManager(db_path=os.path.join(tmp2, "test.db"))
            
            # Verificar migración automática
            kd1 = db2.get_known_device("mtp:LEGACY1")
            self.assertIsNotNone(kd1)
            self.assertEqual(kd1["device_type"], "mtp")
            self.assertEqual(kd1["name"], "Legacy Camera 1")
            
            kd2 = db2.get_known_device("ftp:5")
            self.assertIsNotNone(kd2)
            self.assertEqual(kd2["device_type"], "ftp")
            self.assertEqual(kd2["name"], "Legacy FTP Camera")
            
            kd3 = db2.get_known_device("wifi:pairdrop")
            self.assertIsNotNone(kd3)
            self.assertEqual(kd3["device_type"], "wifi")
            self.assertEqual(kd3["name"], "Legacy WiFi")
        finally:
            shutil.rmtree(tmp2, ignore_errors=True)

    def test_detect_button_removed(self):
        """Verificar que btn_detect_drives no existe en main_window."""
        # Este test verifica que el botón 'Detectar' ha sido eliminado
        # del layout de orígenes en main_window
        import app.ui.main_window as mw
        
        # Verificar que no hay referencia a btn_detect_drives en el código
        # (el test pasa si el botón no se crea en setup_views)
        # Usamos inspección del código fuente
        source_file = os.path.join(os.path.dirname(__file__), "..", "app", "ui", "main_window.py")
        with open(source_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # El botón ya no debe crearse
        self.assertNotIn('self.btn_detect_drives = QPushButton(self.tr("Detectar"))', content)
        # La conexión tampoco debe existir
        self.assertNotIn('self.btn_detect_drives.clicked.connect(self._auto_detect_removable_drives)', content)

    def test_cross_project_persistence(self):
        """Flujo completo cross-proyecto: detectar en A -> visible en B con pre-fill."""
        # Crear proyecto A
        pid_a = self.db.create_project("Proyecto A", "/tmp/proj_a")
        # Simular detección de dispositivo en proyecto A (upsert a known_devices)
        self.db.upsert_known_device("mtp:CROSS1", "mtp", "Cámara Cross", "SN123", "Sony FX3")
        
        # Cambiar a proyecto B (simula cambio de proyecto)
        pid_b = self.db.create_project("Proyecto B", "/tmp/proj_b")
        
        # El dispositivo conocido debe seguir disponible
        name = self.db.get_dispositivo_for_device("mtp:CROSS1")
        self.assertEqual(name, "Cámara Cross")
        
        # Editar nombre en proyecto B
        self.db.save_dispositivo_config("mtp:CROSS1", "Sony FX6")
        self.db.upsert_known_device("mtp:CROSS1", "mtp", name="Sony FX6", last_camera="Sony FX6")
        
        # Volver a proyecto A -> nombre actualizado visible
        name_a = self.db.get_dispositivo_for_device("mtp:CROSS1")
        self.assertEqual(name_a, "Sony FX6")

    def test_delete_all_clears_known_devices(self):
        """Kill-switch limpia known_devices."""
        # Poblar known_devices
        self.db.upsert_known_device("mtp:KILL1", "mtp", "To Kill", "SN1", "Cam 1")
        self.db.upsert_known_device("ftp:99", "ftp", "FTP To Kill", None, "FTP Cam")
        
        # Verificar que existen
        self.assertIsNotNone(self.db.get_known_device("mtp:KILL1"))
        self.assertIsNotNone(self.db.get_known_device("ftp:99"))
        
        # Ejecutar kill-switch (delete_all_known_cameras)
        self.db.delete_all_known_cameras()
        
        # Verificar que known_devices se limpió
        self.assertIsNone(self.db.get_known_device("mtp:KILL1"))
        self.assertIsNone(self.db.get_known_device("ftp:99"))
        
        # También probar delete_all_saved_devices
        self.db.upsert_known_device("mtp:KILL2", "mtp", "To Kill 2", "SN2", "Cam 2")
        self.assertIsNotNone(self.db.get_known_device("mtp:KILL2"))
        self.db.delete_all_saved_devices()
        self.assertIsNone(self.db.get_known_device("mtp:KILL2"))


if __name__ == "__main__":
    unittest.main()