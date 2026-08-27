# Summary: UI tabla origenes

## Descripción
Implementación de tres cambios en la UI:

1. **Botón dedicado USB/MTP** — Agregado botón en columna de ruta para dispositivos MTP/USB que permite reseleccionar la carpeta del dispositivo.
2. **Deselección con ESC/click** — Implementado event filter que permite deseleccionar filas pulsando ESC o haciendo click fuera de la tabla.
3. **Reordenar "Apagar al acabar"** — Mover checkbox debajo de "Generar CSV de integridad" y garantizar posición final en la secuencia de tareas.

## Cambios realizados

### app/ui/main_window.py

1. **Línea ~2400-2405** (`_build_path_widget`):
   - Agregada detección de dispositivos MTP: `is_mtp = bool(session) and device_id and not is_wifi and not is_ftp`
   - Modificado para pasar `is_mtp` al método `_build_remote_source_button`

2. **Línea ~2525-2545** (`_build_remote_source_button`):
   - Modificado para aceptar parámetro `is_mtp`
   - Agregado botón "USB/MTP" con tooltip "Cambiar carpeta del dispositivo..."

3. **Línea ~2610-2627** (`_reconfigure_mtp_source`):
   - Nuevo método que abre `DevicePickerDialog` para reconfigurar origen MTP
   - Registra nuevo dispositivo si el usuario confirma el cambio

4. **Línea ~2850-2870** (nuevo):
   - Agregado método `_clear_source_list_selection()` 
   - Agregado método `_source_list_event_filter()` para handler del filtro
   - Agregado método `eventFilter()` para integración con Qt

5. **Línea ~469** (`__init__`):
   - Agregado `self.source_list.installEventFilter(self)` para capturar eventos

6. **Líneas ~607-614** (post-ingest actions):
   - Reordenado: `chk_generate_report` → `chk_shutdown`

## Tests
- Todos los tests pasan: `python -m unittest discover -s tests` (298 tests OK)
- Tests específicos de `test_source_content.py` pasan (15 tests)

## Verificación pendiente
- [ ] Verificar que el botón USB/MTP aparece correctamente
- [ ] Verificar que ESC deselecciona filas
- [ ] Verificar click-away deselecciona filas
- [ ] Verificar orden visual de checkboxes