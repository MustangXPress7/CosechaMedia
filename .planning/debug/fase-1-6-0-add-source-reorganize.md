---
slug: fase-1-6-0-add-source-reorganize
status: resolved
trigger: "debuguea la fase 1.6.0. La nueva ventana de añadir origenes funciona al 25%, y el reorganizador solo funciona con una carpeta con un nombre específico, el cual creo que en la práctica no es útil para algo que ya estará desordenado en sí."
created: "2026-09-03T22:45:00"
updated: "2026-09-03T23:30:00"
diagnose_only: false
tdd_mode: false
---

## Symptoms

### Expected behavior
- **AddSourceDialog**: Debe ser capaz de añadir orígenes, borrarlos, detectar su disponibilidad. Crear correctamente el acceso WiFi (no solo un cascarón vacío).
- **ReorganizeDialog**: Debe organizar lo que haya de archivos dentro que detecte dentro de sus parámetros, sin requerir una carpeta específica ("SinClasificar").

### Actual behavior
- **AddSourceDialog**: Funciona al ~25%. La UI se muestra pero muchas funcionalidades no funcionan: no añade orígenes correctamente, no borra, no detecta disponibilidad, WiFi es solo un cascarón vacío.
- **ReorganizeDialog**: Solo funciona si existe una carpeta llamada "SinClasificar". Si los archivos están desordenados en otras carpetas, no los detecta ni organiza.

### Error messages
- No se reportan errores explícitos, pero el comportamiento es incompleto/roto.

### Timeline
- Fase 1.6.0 recién implementada (planes 1, 2, 3 completados según SUMMARYs)
- Los bugs aparecen en la implementación actual

### Reproduction
1. Abrir AddSourceDialog (botón "+ Origen")
2. Intentar añadir origen WiFi - no crea acceso real
3. Intentar detectar dispositivos - funcionalidad limitada
4. Abrir ReorganizeDialog - requiere carpeta "SinClasificar" exactamente

---

## Current Focus

**hypothesis**: 
- AddSourceDialog: Falta conexión de callbacks (on_detect, on_delete) en main_window.py, botón QR sin handler, flujos WiFi/FTP incompletos (solo añaden filas placeholder).
- ReorganizeDialog: Hardcodeo de "SinClasificar" como carpeta fuente en _ScanWorker._scan() línea 74 y validaciones en _check_initial_sinclasificar/_on_browse.

**next_action**: gather initial evidence

**test**: 
- Verificar main_window.py integración AddSourceDialog (callbacks on_delete, on_detect)
- Verificar _ScanWorker hardcodeo "SinClasificar"
- Verificar botón QR en AddSourceDialog sin conexión

**expecting**: Identificar puntos exactos de fallo en ambos componentes

**reasoning_checkpoint**: null

**tdd_checkpoint**: null

---

## Evidence

- timestamp: "2026-09-03T22:45:00"
  description: "AddSourceDialog implementado (app/ui/add_source_dialog.py:500 líneas) pero botón QR (línea 261) sin handler onClick"
- timestamp: "2026-09-03T22:45:00"
  description: "AddSourceDialog _add_wifi_row (línea 389) y _add_ftp_row (línea 396) solo añaden filas placeholder sin lógica real de creación"
- timestamp: "2026-09-03T22:45:00"
  description: "ReorganizeDialog _ScanWorker._scan() línea 74 hardcodea 'SinClasificar' como única fuente"
- timestamp: "2026-09-03T22:45:00"
  description: "ReorganizeDialog _check_initial_sinclasificar (línea 282) y _on_browse (línea 304) validan existencia de 'SinClasificar'"
- timestamp: "2026-09-03T22:45:00"
  description: "main_window.py _pick_source_entry debe pasar on_delete y on_detect callbacks a AddSourceDialog"

---

## Eliminated

- QR button click handler missing — fixed by adding `on_qr` callback to AddSourceDialog and connecting it in main_window.py
- WiFi "Nuevo WiFi" button only added placeholder row — fixed by implementing real WiFi sender creation via input dialog and DB insert
- FTP "Nuevo FTP" button only added placeholder row — fixed by opening FtpPickerDialog for real profile creation
- ReorganizeDialog _ScanWorker hardcoded "SinClasificar" folder — fixed by scanning entire project root (excluding Footage/) for video files
- ReorganizeDialog validation required "SinClasificar" to exist — fixed by removing validation and enabling scan when any video files found in project root

---

## Resolution

**root_cause**: 
- AddSourceDialog: Three incomplete features — QR button had no click handler, "Nuevo WiFi" and "Nuevo FTP" buttons only added placeholder rows without real creation logic. The callbacks (on_delete, on_detect) were already correctly connected in main_window.py.
- ReorganizeDialog: The _ScanWorker._scan() method hardcoded "SinClasificar" as the only source folder, and the UI validation (_check_initial_sinclasificar, _on_browse) required this folder to exist before enabling the scan button. This made the reorganizer useless for already-disorganized footage.

**fix**: 
- AddSourceDialog: 
  1. Added `on_qr` callback parameter and connected QR button to it
  2. Implemented `_add_wifi_row` to prompt for sender name and create real inbox sender in DB
  3. Implemented `_add_ftp_row` to open FtpPickerDialog for real FTP profile creation
  4. Added `_show_wifi_qr_for_sender` method in main_window.py to open WiFi panel with QR for selected sender
- ReorganizeDialog:
  1. Rewrote `_ScanWorker._scan()` to walk entire project root, excluding Footage/ organized folder and hidden dirs
  2. Removed "SinClasificar" existence validation in `_check_initial_sinclasificar` and `_on_browse`
  3. Updated UI text to reflect scanning entire project, not just SinClasificar
  4. Updated result messages to use "sin clasificar (sin metadatos de cámara)" instead of "permanecen en SinClasificar"

**verification**: 
- All 325 existing tests pass (16 add_source_dialog tests, 10 reorganize_dialog tests, plus full suite)
- add_source_dialog tests verify: QR button only for WiFi, delete callback triggers, camera detection worker, MTP vs USB distinction, WPD error non-blocking
- reorganize_dialog tests verify: scan groups by camera/date, unclassified files tracked, move + MD5 + DB update, collision suffix handling, worker signals

**files_changed**: 
- app/ui/add_source_dialog.py (QR handler, WiFi/FTP creation logic, on_qr callback)
- app/ui/main_window.py (on_qr callback connection, _show_wifi_qr_for_sender method)
- app/ui/reorganize_dialog.py (ScanWorker full project scan, removed SinClasificar validation, updated UI text)