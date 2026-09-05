---
created: 2026-09-04T23:00:00Z
title: Bugs y mejoras AddSourceDialog - para corrección mañana
area: ui
severity: major
files:
  - app/ui/add_source_dialog.py
  - app/ui/main_window.py
  - app/ui/wifi_panel.py
  - app/core/db.py
---

## Bugs reportados (7)

### BUG-1: WiFi desaparece al abrir QR (de 2026-09-02)
- Al abrir el código QR de un origen WiFi una vez, el origen desaparece de la tabla de orígenes
- Fix D-07: el QR debe abrirse en panel/acción aparte sin provocar `_refresh_source_list()` destructivo
- El origen debe permanecer en la lista tras abrir/cerrar QR

### BUG-2: Deseleccionar más agresivo que la papelera (de 2026-09-02)
- Deseleccionar un origen (checkbox off) en la tabla de orígenes principales borra el origen
- Comportamiento correcto (D-10): checkbox = inhabilitar (enabled=0), papelera = borrar del proyecto
- Deseleccionar NO debe borrar, solo poner `enabled=0` en la sesión

### BUG-3: Botón "Nuevo WiFi" no crea dispositivo real
- Al pulsar "Nuevo WiFi" solo añade fila placeholder
- No abre diálogo para nombre ni crea sender en DB (tabla `inbox_senders`)
- Debe: prompt nombre → insert DB → añadir fila funcional con QR operativo

### BUG-4: Borrar dispositivo no actualiza la tabla en tiempo real
- Al borrar un origen (papelera), la fila permanece visible
- Hay que cerrar y volver a abrir AddSourceDialog para ver el cambio
- Debe: eliminar fila de `_row_sources` y `table.removeRow()` inmediatamente tras `on_delete` callback

### BUG-5: Se crean dispositivos MTP desde ubicaciones de disco (falso positivo)
- `utils.get_mounted_drives()` detecta unidades y `is_removable_drive()` las marca como USB
- Pero algunos paths de disco fijo pasan el filtro y aparecen como "[USB] C:\..." o similar
- Debe: filtrar solo unidades verdaderamente removibles (SD, pendrives) y/o con etiqueta de volumen de cámara
- Pista: `is_removable_drive` usa `GetDriveType` = `DRIVE_REMOVABLE` (2); verificar que no coja fijos

### BUG-6: Botón borrar en filas de "Examinar" / "Detectar" no funciona
- Al añadir carpeta con "Examinar…" o detectar dispositivo, la fila tiene botón papelera
- El callback `on_delete` recibe `kind="folder"` o `kind="device"` pero no borra nada
- Debe: para `folder` → quitar de lista local; para `device` → llamar `on_delete(kind, value)` que borra de proyecto/DB

### BUG-7: Nombre de cámara manual no persiste en AddSourceDialog
- Usuario edita columna "Cámara" (QLineEdit), escribe nombre
- Al cerrar y reabrir AddSourceDialog, el nombre vuelve a "Sin nombre" o al original
- Debe: el nombre editado debe guardarse en la sesión/proyecto y recargarse al poblar

---

## Cambios / Mejoras solicitados (6)

### CHG-1: Opción menú "Borrar todos los dispositivos guardados"
- En barra de menú (ej. menú Herramientas / Dispositivos)
- Acción: borra tabla `known_devices` / `inbox_senders` / perfiles FTP
- Con diálogo de confirmación fuerte ("Esto no se puede deshacer")
- Para depurar nombres antiguos pegados en memoria

### CHG-2: Opción menú "Eliminar todas las cámaras conocidas"
- En barra de menú (mismo submenú)
- Acción: limpia cache de `metadata_engine` + nombres de cámara en DB (`files.camera_model`, `cameras` table)
- Permite resetear detección y ver si proyecto detecta solo cámaras reales

### CHG-3: Centrar checkboxes en AddSourceDialog
- Columna 0 (checkbox "Seleccionar") actualmente alineado a izquierda
- Debe: `Qt.AlignCenter` en el widget contenedor del checkbox

### CHG-4: Filas de sección (rótulos) en celda combinada (span)
- Filas "Conexión física (MTP/USB/SD)", "WiFi / PairDrop", "FTP"
- Actualmente: QLabel en columna 1 (Ruta), otras columnas vacías
- Debe: `table.setSpan(row, 0, 1, 5)` para que ocupe todas las columnas
- Estilo: fondo `theme.color("bg_elevated")`, negrita, padding

