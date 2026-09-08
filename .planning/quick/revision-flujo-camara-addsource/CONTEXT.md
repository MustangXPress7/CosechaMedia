# Contexto del flujo de cámara en AddSourceDialog

## Entradas
- `folders`: rutas recientes y sesiones no gestionadas.
- `senders`: inbox_senders de BD.
- `devices_connected`: `mtp.WpdBackend().list_devices()`.
- `devices_missing`: dispositivos conocidos desconectados.

## Salidas
- `result_sources()`: lista de dicts `{kind, value, camera, enabled}`.

## Mapeo kind → comportamiento

| kind | type UI | Detección | Persistencia en edición |
|------|---------|-----------|--------------------------|
| folder | FOLDER | metadata vía path | No, solo fila |
| usb | USB | metadata vía path | No, solo fila → `_assign_folder_source` |
| device | MTP | No, devuelve "" | Sí, inmediato vía `on_camera_name_changed` |
| sender | WiFi | No | Widget fijo |
| ftp_profile | FTP | No | Sí, inmediato vía `on_camera_name_changed` |

## Callbacks del diálogo
- `on_delete(kind, value)`
- `on_detect(kind, value)` → `_detect_camera_for_source`
- `on_qr(sender_name)`
- `on_camera_name_changed(device_id, nombre)` → `_on_dialog_camera_name_changed`
- `on_wifi_status(sender_id)`

## Persistencia
- `device_settings` via `db.save_dispositivo_config`
- `known_devices` via `db.upsert_known_device`
- Sesiones vía `db.update_session_config` para cada sesión con mismo `device_id`.

## Observaciones
- `textChanged` se conecta para todos los combos editables, pero `_on_camera_text_changed` filtra por kind.
- Detección MTP está comentada como “se hace tras registro”.
- Refresco de UI ocurre si la ventana principal está visible.
