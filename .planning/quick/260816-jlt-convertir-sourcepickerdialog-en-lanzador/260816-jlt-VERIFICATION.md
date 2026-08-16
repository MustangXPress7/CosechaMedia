---
phase: 260816-jlt-convertir-sourcepickerdialog-en-lanzador
verified: 2026-08-16T15:10:00Z
status: human_needed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Abrir la app, añadir un origen (botón «Añadir origen…» / Ctrl+O en el menú Ingesta) y revisar visualmente el lanzador: una única lista sin pestañas con las secciones Carpetas guardadas / Remitentes WiFi / Desconectados, y la fila de botones Examinar/USB-MTP/FTP/WiFi QR."
    expected: "El diálogo se ve ligero y correcto: encabezados de sección bold, ítems desconectados con «📱 {nombre} — desconectado» no seleccionables, Aceptar deshabilitado al abrir y habilitado solo al seleccionar carpeta/remitente; cada botón abre su propia ventana y el resultado vuelve a la tabla de orígenes."
    why_human: "La apariencia visual y la sensación del flujo (qué ventana se abre con cada botón, el gating de Aceptar percibido) no se pueden verificar con grep ni con tests offscreen; es la validación del operador que motivó la inversión parcial de D-12."
---

# Quick 260816-jlt: Convertir SourcePickerDialog en lanzador — Verification Report

**Task Goal:** Convertir SourcePickerDialog en lanzador compacto: eliminar las 3 pestañas, lista de Guardados (Carpetas/Remitentes WiFi/Desconectados como sección) + botones [Examinar][USB/MTP][FTP][WiFi QR]; cada uno abre su ventana propia (DevicePickerDialog, FtpPickerDialog, WifiMethodDialog→ShootInboxPanel); Aceptar solo habilitado con selección válida; registrar inversión parcial de D-12.
**Verified:** 2026-08-16
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth   | Status     | Evidence       |
| --- | ------- | ---------- | -------------- |
| 1   | El diálogo «Añadir origen» abre sin pestañas: una única lista con las secciones Carpetas guardadas / Remitentes WiFi / Desconectados, cada ítem desconectado mostrando su estado «desconectado» | ✓ VERIFIED | `source_picker.py` sin QTabWidget/QStackedWidget/QButtonGroup/QTimer/MtpDevicePane/FtpDevicePane (grep estructural limpio); `_build_ui` crea una sola `list_widget` con `_add_section` × 3 y `_missing_item` ("📱 {name} — desconectado", flags solo `Qt.ItemIsEnabled`); tests `test_no_tabs_and_three_sections` + `test_missing_section_lists_devices` verdes |
| 2   | Aceptar comienza deshabilitado y solo se habilita con una selección válida (carpeta o remitente con data(UserRole)); los encabezados de sección y los ítems desconectados no la habilitan | ✓ VERIFIED | `_update_ok_state` habilita solo si `currentItem.data(Qt.UserRole) is not None`; llamada al final de `_build_ui` y tras `_delete_selected`; `_accept_current` es no-op sin selección válida (no muta kind/value); tests `test_ok_btn_disabled_until_valid_selection`, `test_missing_item_does_not_enable_ok`, `test_accept_current_noop_without_valid_selection` verdes |
| 3   | Los botones Examinar / USB-MTP / FTP / WiFi QR abren cada flujo en su propia ventana (QFileDialog vía kind browse, DevicePickerDialog, FtpPickerDialog, y la cadena WifiMethodDialog→ShootInboxPanel vía MainWindow) y devuelven el resultado con el contrato (kind, value) intacto, sin cambios en main_window.py | ✓ VERIFIED | `_browse`→("browse", None); `_pick_device`→DevicePickerDialog (import módulo) con validación device_id/device_folder → ("device", (id, folder, name)); `_pick_ftp`→FtpPickerDialog → ("ftp_new", (profile_id, id, folder, name)); `_choose_wifi`→("wifi", None). `_apply_source_choice` (main_window.py:2853-2877) despacha browse/folder/sender/ftp_profile/device/ftp_new/wifi; `_pick_wifi_source` (3141) encadena WifiMethodDialog→`_pick_ftp_source`/`_open_wifi_panel` sin doble diálogo. Commits del plan `4ad1f70`+`572cd26` no tocan main_window.py (git show --stat) — el diff sucio de Fase 01 es preexistente. 7 tests de botones verdes |
| 4   | El menú contextual «Eliminar guardado…» sigue operando con on_delete para carpetas y remitentes | ✓ VERIFIED | `_show_item_menu`→`_delete_selected`→`on_delete(kind, value)`; takeItem + `_update_ok_state` solo si on_delete devuelve True; `_delete_saved_source` en main_window.py maneja folder/sender (y ftp_profile); tests `test_delete_saved_removes_item` + `test_delete_saved_keeps_item_when_rejected` verdes |
| 5   | Los tests de source_picker + wifi + e2e pasan en Qt offscreen | ✓ VERIFIED | `python -m unittest tests.test_source_picker tests.test_wifi_source tests.test_e2e` → **Ran 74 tests in 6.809s OK** (ejecutado por el verificador) |