### CHG-5: Selector de cámara con nombres conocidos + trigger "Escanear"
- Columna "Cámara" (col 2): cambiar QLineEdit → QComboBox
- Items: nombres de cámara conocidos en sistema (DB `cameras` table + `files.camera_model` distinct)
- Último item: "🔍 Detectar cámara automáticamente…" (trigger)
- Al seleccionar trigger → lanza detección off-thread (reusa `_start_camera_detection`)
- Mientras detecta: muestra "Detectando…" en combo; al terminar rellena y selecciona el nombre detectado

### CHG-6: Integración CHG-5 con flujo existente
- Mantener `on_detect` callback para detección automática al seleccionar dispositivo sin nombre (D-09)
- El combo editable permite escribir nombre manual si no está en lista
- El nombre elegido (manual, conocido, o detectado) se guarda al aceptar

---

## Notas de implementación

### Para BUG-1 (Nuevo WiFi):
- `AddSourceDialog._add_wifi_row()` línea 389: reemplazar placeholder por `QInputDialog.getText` → `db.add_inbox_sender(name)` → `_append_real_wifi_row(sender)`

### Para BUG-2 (Borrar no actualiza):
- `AddSourceDialog._on_delete_clicked()` línea 309: tras `self.on_delete(kind, value)`, hacer `self._remove_row(row)` que limpie `_row_sources` y `removeRow`

### Para BUG-3 (MTP falso positivo):
- `AddSourceDialog._refresh_physical_section()` línea 377: reforzar filtro en `utils.get_mounted_drives()`
- Verificar `is_removable_drive` + que tenga etiqueta de volumen tipo cámara (DCIM, PRIVATE, etc.) o sea SD card
- Opción: solo mostrar USB si `kind == "usb"` y `utils.is_removable_drive(path)` ES True

### Para BUG-4 (Borrar en Examinar/Detectar):
- `main_window.py` `_on_source_deleted(kind, value)`: implementar borrado real
  - `kind="folder"` → quitar de `session.folders`
  - `kind="device"` → `db.delete_device_source(session_id, device_id)`
  - `kind="sender"` → `db.delete_inbox_sender(sender_id)`
  - `kind="ftp_profile"` → `db.delete_ftp_profile(profile_id)`

### Para BUG-5 (Cámara no persiste):
- `AddSourceDialog.result_sources()` ya devuelve `camera` editado
- `main_window._add_source_entry()` debe persistir en sesión/DB
- Al poblar (`_populate`), leer cámara guardada de la sesión, no del device info

### Para CHG-1/CHG-2 (Menú limpieza):
- `main_window.py`: añadir acciones en menú `&Herramientas` → `Borrar dispositivos guardados…` / `Borrar cámaras conocidas…`
- Conectar a métodos `_delete_all_saved_devices()` / `_delete_all_known_cameras()`

### Para CHG-3 (Centrar checkboxes):
- `AddSourceDialog._add_source_row()` línea 242: wrap checkbox en `QWidget` con `QHBoxLayout` + `setAlignment(Qt.AlignCenter)`

### Para CHG-4 (Span secciones):
- `AddSourceDialog._add_section()` línea 226: usar `self.table.setSpan(row, 0, 1, 5)` y poner QLabel en celda 0

### Para CHG-5/CHG-6 (Combo cámara + trigger):
- `AddSourceDialog._add_source_row()` línea 272: reemplazar `QLineEdit` por `QComboBox`
- Poblar con `self._get_known_camera_names()` (query DB distinct camera_model)
- Conectar `currentIndexChanged` → si es último índice (trigger) → `_start_camera_detection(row, src)`
- Hacer editable: `combo.setEditable(True)` + `combo.lineEdit().textChanged.connect(_update_ok_state)`

---

## Prioridad sugerida para mañana

1. **BUG-2** (borrar no actualiza) — bloquea UX básica
2. **BUG-1** (WiFi desaparece al abrir QR) — regresión UX crítica
3. **BUG-3** (Nuevo WiFi no crea) — feature rota
4. **BUG-4** (deseleccionar borra) — semántica incorrecta
5. **BUG-6** (borrar en Examinar/Detectar) — inconsistencia
6. **BUG-7** (cámara no persiste) — datos se pierden
7. **BUG-5** (MTP falso positivo) — ruido en lista
8. **CHG-3** (centrar checkboxes) — pulido rápido
9. **CHG-4** (span secciones) — pulido visual
10. **CHG-1/CHG-2** (menú limpieza) — herramienta debug
11. **CHG-5/CHG-6** (combo cámara + trigger) — mejora UX mayor

---

## Tests a añadir/actualizar

- `tests/test_add_source_dialog.py`: tests para BUG-1, BUG-2, BUG-3, BUG-4, BUG-5, BUG-6, BUG-7, CHG-3, CHG-4, CHG-5
- `tests/test_main_window.py`: tests para CHG-1, CHG-2, integración callbacks