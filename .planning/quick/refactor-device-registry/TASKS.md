# Tareas ejecutables

## Fase 1 - Esqueleto
1. Validar imports de device_registry → DONE
2. Crear documentación de API en device_registry.py docstring

## Fase 2 - Migración de consumidores
3. Cambiar import en app/ui/mixins/camera_mixin.py: from app.core.db import db → from app.core.device_registry import *
   Actualizar llamadas db.upsert_known_device, db.get_dispositivo_for_device, db.save_dispositivo_config → DONE
4. Cambiar import en app/ui/mixins/devices_mixin.py similar
5. Cambiar import en app/ui/add_source_dialog.py
6. Cambiar import en app/core/mtp.py
7. Cambiar import en app/core/ftp.py

## Fase 3 - Consolidación
8. Copiar implementación de métodos de db.py a device_registry.py
9. Modificar db.py para delegar a device_registry con warnings de deprecación
10. Añadir tests unitarios para device_registry

## Fase 4 - Verificación
11. Ejecutar pruebas manuales de añadir/quitar dispositivo
12. Ejecutar pruebas manuales de renombrar nombre de cámara
13. Revisar logs de error