**Score:** 5/5 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected    | Status | Details |
| -------- | ----------- | ------ | ------- |
| `app/ui/source_picker.py` | Lanzador compacto sin pestañas | ✓ VERIFIED | 224 líneas, implementación real (no stub); firma del constructor intacta `(parent, folders, senders, devices_missing, mtp_backend, ftp_backend, on_delete)`; imports módulo de DevicePickerDialog/FtpPickerDialog; sin rastro de `tabs`/`pane_stack`/`mtp_pane`/`btn_wifi_entry`/`missing_list` |
| `tests/test_source_picker.py` | Adaptado + nuevos tests | ✓ VERIFIED | 21 métodos `test_`; fakes patchean `app.ui.source_picker.DevicePickerDialog/FtpPickerDialog`; doble clic vía secuencia manual de QMouseEvent (QTest.mouseDClick no-op offscreen) |
| `.planning/phases/01-auditor-a-ui-y-plan-de-reubicaci-n/01-CONTEXT.md` | Nota REVISIÓN bajo D-12 | ✓ VERIFIED | Línea 33 con el literal exacto del plan; texto original de D-12 conservado en la línea anterior |
| `.planning/PROJECT.md` | Fila en Key Decisions | ✓ VERIFIED | Línea 65: «Inversión parcial de D-12 (lanzador de orígenes)» con el literal exacto del plan |

### Key Link Verification

| From | To  | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| SourcePickerDialog.kind/value | MainWindow._apply_source_choice | Contrato (kind, value) | WIRED | `_pick_source_entry` (2879) construye el diálogo con folders/senders/devices_missing/on_delete y devuelve `(dialog.kind, dialog.value)`; `_apply_source_choice` (2853) despacha browse/folder/sender/ftp_profile/device/ftp_new/wifi — cobertura completa |
| SourcePickerDialog._pick_device | DevicePickerDialog | device_id/device_folder/device_name | WIRED | Import módulo (source_picker.py:22); device_picker.py expone `self.device_id/device_name/device_folder` (líneas 249-251, poblados en 284-286) |
| SourcePickerDialog._pick_ftp | FtpPickerDialog | profile_id/device_id/device_folder/device_name | WIRED | Import módulo (source_picker.py:23); ftp_picker.py expone los 4 atributos (líneas 467-470, poblados en 503-506) |
| kind='wifi' | MainWindow._pick_wifi_source | Cadena WifiMethodDialog → ShootInboxPanel / FtpPickerDialog | WIRED | main_window.py:2876-2877 y 3141-3150: WifiMethodDialog → `method=="ftp"`→`_pick_ftp_source()` / `"pairdrop"`→`_open_wifi_panel(force_new_sender=True)` — sin doble diálogo; test_e2e + test_wifi_source verdes |
| Registro inversión parcial D-12 | 01-CONTEXT.md + PROJECT.md | Nota REVISIÓN + fila Key Decisions | WIRED | Contenido literal del plan presente en ambos documentos |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| list_widget (Carpetas) | folders | `db.get_recent_paths("source")` + `db.get_sessions()` vía `_pick_source_entry` (main_window.py:2890-2896) | Sí | ✓ FLOWING |
| list_widget (Remitentes WiFi) | senders | `db.list_inbox_senders()` + `sanitize_alias` usado (main_window.py:2899-2901) | Sí | ✓ FLOWING |
| list_widget (Desconectados) | devices_missing | `_disconnected_devices()`: `mtp.WpdBackend().list_devices()` ∩ `db.get_sessions()` (main_window.py:2903) | Sí | ✓ FLOWING |
| kind/value | Dialogo → `_apply_source_choice` | Resultados reales de DevicePickerDialog/FtpPickerDialog/WifiMethodDialog | Sí | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Suite source_picker + wifi + e2e en Qt offscreen | `python -m unittest tests.test_source_picker tests.test_wifi_source tests.test_e2e` | Ran 74 tests in 6.809s — OK (ffprobe stderr es el error-handling esperado de los tests e2e con medios falsos) | ✓ PASS |
| Gate estructural sin pestañas | grep QTabWidget/btn_wifi_entry/missing_list/pane_stack en source_picker.py | Sin coincidencias | ✓ PASS |
| Registro D-12 en docs | grep REVISIÓN (2026-08-16) en 01-CONTEXT.md; «Inversión parcial de D-12» en PROJECT.md | Ambas presentes con literal exacto | ✓ PASS |
| main_window.py sin tocar por este plan | `git show --stat 4ad1f70 572cd26` | Solo `tests/test_source_picker.py` y `app/ui/source_picker.py` | ✓ PASS |

