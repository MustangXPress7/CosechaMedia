---
slug: bugs-add-source-dialog
created: 2026-09-04
status: incomplete
commit: null
---

# Bugs y mejoras AddSourceDialog

## Resumen

Corregidos los 7 bugs reportados y aplicadas las 6 mejoras del diálogo
«Añadir origen» (plan `2026-09-04-bugs-add-source-dialog.md`).

## Cambios aplicados

- **BUG-1** (WiFi desaparece al abrir QR): eliminada la definición duplicada
  de `_show_wifi_qr_for_sender` que refrescaba destructivamente la tabla.
- **BUG-2/BUG-4** (borrar no actualiza): `_on_delete_clicked` elimina la fila
  visual y del dict interno vía `_remove_row`.
- **BUG-3** (Nuevo WiFi): eliminada la referencia muerta a
  `self.current_project_id`; se crea el remitente en DB y su fila funcional.
- **BUG-5** (falsos positivos MTP): `_windows_mounted_drives` filtra discos
  fijos simulando `DRIVE_REMOVABLE` con `_is_false_positive_drive`.
- **BUG-7** (cámara no persiste): el widget de cámara escribe en
  `_row_sources[row]["camera"]` en tiempo real.
- **CHG-1/CHG-2**: menú `&Herramientas` con «Borrar dispositivos guardados…»
  y «Borrar cámaras conocidas…»; nuevos métodos DB
  `delete_all_saved_devices` / `delete_all_known_cameras` y
  `metadata_engine.clear_cache`.
- **CHG-3**: checkboxes centrados (contenedor `Qt.AlignCenter`).
- **CHG-4**: filas de sección en celda combinada `setSpan` (col 0 + fondo).
- **CHG-5/CHG-6**: la celda de cámara es un `QComboBox` editable poblado con
  `db.list_known_camera_names()` + ítem disparador de detección off-thread.

## Archivos

- `app/ui/add_source_dialog.py`
- `app/ui/main_window.py`
- `app/core/utils.py`
- `app/core/db.py`
- `app/core/metadata_engine.py`
- `tests/test_add_source_dialog.py`
- `tests/test_main_window.py`

## Verificación

- `test_add_source_dialog.py`: tests nuevos (BUG-2/7, CHG-3/4/5) y
  actualizados al combo.
- `test_main_window.py`: `TestCleanupMenu` para CHG-1/CHG-2.
- Toda la suite: **342 tests OK** (4 skipped).

## Estado

Pendiente de commit. Verificación completa.
