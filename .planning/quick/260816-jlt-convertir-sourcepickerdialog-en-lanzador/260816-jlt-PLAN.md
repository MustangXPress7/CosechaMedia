---
phase: 260816-jlt-convertir-sourcepickerdialog-en-lanzador
plan: 1
type: execute
wave: 1
depends_on: []
files_modified:
  - app/ui/source_picker.py
  - tests/test_source_picker.py
  - .planning/phases/01-auditor-a-ui-y-plan-de-reubicaci-n/01-CONTEXT.md
  - .planning/PROJECT.md
autonomous: true
requirements: [UI-04, UI-05]
estimate:
  tokens: 18000
  raw_tokens: 18000
  tasks: 2
  confidence: low

must_haves:
  truths:
    - "El diálogo «Añadir origen» abre sin pestañas: una única lista con las secciones Carpetas guardadas / Remitentes WiFi / Desconectados, cada ítem desconectado mostrando su estado «desconectado»."
    - "Aceptar comienza deshabilitado y solo se habilita con una selección válida (carpeta o remitente con data(UserRole)); los encabezados de sección y los ítems desconectados no la habilitan."
    - "Los botones Examinar / USB-MTP / FTP / WiFi QR abren cada flujo en su propia ventana (QFileDialog vía kind browse, DevicePickerDialog, FtpPickerDialog, y la cadena WifiMethodDialog→ShootInboxPanel vía MainWindow) y devuelven el resultado con el contrato (kind, value) intacto, sin cambios en main_window.py."
    - "El menú contextual «Eliminar guardado…» sigue operando con on_delete para carpetas y remitentes."
    - "Los tests de source_picker + wifi + e2e pasan en Qt offscreen."
  artifacts:
    - app/ui/source_picker.py
    - tests/test_source_picker.py
    - .planning/phases/01-auditor-a-ui-y-plan-de-reubicaci-n/01-CONTEXT.md
    - .planning/PROJECT.md
  key_links:
    - "SourcePickerDialog.kind/value ↔ MainWindow._apply_source_choice: contrato (kind, value) intacto — browse/folder/sender/device/ftp_new/wifi."
    - "SourcePickerDialog._pick_device ↔ DevicePickerDialog.accept(): device_id/device_folder/device_name."
    - "SourcePickerDialog._pick_ftp ↔ FtpPickerDialog.accept(): profile_id/device_id/device_folder/device_name."
    - "kind='wifi' ↔ MainWindow._pick_wifi_source(): cadena WifiMethodDialog → ShootInboxPanel / FtpPickerDialog sin doble diálogo."
    - "Registro de la inversión parcial de D-12 en 01-CONTEXT.md y PROJECT.md (Key Decisions)."
---

<objective>
Convertir `SourcePickerDialog` en un lanzador compacto de orígenes.