### Probe Execution

No probes declarados en el plan (plan de UI con gate de tests). N/A.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| UI-04 | 260816-jlt-PLAN | Diálogo de orígenes rediseñado como lanzador (sin pestañas, secciones, Aceptar gated) | ✓ SATISFIED | Truths 1, 2, 4; tests verdes |
| UI-05 | 260816-jlt-PLAN | Flujos USB/MTP/FTP/WiFi desde ventanas propias con contrato intacto | ✓ SATISFIED | Truth 3; key links 2-4; e2e verde |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | Sin deuda: sin TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER en `source_picker.py` ni `tests/test_source_picker.py`; sin `pass`/stubs; todos los strings UI pasan por `tr()`/`QtString` (único literal no traducible: prefijo emoji "📱 " y " — " en `_missing_item`) | ℹ️ Info | Ninguno |

### Human Verification Required

### 1. Aceptación visual y de flujo del lanzador por el operador

**Test:** Abrir la app, añadir un origen (botón «Añadir origen…» o menú Ingesta → Seleccionar origen) y revisar el lanzador en vivo: lista sin pestañas con las 3 secciones, fila de botones Examinar/USB-MTP/FTP/WiFi QR, y cada flujo abriendo su ventana propia.
**Expected:** El diálogo se ve ligero y correcto: encabezados de sección bold, ítems desconectados «📱 {nombre} — desconectado» no seleccionables, Aceptar deshabilitado al abrir y habilitado solo al seleccionar carpeta/remitente; cada botón abre su propia ventana y el resultado vuelve a la tabla de orígenes sin errores.
**Why human:** La apariencia visual y la sensación del flujo no se pueden verificar con grep ni con tests offscreen (la plataforma offscreen valida lógica y wiring, no percepción); es la validación del operador que motivó la inversión parcial de D-12.

### Gaps Summary

Sin gaps funcionales: los 5 must-haves están verificados con evidencia (implementación real, wiring completo, data-flow desde la BD, y la suite de 74 tests ejecutada por el verificador en verde). El único resto es la confirmación visual/funcional del operador (status `human_needed`, no `gaps_found`). Nota de contexto: `app/ui/main_window.py` tiene diffs sin commitear preexistentes de la Fase 01 (wiring D-12) — no son de este plan (sus commits `4ad1f70`/`572cd26` solo tocan `source_picker.py` y `tests/test_source_picker.py`); el contrato (kind, value) en el working tree está intacto y cubre los 7 kinds.

---

_Verified: 2026-08-16_
_Verifier: the agent (gsd-verifier)_
