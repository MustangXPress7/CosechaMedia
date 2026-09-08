# Contexto de refactor de device registry

## Problema
db.py gestiona proyectos, sesiones, ingesta y dispositivos mezclados. Bugs recurrentes al añadir/quitar dispositivos y al renombrar nombres de cámara.

## Estado actual
- `app/core/db.py` contiene DatabaseManager con métodos de dispositivo:
  upsert_known_device, get_known_device, list_known_devices, delete_known_device, delete_known_devices_by_type, sync_device_settings_to_known, list_known_camera_names, delete_all_known_cameras, delete_all_saved_devices, save_dispositivo, get_dispositivo_for_card, get_dispositivo_for_device, save_dispositivo_config, get_device_delicate, set_device_delicate, _sanitize_dispositivo_nombre
- `app/core/device_registry.py` creado como fachada proxy a db.
- Consumidores principales:
  app/ui/mixins/camera_mixin.py
  app/ui/mixins/devices_mixin.py
  app/ui/add_source_dialog.py
  app/core/mtp.py
  app/core/ftp.py

## Dependencias
- PySide6, SQLite, app.core.db
- No cambios de esquema de base de datos en esta fase.

## Suposiciones
- db.py seguirá siendo fuente de verdad hasta Fase 3.
- API de dispositivo no cambia de firma.
