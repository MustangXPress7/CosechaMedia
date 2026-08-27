# PLAN: UI tabla origenes - boton dedicado USB/MTP, deseleccion con ESC/click, Apagar al acabar bajo CSV y ultima tarea

## Descripción
Modificaciones en la tabla de orígenes y acciones post-ingesta:

1. **Botón dedicado USB/MTP** — En la columna de ruta de origen, para dispositivos USB/MTP, agregar un botón visible con el tipo de dispositivo que permita re-abrir el selector del dispositivo para elegir otra carpeta/ubicación.

2. **Deselección de filas** — Permitir deseleccionar filas de la tabla de orígenes pulsando ESC o haciendo click fuera de la tabla.

3. **Reordenar "Apagar al acabar"** — Mover la casilla "Apagar al acabar" debajo de "Generar CSV de integridad" y garantizar que se ejecute como última tarea post-ingesta.

## Archivos a modificar
- `app/ui/main_window.py` — Contiene la tabla de orígenes, los widgets de opciones, y la secuencia de acciones post-ingesta

## Tareas

### Tarea 1: Botón dedicado USB/MTP en la tabla de orígenes
- [ ] Modificar `_build_path_widget` (≈línea 2337) para detectar sesiones MCP/ MTP (device_id pero no wifi/ftp)
- [ ] Agregar un botón con texto "USB/MTP" style (como el botón FTP/QR existente) que reabra DevicePickerDialog
- [ ] Crear método `_reconfigure_mtp_source` similar a `_reconfigure_ftp_source` que permita cambiar la carpeta del dispositivo
- [ ] El botón debe mostrar el nombre del dispositivo como tooltip o texto

### Tarea 2: Permitir deselección de filas en tabla de orígenes
- [ ] Agregar manejo de evento `keyPressEvent` o usar `QShortcut` para capturar tecla ESC
- [ ] Cuando ESC se presione, limpiar selección de `source_list` y actualizar estado
- [ ] Alternativamente, instalar un event filter que detecte clicks fuera de la tabla

### Tarea 3: Reordenar y garantizar posición de "Apagar al acabar"
- [ ] Mover `chk_shutdown` para que aparezca DESPUÉS de `chk_generate_report` en el layout `post_terminar`
- [ ] Verificar que la secuencia de `_pending_actions` mantenga shutdown como última tarea
- [ ] Agregar asesoría defensiva: siempre mover "shutdown" al final de `_pending_actions` antes de ejecutar

## Verificación
- [ ] Verificar que la tabla de orígenes muestra el nuevo botón para dispositivos MTP
- [ ] Verificar que haciendo click en el botón se abre el selector de dispositivo nuevamente
- [ ] Verificar que ESC deselecciona filas de la tabla
- [ ] Verificar orden visual: "Generar CSV" → "Apagar al acabar"
- [ ] Verificar que shutdown se ejecuta después de todos los demás trabajos

## Archivos a leer
- `app/ui/main_window.py` líneas 2300-2450 (build_path_widget, options widget)
- `app/ui/main_window.py` líneas 600-640 (post-ingest actions)
- `app/ui/main_window.py` líneas 1920-1935 (_pending_actions setup)
- `app/ui/main_window.py` líneas 2546-2550 (_reconfigure_ftp_source como referencia)