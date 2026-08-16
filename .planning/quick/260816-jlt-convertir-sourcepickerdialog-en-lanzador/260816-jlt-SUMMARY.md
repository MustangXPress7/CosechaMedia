---
phase: 260816-jlt-convertir-sourcepickerdialog-en-lanzador
plan: 1
subsystem: ui
tags: [pyside6, qt, source-picker, dialog, launcher, d-12]

requires:
  - phase: 01-auditor-a-ui-y-plan-de-reubicaci-n
    provides: D-12 decisión del diálogo unificado de orígenes, UI-REVIEW hallazgo 1 (Aceptar muerto)
provides:
  - "SourcePickerDialog como lanzador compacto sin pestañas: lista por secciones (Carpetas guardadas / Remitentes WiFi / Desconectados) + botones que abren ventanas propias"
  - "Aceptar gated a selección válida (cierra el hallazgo UI-REVIEW #1 del botón muerto)"
  - "Contrato (kind, value) intacto: browse/folder/sender/device/ftp_new/wifi, sin cambios en main_window.py"
  - "Registro de la inversión parcial de D-12 en 01-CONTEXT.md y PROJECT.md Key Decisions"
affects: [01-auditor-a-ui-y-plan-de-reubicaci-n, verify-work, fase de implementación v2 UI-04/UI-05]

actuals:
  tokens: 5783
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Diálogo lanzador: los flujos pesados (DevicePickerDialog/FtpPickerDialog) se abren en ventanas propias en lugar de embeberse"
    - "Doble clic en tests offscreen vía envío manual de QMouseEvent (QTest.mouseDClick no genera el evento en plataforma offscreen)"

key-files:
  created: []
  modified:
    - app/ui/source_picker.py
    - tests/test_source_picker.py
    - .planning/phases/01-auditor-a-ui-y-plan-de-reubicaci-n/01-CONTEXT.md
    - .planning/PROJECT.md

key-decisions:
  - "Inversión parcial de D-12: el diálogo unificado con 3 pestañas embebidas se rediseñó como lanzador compacto (lista de Guardados por secciones + botones USB/MTP, FTP, WiFi QR que abren ventanas propias); se mantiene la parte de D-12 de mostrar guardados y dispositivos desconectados en la misma ventana"
  - "mtp_backend/ftp_backend se conservan en la firma del constructor por compatibilidad de API pero el lanzador no los usa (los diálogos hijos crean los suyos)"

requirements-completed: [UI-04, UI-05]

coverage:
  - id: D1
    description: "Diálogo «Añadir origen» sin pestañas: una única lista con las secciones Carpetas guardadas / Remitentes WiFi / Desconectados; encabezados sin UserRole"
    requirement: UI-04
    verification:
      - kind: unit
        ref: "tests/test_source_picker.py#test_no_tabs_and_three_sections"
        status: pass
      - kind: unit
        ref: "tests/test_source_picker.py#test_missing_section_lists_devices"
        status: pass
    human_judgment: false
  - id: D2
    description: "Aceptar deshabilitado al abrir, se habilita solo con selección válida (folder/sender con UserRole); ítems desconectados no la habilitan; _accept_current sin selección válida es no-op"
    requirement: UI-04
    verification:
      - kind: unit
        ref: "tests/test_source_picker.py#test_ok_btn_disabled_until_valid_selection"
        status: pass
      - kind: unit
        ref: "tests/test_source_picker.py#test_missing_item_does_not_enable_ok"
        status: pass
      - kind: unit
        ref: "tests/test_source_picker.py#test_accept_current_noop_without_valid_selection"
        status: pass
    human_judgment: false
  - id: D3
    description: "Botones Examinar / USB-MTP / FTP / WiFi QR abren cada flujo en su propia ventana (browse sin QFileDialog, DevicePickerDialog, FtpPickerDialog, wifi→cadena MainWindow) y devuelven el contrato (kind, value) intacto; cancelar no muta kind/value"
    requirement: UI-05
    verification:
      - kind: unit
        ref: "tests/test_source_picker.py#test_browse_button_sets_browse"
        status: pass
      - kind: unit
        ref: "tests/test_source_picker.py#test_mtp_button_opens_device_picker_and_accepts"
        status: pass
      - kind: unit
        ref: "tests/test_source_picker.py#test_mtp_button_cancel_keeps_launcher_open"
        status: pass
      - kind: unit
        ref: "tests/test_source_picker.py#test_ftp_button_opens_ftp_picker_and_accepts"
        status: pass
      - kind: unit
        ref: "tests/test_source_picker.py#test_wifi_qr_button_sets_wifi"
        status: pass
      - kind: unit
        ref: "tests/test_source_picker.py#test_mtp_requires_valid_device_folder"
        status: pass
    human_judgment: false
  - id: D4
    description: "Menú contextual «Eliminar guardado…» sigue operando vía on_delete (keep/reject) y doble clic en ítem válido acepta"
    verification:
      - kind: unit
        ref: "tests/test_source_picker.py#test_double_click_item_accepts"
        status: pass
      - kind: unit
        ref: "tests/test_source_picker.py#test_delete_saved_removes_item"
        status: pass
      - kind: unit
        ref: "tests/test_source_picker.py#test_delete_saved_keeps_item_when_rejected"
        status: pass
    human_judgment: false
  - id: D5
    description: "Firma del constructor sin cambios (folders, senders, devices_missing, mtp_backend, ftp_backend, on_delete) — compatibilidad con _pick_source_entry"
    verification:
      - kind: unit
        ref: "tests/test_source_picker.py#test_constructor_signature_compat"
        status: pass
    human_judgment: false
  - id: D6
    description: "Suite completa de los 3 archivos afectados en verde (source_picker + wifi_source + e2e) en Qt offscreen"
    verification:
      - kind: unit
        ref: "python -m unittest tests.test_source_picker tests.test_wifi_source tests.test_e2e -v"
        status: pass
    human_judgment: false
  - id: D7
    description: "Inversión parcial de D-12 registrada en 01-CONTEXT.md (nota REVISIÓN) y PROJECT.md (fila Key Decisions)"
    verification:
      - kind: other
        ref: "python -c assert REVISIÓN (2026-08-16) en 01-CONTEXT.md y fila Inversión parcial de D-12 en PROJECT.md"
        status: pass
    human_judgment: false