**Purpose:** El diálogo unificado D-12 (3 pestañas que embeben los paneles MTP/FTP dentro de la misma ventana) se rediseña a petición del operador: una sola ventana sin pestañas con la lista de Guardados por secciones (Carpetas guardadas, Remitentes WiFi, Desconectados) y una fila de botones que abren cada buscador en su propia ventana. Así el diálogo principal se vuelve ligero y cada flujo (USB/MTP, FTP, WiFi) conserva su ventana dedicada, eliminando además el botón «Aceptar» muerto de la pestaña Guardados (hallazgo UI-REVIEW #1): Aceptar solo se habilita con selección válida. Se registra la inversión parcial de D-12 en los documentos de decisión.

**Output:**
- `app/ui/source_picker.py` reescrito como lanzador (sin QTabWidget ni paneles embebidos).
- `tests/test_source_picker.py` adaptado + tests nuevos (gating de Aceptar, botones, secciones).
- Anotación de revisión en D-12 (`01-CONTEXT.md`) y fila en Key Decisions (`PROJECT.md`).
</objective>

<execution_context>
@C:/Users/JoanRamon/.config/opencode/gsd-core/workflows/execute-plan.md
@C:/Users/JoanRamon/.config/opencode/gsd-core/templates/summary.md
</execution_context>

<context>
@C:/Users/JoanRamon/Documents/CosechaMedia/.planning/quick/260816-jlt-convertir-sourcepickerdialog-en-lanzador/260816-jlt-PLAN.md

# Fuente de decisiones
@C:/Users/JoanRamon/Documents/CosechaMedia/.planning/phases/01-auditor-a-ui-y-plan-de-reubicaci-n/01-CONTEXT.md (D-12 — decisión que este plan remodela por petición explícita del operador; resto de decisiones D-01..D-11 y D-03 «no esconder nada» vigentes)
@C:/Users/JoanRamon/Documents/CosechaMedia/.planning/phases/01-auditor-a-ui-y-plan-de-reubicaci-n/01-UI-REVIEW.md (hallazgo 1: «Aceptar muerto» en Guardados, source_picker.py:210,226-233; hallazgo 4: botones zombie btn_browse_source/btn_receive_wifi — FUERA de alcance, no tocar)

# Código relevante
@C:/Users/JoanRamon/Documents/CosechaMedia/app/ui/source_picker.py (objetivo del cambio)
@C:/Users/JoanRamon/Documents/CosechaMedia/app/ui/device_picker.py (DevicePickerDialog: device_id/device_name/device_folder)
@C:/Users/JoanRamon/Documents/CosechaMedia/app/ui/ftp_picker.py (FtpPickerDialog: profile_id/device_id/device_name/device_folder)
@C:/Users/JoanRamon/Documents/CosechaMedia/app/ui/main_window.py (solo lectura: `_pick_source_entry` :2879-2909 y `_apply_source_choice` :2853-2877 — contrato (kind, value))
@C:/Users/JoanRamon/Documents/CosechaMedia/tests/test_source_picker.py (adaptación)
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Reescribir SourcePickerDialog como lanzador compacto (sin pestañas) con Aceptar gated y botones que abren ventanas propias</name>
  <files>app/ui/source_picker.py, tests/test_source_picker.py</files>
  <behavior>
    - Test 1: el diálogo no tiene QTabWidget; `list_widget` contiene los encabezados de sección "Carpetas guardadas", "Remitentes WiFi" y "Desconectados" (los encabezados no tienen data(Qt.UserRole)).
    - Test 2: `ok_btn` está deshabilitado al abrir; al seleccionar un ítem de carpeta o remitente (con UserRole) se habilita; al quitar la selección vuelve a deshabilitarse.
    - Test 3: seleccionar un ítem "desconectado" (sin UserRole) NO habilita `ok_btn`; `_accept_current()` sin selección válida no acepta y no muta kind/value.
    - Test 4: clic en "Examinar…" → kind="browse", value=None (accept).
    - Test 5: clic en "USB/MTP" → se crea DevicePickerDialog; con fake Accepted + device_id/device_folder válidos → kind="device", value=(device_id, device_folder, device_name); con Cancelar → kind sigue None.
    - Test 6: clic en "FTP" → se crea FtpPickerDialog; fake Accepted → kind="ftp_new", value=(profile_id, device_id, device_folder, device_name).
    - Test 7: clic en "WiFi QR" → kind="wifi", value=None (accept).
    - Test 8: doble clic en ítem válido acepta; menú contextual "Eliminar guardado…" borra vía on_delete (keep/reject).
    - Test 9: la firma del constructor no cambia (folders, senders, devices_missing, mtp_backend, ftp_backend, on_delete) — compatibilidad con `_pick_source_entry`.
  </behavior>
  <action>
    Reescribe `app/ui/source_picker.py` como lanzador compacto (per D-12 remodelado por el operador; respeta D-03 «no esconder nada» y las convenciones de CONVENTIONS.md: strings ES vía tr()/QtString, `_` en helpers privados, construcción programática sin .ui).

    ORDEN TDD: primero actualiza `tests/test_source_picker.py` a la nueva estructura (RED — los tests nuevos fallan contra la implementación actual), luego reescribe `source_picker.py` hasta verde (GREEN). Commits atómicos: test (RED) y feat (GREEN) separados.

    ESTRUCTURA NUEVA del diálogo:
    - Mantén la firma de `__init__` intacta (parent, folders, senders, devices_missing, mtp_backend, ftp_backend, on_delete). `mtp_backend`/`ftp_backend` se conservan por compatibilidad de API pero el lanzador no los usa (los diálogos hijos crean los suyos). Sigue exponiendo `self.kind` y `self.value` con el contrato existente.
    - Elimina el QTabWidget y las 3 pestañas: `tabs`, `_build_saved_tab`, `_build_devices_tab`, `_build_missing_tab`, `pane_stack`, `mtp_pane`, `ftp_pane`, `btn_wifi_entry`, `btn_mtp_tab`, `btn_ftp_tab`, `_preload_panes`, `_on_tab_changed`, `_on_pane_selection_changed`, `_on_search_again`, y el QTimer. Elimina los imports de QTabWidget, QStackedWidget, QButtonGroup, QTimer, MtpDevicePane y FtpDevicePane.
    - Importa a nivel de módulo `DevicePickerDialog` (de `app.ui.device_picker`) y `FtpPickerDialog` (de `app.ui.ftp_picker`) — import en el namespace del módulo para que los tests puedan parchearlos como `app.ui.source_picker.DevicePickerDialog`. No importes WifiMethodDialog aquí: el WiFi se resuelve devolviendo ("wifi", None) y MainWindow encadena.
    - Layout: hint (una línea, wordWrap) → `self.list_widget` (QListWidget, stretch 1) → fila de búsqueda con 4 QPushButton: `btn_browse` ("Examinar…"), `btn_mtp` ("USB/MTP"), `btn_ftp` ("FTP"), `btn_wifi_qr` ("WiFi QR") + stretch → fila inferior: Cancelar (reject) y `ok_btn` "Aceptar" (objectName "PrimaryAction", click→`_accept_current`). Ventana mínima ~560px.
    - `list_widget`: conecta itemDoubleClicked→`_accept_item`, customContextMenuRequested→`_show_item_menu`, itemSelectionChanged→`_update_ok_state`.
    - Secciones con `_add_section` (mantén el patrón actual: encabezado bold no seleccionable + "(vacío)" si no hay ítems): "Carpetas guardadas" con `_folder_item`, "Remitentes WiFi" con `_sender_item`, "Desconectados" con un nuevo `_missing_item(dev)` que crea un QListWidgetItem "📱 {name} — desconectado" con flags Qt.ItemIsEnabled (sin UserRole: no seleccionable, no habilita Aceptar, no borrable) y tooltip de estado. Conserva `saved_empty_label` ("Sin dispositivos guardados") visible solo si no hay carpetas ni remitentes.
    - Aceptar gated (cierra el hallazgo del botón muerto): `_update_ok_state` habilita `ok_btn` solo si `currentItem` tiene `data(Qt.UserRole)` no nulo; llámala al final de `_build_ui` y tras `_delete_selected` (takeItem cambia la selección). `_accept_current` = obtener currentItem; si None o UserRole nulo, return sin hacer nada (no mutar kind/value); si válido, `_set_from_item` + accept.
    - Botones: `_browse` → kind="browse", value=None, accept (sin abrir QFileDialog: lo abre MainWindow en `_apply_source_choice`). `_pick_device` → ejecuta DevicePickerDialog(self); si `dialog.exec() == QDialog.Accepted` y `dialog.device_id` y `dialog.device_folder` no vacíos, kind="device", value=(device_id, device_folder, device_name), accept; si no, return (el lanzador permanece abierto). `_pick_ftp` → idéntico con FtpPickerDialog y kind="ftp_new", value=(profile_id, device_id, device_folder, device_name); si no hay device_id/device_folder válidos, return sin aceptar. `_choose_wifi` → kind="wifi", value=None, accept.
    - Conserva sin cambios de comportamiento: `_accept_item`, `_set_from_item`, `_folder_item`, `_sender_item`, `_show_item_menu`, `_delete_selected`, `_add_section`.
    - NO toques `app/ui/main_window.py` (el contrato (kind, value) cubre browse/folder/sender/device/ftp_new/wifi; la cadena WiFi WifiMethodDialog→ShootInboxPanel sigue intacta en `_apply_source_choice`→`_pick_wifi_source`). NO toques los botones zombie `btn_browse_source`/`btn_receive_wifi` (UI-REVIEW hallazgo 4, fuera de alcance; tests dependen de ellos).

    TESTS (`tests/test_source_picker.py`): conserva los tests que sigan siendo válidos (sender/folder selection, browse, "Sin dispositivos guardados", no duplicación de perfiles FTP en Guardados, delete keep/reject, "(vacío)"). Sustituye los que dependen de la estructura vieja: `test_wifi_button_in_devices_tab` (usaba `dlg.tabs.widget(1)`/`btn_wifi_entry`) pasa a verificar `btn_wifi_qr` y la ausencia de tabs; `test_missing_tab_has_no_ftp_profiles` (usaba `missing_list`) pasa a buscar la sección "Desconectados" dentro de `list_widget`. Añade los tests del bloque `<behavior>` con fakes: para USB/MTP y FTP parchea `app.ui.source_picker.DevicePickerDialog` / `app.ui.source_picker.FtpPickerDialog` con subclases fake que fijan `exec`/`device_id`/`device_folder`/`device_name`/`profile_id` y registran si fueron construidos. Usa `QTest`/llamadas directas a los handlers igual que el patrón actual del archivo (el test se ejecuta offscreen vía QT_QPA_PLATFORM).
  </action>
  <verify>
    <automated>python -m unittest tests.test_source_picker tests.test_wifi_source tests.test_e2e -v</automated>
  </verify>
  <done>La suite de los 3 archivos pasa verde; `source_picker.py` no contiene QTabWidget y expone `btn_browse`/`btn_mtp`/`btn_ftp`/`btn_wifi_qr`; el diálogo devuelve el contrato (kind, value) sin cambios en `main_window.py`.</done>
</task>

<task type="auto">
  <name>Task 2: Registrar la inversión parcial de D-12 en los documentos de decisión</name>
  <files>.planning/phases/01-auditor-a-ui-y-plan-de-reubicaci-n/01-CONTEXT.md, .planning/PROJECT.md</files>
  <action>
    Registra la inversión parcial de D-12 decidida por el operador el 2026-08-16 (per petición explícita del usuario; usa Edit con reemplazo puntual, nunca Write sobre el documento completo).

    1. En `01-CONTEXT.md`, sobre la entrada D-12 (línea 32): conserva el texto original y añade debajo una línea de revisión con este contenido literal: "**REVISIÓN (2026-08-16):** inversión parcial por decisión del operador — el diálogo unificado pasa a ser un lanzador compacto sin pestañas: los paneles MTP/FTP embebidos se sustituyen por botones (USB/MTP, FTP, WiFi QR) que abren `DevicePickerDialog`/`FtpPickerDialog`/la cadena WiFi en ventanas propias; se mantiene vigente la parte de D-12 de mostrar los guardados y la zona de dispositivos desconectados en la misma ventana de orígenes. Impacto: `app/ui/source_picker.py` (reescrito) y `tests/test_source_picker.py` (adaptado)." No modifiques ninguna otra decisión.
    2. En `PROJECT.md`, sección `## Key Decisions` (tabla de la línea 60): añade una fila nueva: "Inversión parcial de D-12 (lanzador de orígenes) | El diálogo unificado con 3 pestañas embebidas se rediseñó como lanzador compacto: lista de Guardados por secciones + botones que abren DevicePickerDialog/FtpPickerDialog/cadena WiFi en ventanas propias | ✓ Good — registrado 2026-08-16 (quick 260816-jlt)". No toques el resto de la tabla ni la sección Evolution.
  </action>
  <verify>
    <automated>python -c "import pathlib; c=pathlib.Path('.planning/phases/01-auditor-a-ui-y-plan-de-reubicaci-n/01-CONTEXT.md').read_text(encoding='utf-8'); p=pathlib.Path('.planning/PROJECT.md').read_text(encoding='utf-8'); assert 'REVISIÓN (2026-08-16)' in c and 'inversión parcial' in c, 'falta nota en 01-CONTEXT.md'; assert 'Inversión parcial de D-12' in p and '260816-jlt' in p, 'falta fila en PROJECT.md'"</automated>
  </verify>
  <done>La nota de revisión de D-12 existe en `01-CONTEXT.md` (texto original conservado) y la fila de decisión existe en `PROJECT.md` Key Decisions.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Diálogos hijos → lanzador | El resultado de DevicePickerDialog/FtpPickerDialog (device_id/device_folder/profile_id) cruza de un diálogo a otro como datos de confianza |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-260816-01 | Spoofing | `_pick_device`/`_pick_ftp` | low | mitigate | Validar `device_id`/`device_folder` no vacíos antes de aceptar (los diálogos hijos ya validan vía `commit()`; el lanzador no confía en el Accepted por sí solo) |
| T-260816-02 | Tampering | `source_picker.py` rewrite | low | mitigate | Tests offscreen (test_source_picker + test_wifi_source + test_e2e) verifican el contrato (kind, value) y la cadena WiFi; ningún string nuevo escapa de `tr()` |
| T-260816-SC | Tampering | instala paquetes | n/a | accept | Sin instalación de paquetes en este plan — no aplica gate de legitimidad |
</threat_model>

<verification>
- Ejecutar la suite de los 3 archivos afectados: `python -m unittest tests.test_source_picker tests.test_wifi_source tests.test_e2e -v` — debe salir verde.
- Verificar que `app/ui/main_window.py` queda sin diffs (el contrato (kind, value) se preserva).
- Verificar que `app/ui/source_picker.py` no conserva rastro de la estructura de pestañas (QTabWidget, pane_stack, mtp_pane, btn_wifi_entry, missing_list).
</verification>

<success_criteria>
- El diálogo «Añadir origen» abre sin pestañas con las 3 secciones en una lista y Aceptar gated a selección válida.
- Cada botón abre su ventana propia y devuelve el resultado sin cambios en `main_window.py`.
- La inversión parcial de D-12 queda registrada en `01-CONTEXT.md` y `PROJECT.md`.
- Tests de source_picker + wifi + e2e en verde; sin cambios en `app/core/`.
</success_criteria>

<output>
Create `.planning/quick/260816-jlt-convertir-sourcepickerdialog-en-lanzador/260816-jlt-SUMMARY.md` when done, siguiendo `templates/summary.md` (quick: qué se cambió, qué tests cubren el gating de Aceptar y los botones, verificación del contrato (kind, value), y el registro de la inversión parcial de D-12).
</output>
