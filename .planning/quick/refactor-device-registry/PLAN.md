# Plan de Refactor: Separar gestión de dispositivos de db.py

## Objetivo
Isolar la gestión de dispositivos y nombres de cámara de `DatabaseManager` para reducir bugs al añadir/quitar dispositivos y al gestionar nombres.

## Contexto
- `db.py` contiene ~1.600 líneas y mezcla proyectos/sesiones/ingesta con dispositivos.
- Bugs recurrentes en añadir/quitar dispositivos y renombrar nombres de cámara.
- Métodos de dispositivo:
  upsert_known_device, get_known_device, list_known_devices, delete_known_device, delete_known_devices_by_type, sync_device_settings_to_known, list_known_camera_names, delete_all_known_cameras, delete_all_saved_devices, save_dispositivo, get_dispositivo_for_card, get_dispositivo_for_device, save_dispositivo_config, get_device_delicate, set_device_delicate, _sanitize_dispositivo_nombre.

## Alcance
- Crear capa `device_registry` que centralice la gestión de dispositivos.
- Migrar consumidores clave a usar `device_registry`.
- Mantener compatibilidad con `db.py` vía delegación.

## Tareas
### Fase 1 - Esqueleto
- [x] Crear `app/core/device_registry.py` como fachada proxy a `db`.
- [ ] Documentar API pública del registry.

### Fase 2 - Migración de consumidores
- [ ] Actualizar `app/ui/mixins/camera_mixin.py` para importar de `device_registry`.
- [ ] Actualizar `app/ui/mixins/devices_mixin.py` para importar de `device_registry`.
- [ ] Actualizar `app/ui/add_source_dialog.py` para importar de `device_registry`.
- [ ] Actualizar `app/core/mtp.py` y `app/core/ftp.py` para importar de `device_registry`.

### Fase 3 - Consolidación
- [ ] Mover implementación real de métodos de dispositivo de `db.py` a `device_registry.py`.
- [ ] Dejar en `db.py` wrappers con deprecación.
- [ ] Añadir tests de integración para añadir/quitar dispositivo y renombrar.

### Fase 4 - Verificación
- [ ] Reproducir casos de bug: añadir dispositivo MTP, cambiar nombre, quitar dispositivo.
- [ ] Validar que `known_devices`, `device_settings` y sesiones se actualizan coherentemente.
- [ ] No regressions en UI de dispositivos.

## Criterios de aceptación
- Todos los usos de `db.upsert_known_device`, `db.get_dispositivo_for_device`, `db.save_dispositivo_config` pasan por `device_registry`.
- Añadir/quitar dispositivo funciona sin inconsistencias.
- Renombrar nombre de dispositivo actualiza `known_devices`, `device_settings` y sesiones.
- `db.py` mantiene API retrocompatible.

## Riesgos
- Cambio transversal en imports.
- Posibles referencias ocultas a métodos de dispositivo en tests.

## Próximo paso
Crear artefactos GSD de contexto y criterios.
