import os
import json
import tempfile
import unittest
import shutil

from app.core.db import DatabaseManager


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


if __name__ == "__main__":
    unittest.main()