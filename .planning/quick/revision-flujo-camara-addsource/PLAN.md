# PLAN.md - Revisión flujo selección/renombre cámara en AddSourceDialog

## Objetivo
Entender y documentar el flujo actual de selección/renombre de cámara en `AddSourceDialog` y por qué el usuario percibe confusión entre “renombrar dispositivo conocido” y “añadir nuevo nombre de cámara para la fila”.

## Contexto
- Diálogo: `app/ui/add_source_dialog.py`
- Llamador: `app/ui/mixins/sources_mixin.py::_pick_source_entry`
- Persistencia nombres: `app/ui/mixins/camera_mixin.py::_on_dialog_camera_name_changed`, `_detect_camera_for_source`
- BD: `app/core/db.py` `save_dispositivo_config`, `upsert_known_device`

Secciones del diálogo:
* Conexión física: `kind` `folder`, `device` MTP, `usb`
* WiFi: `kind` `sender`
* FTP: `kind` `ftp_profile`

## Hallazgos actuales

### Construcción combo
`app/ui/add_source_dialog.py:398-439` `_build_camera_combo`
- Combo editable, `insertPolicy NoInsert`.
- Nombres conocidos desde `db.list_known_camera_names()`.
- Ítems especiales: `— Vacío —` y `🔍 Detectar cámara automáticamente…`.
- `textChanged` → `_update_camera_in_row` + `_on_camera_text_changed`.
- `currentIndexChanged` → `_on_camera_combo_changed`.

### Persistencia inmediata
`app/ui/add_source_dialog.py:441-472` `_on_camera_text_changed`
- Solo para `kind == "device"` o `kind == "ftp_profile"`.
- Llama a `on_camera_name_changed(device_id, name)`.

`app/ui/mixins/camera_mixin.py:312-339` `_on_dialog_camera_name_changed`
- `db.save_dispositivo_config(device_id, sane)`
- `db.upsert_known_device(device_id, device_type, name=sane, last_camera=sane)`
- Actualiza **todas** las sesiones del proyecto con ese `device_id`: `db.update_session_config(s["id"], nombre_dispositivo=sane)`
- Refresca UI si visible.

### Detección
`app/ui/add_source_dialog.py:882-898` `_start_camera_detection`
- Worker `_CameraDetectWorker(self.on_detect, src)`.
- `app/ui/mixins/camera_mixin.py:230-265` `_detect_camera_for_source`
  - `folder` / `usb` → metadata del archivo más pequeño.
  - `device` MTP → `return ""` por diseño.
  - `sender` / `ftp_profile` → `return ""`.
- `_on_camera_detected` vuelve a llamar a `on_camera_name_changed` si `ok`.

### Resultado
`app/ui/add_source_dialog.py:992-1006` `result_sources`
- Devuelve `kind, value, camera` leyendo el widget de la celda.

## Problemas identificados
1. Persistencia carácter a carácter vía `textChanged` para dispositivos gestionados.
2. Renombre global inmediato: editar nombre en diálogo cambia sesiones existentes.
3. Detección MTP no funcional: botón presente pero devuelve vacío.
4. Asimetría por kind:
   - `folder`/`usb`: cambio no persiste vía `device_settings`.
   - `device`/`ftp_profile`: persiste inmediatamente.
5. Duplicidad de persistencia: `textChanged` + callback de detección.
6. Lista de nombres conocidos estática en la sesión; nuevos nombres no aparecen hasta próxima apertura.

## Tareas

### Tarea 1 - Mapeo de flujo
- Documentar secuencia: construcción combo → edición → `textChanged` → `_on_camera_text_changed` → `on_camera_name_changed` → BD y sesiones.
- Documentar secuencia detección: `currentIndexChanged` → `TRIGGER_DETECT` → worker → `_on_camera_detected`.

### Tarea 2 - Verificación por kind
- `folder`: edición no persiste, se devuelve en `result_sources`.
- `usb`: igual que folder, se mapea a `_assign_folder_source`.
- `device`: edición persiste inmediatamente y renombra sesiones.
- `ftp_profile`: mismo comportamiento que device.
- `sender`: widget fijo, no editable.

### Tarea 3 - Pruebas de reproducción
- Abrir diálogo con proyecto con sesiones existentes para mismo `device_id`.
- Editar nombre de cámara para `device` y comprobar cambios en BD y sesiones.
- Editar nombre para `folder`/`usb` y comprobar que no se escribe en BD.
- Probar detección en `folder`/`usb` con contenido de vídeo.
- Probar detección en `device` MTP y confirmar que no hace nada.

### Tarea 4 - Criterios de aceptación
- Documentación clara de qué kind persiste y cuándo.
- Lista de comportamientos inesperados confirmados con evidencia.
- Propuesta de separación entre “valor de fila” y “renombrar dispositivo conocido”.

## Archivos clave
- `app/ui/add_source_dialog.py`
- `app/ui/mixins/sources_mixin.py::_pick_source_entry`
- `app/ui/mixins/camera_mixin.py::_on_dialog_camera_name_changed`, `_detect_camera_for_source`, `_device_type_for_id`
- `app/core/db.py:save_dispositivo_config`, `upsert_known_device`, `update_session_config`

## Riesgos
- Cambios en persistencia pueden afectar sesiones existentes.
- Detección MTP requiere acceso a path cacheado, no disponible en el diálogo.

## Próximos pasos
- Ejecutar plan de verificación y registrar resultados en `VERIFICATION.md`.
- Proponer diseño de corrección con separación de responsabilidades.
