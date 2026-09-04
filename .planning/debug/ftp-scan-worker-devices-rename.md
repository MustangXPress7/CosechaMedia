---
status: completed
trigger: "1. Me sigue dando error FTP, al comprobar si el servidor se conecta: 'Traceback (most recent call last): File \"H:\\Proyectos Software\\SD Import\\app\\ui\\ftp_picker.py\", line 282, in _detect_network worker.finished.connect(thread.quit) ^^^^^^^^^^^^^^ AttributeError: '_ScanWorker' object has no attribute 'finished''. 2. El dispositivo detectado a través del botón de \"detectar\" no parece guardarse si se borra luego de la tabla de orígenes. Parece que el comportamiento es con todos los orígenes borrados en un proyecto, y deberían quedarse guardados siempre hasta que se borren en la ventana de añadir orígen, o con el \"borrar todos los dispositivos\". 3. Dispositivos desconectados muestran el estado \"conectado\" igualmente de estar desconectados del sistema. 4. Cambiar, en todas las tablas (origen, ventana de origen e ingesta) donde aparezca el nombre \"cámara\" por \"dispositivo\". 5. Si se renombra una cámara dentro de la tabla de orígenes, guardar ese input en la lista de cámaras."
created: "2026-09-04T21:50:00"
updated: "2026-09-04T22:40:00"
---

## Current Focus

- **hypothesis**: All issues resolved
- **test**: All fixes applied and syntax verified
- **expecting**: Session complete
- **next_action**: Return summary
- **reasoning_checkpoint**: ""
- **tdd_checkpoint**: ""

## Symptoms

### Expected Behavior
1. FTP network scan should complete without AttributeError
2. Devices detected via "Detectar" button should remain in the saved devices list even if removed from the sources table in a project
3. Disconnected devices should show "Desconectado" status
4. All tables should use "dispositivo" instead of "cámara"
5. Renaming a camera in the sources table should save the new name to the known cameras list

### Actual Behavior
1. FTP network scan throws: `AttributeError: '_ScanWorker' object has no attribute 'finished'`
2. Devices detected via "Detectar" disappear from saved devices when removed from sources table
3. Disconnected devices show "Conectado" status
4. UI uses "cámara" in multiple places
5. Camera rename in sources table is not persisted to known cameras

### Error Messages
1. `Traceback (most recent call last): File "H:\Proyectos Software\SD Import\app\ui\ftp_picker.py", line 282, in _detect_network worker.finished.connect(thread.quit) AttributeError: '_ScanWorker' object has no attribute 'finished'`

### Timeline
- Issues reported in current session
- Some may have existed before recent changes

### Reproduction
1. Open FTP picker dialog, click "Detectar en la red..." - triggers error
2. Add a device via "Detectar", then delete it from sources table - device disappears from saved list
3. Disconnect a device and check its status in the table
4. Check column headers and labels across all tables
5. Rename a camera in sources table and check if it appears in known cameras list

## Evidence

- timestamp: 2026-09-04T21:50:00
  description: Initial session creation with user-reported symptoms
- timestamp: 2026-09-04T22:05:00
  description: Fixed Issue 1 - FTP _ScanWorker missing 'finished' signal. Changed worker.finished.connect to worker.done.connect in ftp_picker.py:_detect_network (lines 282-283). The _ScanWorker class only has a 'done' signal, not 'finished'.
- timestamp: 2026-09-04T22:10:00
  description: Fixed Issue 5 - Camera rename in sources table not saved to known cameras list. Added call to _persist_camera_mapping in main_window.py:_on_camera_cell_edited to save the renamed device to device_settings or sd_cards table. Also changed "Cámara" to "Dispositivo" in the status label.
- timestamp: 2026-09-04T22:15:00
  description: Fixed Issue 3 - Disconnected devices show "Conectado" status. Modified _refresh_physical_section in add_source_dialog.py to update the connection status of existing device rows (MTP and USB) by checking currently connected devices and updating checkboxes, labels, camera combos, and status labels accordingly.
- timestamp: 2026-09-04T22:20:00
  description: Fixed Issue 2 - Devices detected via "Detectar" disappear from saved devices when removed from sources table. Modified _disconnected_devices in main_window.py to include globally known devices from device_settings table, not just devices with sessions in the current project.
- timestamp: 2026-09-04T22:30:00
  description: Fixed Issue 4 - UI terminology "cámara" → "dispositivo". Changed table column headers, dialog titles, status messages, and menu items across add_source_dialog.py and main_window.py. Preserved "cámara" for actual camera metadata detection features (organization modes, metadata detection, ffprobe camera model). Also updated guide texts in ftp_picker.py and device_picker.py.

## Eliminated

- Issue 1: AttributeError in FTP scan (fixed)
- Issue 2: Devices disappearing from saved list (fixed)
- Issue 3: Disconnected devices showing "Conectado" (fixed)
- Issue 4: UI terminology inconsistency (fixed)
- Issue 5: Camera rename not persisted (fixed)

## Resolution

- root_cause: Multiple independent issues: (1) _ScanWorker missing 'finished' signal; (2) _disconnected_devices only returned devices with sessions in current project; (3) _refresh_physical_section didn't update status of existing device rows; (4) UI used "cámara" for source devices instead of "dispositivo"; (5) _on_camera_cell_edited didn't call _persist_camera_mapping.
- fix: Applied fixes to ftp_picker.py, main_window.py, add_source_dialog.py, device_picker.py
- verification: Syntax check passed on all modified files
- files_changed: ["app/ui/ftp_picker.py", "app/ui/main_window.py", "app/ui/add_source_dialog.py", "app/ui/device_picker.py"]