duration: ~20min
completed: 2026-08-16
status: complete
---

# Quick 260816-jlt: Convertir SourcePickerDialog en lanzador Summary

**SourcePickerDialog reescrito como lanzador compacto sin pestañas — lista de Guardados por secciones (Carpetas guardadas / Remitentes WiFi / Desconectados), Aceptar gated a selección válida (cierra UI-REVIEW #1) y botones Examinar/USB-MTP/FTP/WiFi QR que abren cada buscador en su propia ventana, con el contrato (kind, value) intacto y sin cambios en main_window.py; inversión parcial de D-12 registrada en los documentos de decisión**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-08-16
- **Completed:** 2026-08-16
- **Tasks:** 2
- **Files modified:** 4 (2 código + 2 docs de decisión)

## Accomplishments

- `SourcePickerDialog` reescrito como lanzador: sin `QTabWidget` ni paneles MTP/FTP embebidos; una única `list_widget` con las secciones "Carpetas guardadas", "Remitentes WiFi" y "Desconectados" (esta última con ítems "📱 {name} — desconectado", sin UserRole → no seleccionables, no habilitan Aceptar, no borrables).
- Aceptar gated: `_update_ok_state` habilita `ok_btn` solo con selección válida (UserRole no nulo); `_accept_current` es no-op sin selección válida — cierra el hallazgo UI-REVIEW #1 del «Aceptar» muerto.
- Botones de búsqueda en fila propia: "Examinar…" (`kind="browse", value=None`), "USB/MTP" (`DevicePickerDialog` → `kind="device"`), "FTP" (`FtpPickerDialog` → `kind="ftp_new"`), "WiFi QR" (`kind="wifi", value=None` → MainWindow encadena WifiMethodDialog→ShootInboxPanel). Validación defensiva de `device_id`/`device_folder` no vacíos antes de aceptar (T-260816-01); cancelar deja el lanzador abierto sin mutar kind/value.
- Contrato (kind, value) intacto — `main_window.py` sin tocar; la firma del constructor se conserva (compatibilidad con `_pick_source_entry`).
- Inversión parcial de D-12 registrada: nota `**REVISIÓN (2026-08-16):**` bajo la entrada D-12 en `01-CONTEXT.md` (texto original conservado) y fila "Inversión parcial de D-12 (lanzador de orígenes)" en `PROJECT.md` Key Decisions.
- 21 tests de `test_source_picker.py` (adaptados + nuevos: gating de Aceptar, secciones, botones con fakes, doble clic, signature compat); suite completa de los 3 archivos (74 tests) en verde.

## Task Commits

Cada tarea se commiteó atómicamente:

1. **Task 1: Reescribir SourcePickerDialog como lanzador compacto (TDD)** - `4ad1f70` (test: RED) + `572cd26` (feat: GREEN)
2. **Task 2: Registrar la inversión parcial de D-12 en los documentos de decisión** - sin commit (docs; el orquestador gestiona el commit de docs)

**Plan metadata:** 7f4fddd (docs: plan — preexistente)

## Files Created/Modified

- `app/ui/source_picker.py` - Reescrito como lanzador compacto: sin QTabWidget/QStackedWidget/QButtonGroup/QTimer/MtpDevicePane/FtpDevicePane; imports de `DevicePickerDialog`/`FtpPickerDialog` a nivel de módulo; list_widget con 3 secciones; ok_btn gated; botones btn_browse/btn_mtp/btn_ftp/btn_wifi_qr; `_missing_item` nuevo; se conservan `_accept_item`, `_set_from_item`, `_folder_item`, `_sender_item`, `_show_item_menu`, `_delete_selected`, `_add_section`.
- `tests/test_source_picker.py` - Adaptado a la estructura lanzador: tests conservados (sender/folder selection, browse, "(vacío)", no duplicación FTP, delete keep/reject, sufijo "(ya asignado)") + nuevos (no tabs y 3 secciones, gating de Aceptar, ítem desconectado no habilita, botones con fakes DevicePickerDialog/FtpPickerDialog, doble clic, firma del constructor).
- `.planning/phases/01-auditor-a-ui-y-plan-de-reubicaci-n/01-CONTEXT.md` - Nota `REVISIÓN (2026-08-16)` bajo la entrada D-12 (texto original conservado).
- `.planning/PROJECT.md` - Fila nueva en Key Decisions: "Inversión parcial de D-12 (lanzador de orígenes)".

## Decisions Made

- Inversión parcial de D-12 por decisión explícita del operador (2026-08-16): el diálogo unificado con 3 pestañas embebidas se rediseña como lanzador compacto; los paneles MTP/FTP embebidos se sustituyen por botones que abren `DevicePickerDialog`/`FtpPickerDialog`/cadena WiFi en ventanas propias; se mantiene vigente la parte de D-12 de mostrar guardados + dispositivos desconectados en la misma ventana de orígenes.
- `mtp_backend`/`ftp_backend` se conservan en la firma por compatibilidad de API (D-03 «no esconder nada» y contrato con `_pick_source_entry` intactos).
- Tests offscreen: doble clic simulado con envío manual de `QMouseEvent` (press/release/dblclick/release) porque `QTest.mouseDClick` no genera el evento en la plataforma offscreen.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `QTest.mouseDClick` (y doble clic manual con `mouseClick`×2) no dispara `itemDoubleClicked` en Qt offscreen (la selección sí cambia, pero el evento de doble clic no llega a la vista). Resuelto enviando la secuencia de eventos `QMouseEvent` explícitamente (Press → Release → MouseButtonDblClick → Release) — fixture `_send_double_click` en el test.
- Observación (no causada por este plan): `app/ui/main_window.py` tenía diffs sin commitear de la implementación v2 de Fase 01 (wiring D-12, ~362 inserciones) junto con el resto del estado sucio de la Fase 01. Este plan no tocó `main_window.py` ni `app/core/` — los diffs preexistentes permanecen intactos para su commit por el flujo que corresponda.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- El diálogo «Añadir origen» abre sin pestañas con las 3 secciones y Aceptar gated; cada botón abre su ventana propia con el contrato (kind, value) intacto — listo para la verificación funcional por el operador (quick).
- La inversión parcial de D-12 queda documentada para la fase de implementación v2 (UI-04/UI-05), que deberá partir del estado actual de `source_picker.py`.
- Pendiente de resolver por el flujo de Fase 01: el commit del estado sucio preexistente (wiring D-12 de `main_window.py`, `device_picker.py`, `ftp_picker.py`, `app/core/`, i18n y tests asociados) que este plan asumió como base.

---
*Quick: 260816-jlt-convertir-sourcepickerdialog-en-lanzador*
*Completed: 2026-08-16*

## Self-Check: PASSED

- FOUND: `app/ui/source_picker.py`
- FOUND: `tests/test_source_picker.py`
- FOUND: `.planning/quick/260816-jlt-convertir-sourcepickerdialog-en-lanzador/260816-jlt-SUMMARY.md`
- FOUND: commit `4ad1f70` (test RED)
- FOUND: commit `572cd26` (feat GREEN)
- Verificación completa: `python -m unittest tests.test_source_picker tests.test_wifi_source tests.test_e2e -v` → 74 tests OK; gate estructural sin QTabWidget → PASS.
