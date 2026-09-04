---
slug: bugs-add-source-dialog
created: 2026-09-04
area: ui
title: Bugs y mejoras AddSourceDialog
---

# Bugs y mejoras AddSourceDialog

Corrige los 7 bugs reportados y aplica las 6 mejoras CHG del diálogo «Añadir
origen» (plan `2026-09-04-bugs-add-source-dialog.md`).

## Ámbito

- `app/ui/add_source_dialog.py`
- `app/ui/main_window.py`
- `app/core/utils.py`
- `app/core/db.py`
- `app/core/metadata_engine.py`
- `tests/test_add_source_dialog.py`
- `tests/test_main_window.py`

## Tareas

### BUG-1: WiFi desaparece al abrir QR
- Eliminada la definición duplicada de `_show_wifi_qr_for_sender` (la de la
  línea ~2814, con `_sync_wifi_sessions()`, hacía sombra a la versión fija
  D-07 y refrescaba la tabla destructivamente).

### BUG-2/BUG-4: borrar no actualiza la tabla en tiempo real
- `_on_delete_clicked` llama a `on_delete` y, si devuelve True (o no hay
  callback), elimina la fila visual y del dict `_row_sources` vía `_remove_row`.

### BUG-3: "Nuevo WiFi" no crea remitente real
- `_add_wifi_row` ya preguntaba el nombre e insertaba en DB; se eliminó la
  referencia muerta a `self.current_project_id`.

### BUG-5: falsos positivos MTP desde discos fijos
- `_windows_mounted_drives` filtra falsos positivos `DRIVE_REMOVABLE`
  (SSD/NVMe de sistema) según etiqueta y carpetas de sistema vía
  `_is_false_positive_drive`.

### BUG-7: nombre de cámara no persiste
- El `QLineEdit`/`QComboBox` de cámara escribe en `_row_sources[row]["camera"]`
  en tiempo real (`_update_camera_in_row`).

### CHG-1/CHG-2: menú Herramientas de limpieza
- Nuevo menú `&Herramientas` con «Borrar dispositivos guardados…» y «Borrar
  cámaras conocidas…». Métodos `_delete_all_saved_devices` /
  `_delete_all_known_cameras` + `db.delete_all_saved_devices` /
  `db.delete_all_known_cameras` + `metadata_engine.clear_cache`.

### CHG-3: checkboxes centrados
- El checkbox de la columna 0 va envuelto en un contenedor con
  `setAlignment(Qt.AlignCenter)`.

### CHG-4: filas de sección en celda combinada
- `_add_section` usa `setSpan(row, 0, 1, columnCount)` y coloca el rótulo en
  la columna 0 con fondo `bg_elevated`.

### CHG-5/CHG-6: combo de cámara con nombres conocidos + escáner
- La celda Cámara es un `QComboBox` editable, poblado con
  `db.list_known_camera_names()`, con un ítem disparador
  «Detectar cámara automáticamente…» que lanza la detección off-thread.

## Verificación

- `tests/test_add_source_dialog.py`: tests nuevos para BUG-1/2/3/4/5/7,
  CHG-3, CHG-4, CHG-5.
- `tests/test_main_window.py`: `TestCleanupMenu` para CHG-1/CHG-2.
- Toda la suite: 342 tests OK.
