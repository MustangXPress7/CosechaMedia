---
phase: 260816-k7i-corregir-hallazgos-pendientes-del-ui-rev
plan: 1
subsystem: ui
tags: [pyside6, qdialog, source-picker, main-window, wizard, i18n-es]

# Dependency graph
requires:
  - phase: 01-auditor-a-ui-y-plan-de-reubicaci-n
    provides: hallazgos UI-REVIEW (fix 2/3, items 3-5), decisiones D-03/D-09/D-12, UI-SPEC §185/§186/§198
provides:
  - ProjectWizard reactivado en «Nuevo Proyecto» (proyecto + sesión inicial + selección + botones habilitados)
  - Confirmaciones destructivas veraces (borrar sesión: «registros de ingesta», archivos se conservan; apagado default No)
  - btn_selective_dump movido a Acciones post-ingesta → Operaciones
  - Botones zombie (btn_browse_source/btn_receive_wifi) y sus callers eliminados; cadena WiFi intacta vía Añadir origen → WiFi QR
  - Menú Ingesta/Configuración limpio; gestión de guardados (MTP+FTP) migrada al diálogo Añadir origen con rol ("device", id)
  - Guard de rol en _accept_item/_set_from_item: el doble clic en «Desconectados» nunca acepta ni muta kind/value (regresión k7i corregida)
affects: [01-auditor-a-ui-y-plan-de-reubicaci-n, verify-work, ui-review]

actuals:
  tokens: 8299
  tasks: 3
  commits: 6

tech-stack:
  added: []
  patterns:
    - "Rol Qt.UserRole ("device", id) en ítems no-accionables del picker unificado: porta capacidad de borrado sin habilitar OK ni aceptar el diálogo."
    - "Guard de rol idéntico en _update_ok_state/_accept_current/_accept_item/_set_from_item: un ítem no-accionable nunca muta kind/value ni acepta (T-260816-04)."

key-files:
  created: []
  modified:
    - app/ui/main_window.py
    - app/ui/source_picker.py
    - tests/test_wifi_source.py
    - tests/test_source_picker.py

key-decisions:
  - "Guard de rol también en _accept_item/_set_from_item (vía doble clic), no solo en _accept_current/_update_ok_state — defensa en profundidad para el contrato no-accionable (T-260816-04)."
  - "La vía legítima kind='device' (DevicePickerDialog → tupla de 3) se conserva intacta: el guard solo aplica al rol de ítem ("device", id), nunca a _pick_device."

patterns-established:
  - "Un ítem de lista no-accionable con rol porta metadatos de gestión (borrado) pero queda excluido de TODAS las vías de aceptación/mutación del diálogo."

requirements-completed: [UI-04, UI-05]

coverage:
  - id: D1
    description: "«Nuevo Proyecto» abre ProjectWizard modal (600×520); al confirmar crea proyecto + sesión inicial, selecciona el proyecto en el combo y habilita los botones de gestión; cancelar no crea nada."
    requirement: UI-04
    verification:
      - kind: e2e
        ref: "tests/test_e2e.py (MainWindow arranca tras el rewire)"
        status: pass
      - kind: other
        ref: "spot-check runtime offscreen (proyecto+sesión+combo+botones, cancel limpio) — ver 260816-k7i-VERIFICATION.md truth 1"
        status: pass
    human_judgment: true
    rationale: "La modalidad y apariencia visual del wizard requieren ojos humanos (verificado por spot-check automático + código)."
  - id: D2
    description: "Confirmaciones destructivas veraces: borrar sesión declara «registros de ingesta» (archivos en disco se conservan) y apagado con default No."
    requirement: UI-05
    verification:
      - kind: e2e
        ref: "tests/test_e2e.py"
        status: pass
      - kind: other
        ref: "gates estructurales (asserts de texto y default) — VERIFICATION.md truth 2"
        status: pass
    human_judgment: false
  - id: D3
    description: "«Volcado selectivo…» vive en Acciones post-ingesta → Operaciones y sigue abriendo el asistente."
    requirement: UI-04
    verification:
      - kind: automated_ui
        ref: "tests/test_source_content.py#test_selective_dump_button_present"
        status: pass
    human_judgment: true
    rationale: "La posición en el layout se verificó por código (op_row); la presentación visual es humana (UI-05)."
  - id: D4
    description: "Sin botones ocultos ni su lógica (btn_browse_source/btn_receive_wifi/select_source_path/_update_wifi_button_state); el WiFi entra por Añadir origen → WiFi QR → WifiMethodDialog."
    requirement: UI-04
    verification:
      - kind: automated_ui
        ref: "tests/test_wifi_source.py#test_open_wifi_panel_with_project_starts_server"
        status: pass
      - kind: automated_ui
        ref: "tests/test_wifi_source.py#test_open_wifi_panel_without_project_is_noop"
        status: pass
      - kind: other
        ref: "grep de ausencia de símbolos zombie — VERIFICATION.md truth 4"
        status: pass
    human_judgment: false
  - id: D5
    description: "Gestión de dispositivos guardados migrada al diálogo Añadir origen (sección Desconectados + menú contextual «Eliminar guardado…»), MTP y FTP, con confirmación veraz y default No; el doble clic en «Desconectados» nunca acepta ni muta kind/value."
    requirement: UI-04
    verification:
      - kind: automated_ui
        ref: "tests/test_source_picker.py#test_missing_item_carries_device_role"
        status: pass
      - kind: automated_ui
        ref: "tests/test_source_picker.py#test_accept_item_noop_for_missing_device"
        status: pass
      - kind: automated_ui
        ref: "tests/test_source_picker.py#test_double_click_missing_item_does_not_accept"
        status: pass
      - kind: automated_ui
        ref: "tests/test_source_picker.py#test_delete_device_item_calls_on_delete"
        status: pass
      - kind: automated_ui
        ref: "tests/test_wifi_source.py (rama device de _delete_saved_source, incl. ftp:)"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-08-16
status: complete
---

# Quick k7i: Corregir hallazgos pendientes del UI-REVIEW — Summary

**ProjectWizard reactivado en creación de proyecto, confirmaciones destructivas veraces (default No), volcado selectivo movido a Operaciones, botones zombie eliminados, menú limpio con gestión de guardados (MTP/FTP) migrada al diálogo Añadir origen, y guard de rol en `_accept_item`/`_set_from_item` que corrige la regresión del doble clic en «Desconectados»**

## Performance

- **Duration:** ~20 min (gap fix: ~8 min; tasks 1-3: ~12 min previos)
- **Started:** 2026-08-16
- **Completed:** 2026-08-16
- **Tasks:** 3 (+1 gap fix de verificación)
- **Files modified:** 4

## Accomplishments
- «Nuevo Proyecto» pasa por ProjectWizard (modal 600×520): proyecto + sesión inicial, selección en combo y botones habilitados al confirmar; cancel sin efectos (fix 2).
- Borrar sesión declara la consecuencia real («registros de ingesta», archivos en disco se conservan) y el apagado pregunta con default No (fix 3, D-09).
- «Volcado selectivo…» movido a Acciones post-ingesta → Operaciones, sin cambiar su nombre ni su slot (item 3, UI-SPEC §198).
- Botones zombie `btn_browse_source`/`btn_receive_wifi` y `_update_wifi_button_state`/`select_source_path` eliminados sin referencias colgantes; la cadena WiFi (Añadir origen → WiFi QR → WifiMethodDialog) queda intacta (item 4, D-03).
- Menú Ingesta/Configuración sin entradas duplicadas; gestión de guardados (MTP y FTP) migrada al diálogo unificado con rol `("device", id)` y borrado contextual con confirmación veraz default No (item 5, D-12).
- **Regresión k7i corregida:** `_accept_item` y `_set_from_item` ahora portan el guard de rol de `_accept_current` — el doble clic en un ítem «Desconectados» no acepta el diálogo ni muta kind/value, cerrando el `ValueError` en `_apply_source_choice` (T-260816-04 completa).

## Task Commits

Cada tarea se commiteó atómicamente:

1. **Task 1: ProjectWizard + confirmaciones destructivas** - `d7e1bf9` (fix)
2. **Task 2: Botones zombie y volcado selectivo** - `a1e3fda` (fix)
3. **Task 3: Menú limpio + gestión de guardados (RED/GREEN)** - `66fa135` (test), `7aa7f98` (fix)
4. **Gap fix (verificación k7i): guard de rol en `_accept_item`** - `5d970b3` (fix)

**Plan metadata:** `2d0f212` (docs: complete plan)

## Files Created/Modified
- `app/ui/main_window.py` - Wizard rewire (`_show_create_project` → `_on_project_wizard_finished`/`_close_project_wizard`), copy veraz de borrado de sesión, apagado default No, `btn_selective_dump` en op_row, zombies y acciones de menú retiradas, rama `kind == "device"` en `_delete_saved_source`, `_disconnected_devices` incluye `ftp:`
- `app/ui/source_picker.py` - `_missing_item` porta rol `("device", id)`; guard de rol en `_update_ok_state`/`_accept_current`/`_accept_item`/`_set_from_item`; menú contextual «Eliminar guardado…»
- `tests/test_wifi_source.py` - gating de `_open_wifi_panel` (con/sin proyecto), rama device de `_delete_saved_source` (incl. `ftp:`)
- `tests/test_source_picker.py` - helper `_missing_item` migrado a `role[0] == "device"`; Test 1 (rol no accionable), Test 2 (borrado vía on_delete), y **tests de regresión del doble clic** (`test_accept_item_noop_for_missing_device`, `test_double_click_missing_item_does_not_accept`)

## Decisions Made
- Guard de rol también en `_accept_item`/`_set_from_item` (vía doble clic), no solo en `_accept_current`/`_update_ok_state` — defensa en profundidad para el contrato no-accionable (T-260816-04).
- La vía legítima `kind == "device"` (DevicePickerDialog → tupla de 3) se conserva intacta: el guard solo aplica al rol de ítem `("device", id)`, nunca a `_pick_device`.
- Borrado de guardados con copy veraz y default No (coherente con D-09 y con el fix 3b).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Regresión de doble clic en ítems «Desconectados» (hallada por el verificador)**
- **Found during:** Verificación de quick k7i (truth 5, T-260816-04 incompleta)
- **Issue:** El rol `("device", id)` añadido a `_missing_item` (Task 3) activó la vía `_accept_item` (itemDoubleClicked): el doble clic en «Desconectados» mutaba kind/value a `("device", <id-crudo>)` y aceptaba el diálogo; `_apply_source_choice` desempaquetaba `device_id, device_folder, device_name = value` y lanzaba `ValueError: too many values to unpack`. El guard de T-260816-04 solo cubría `_update_ok_state`/`_accept_current`; el SUMMARY previo afirmaba defensa en profundidad en `_accept_item` que no existía. Regresión: sin rol, `_accept_item` era no-op.
- **Fix:** Guard idéntico al de `_accept_current` al inicio de `_accept_item` (no acepta el diálogo) y en `_set_from_item` (no muta kind/value). Tests de regresión por ambas vías: llamada directa a `_accept_item` y evento real de doble clic sobre un ítem «Desconectados» (diálogo no acepta, kind/value quedan None, `_apply_source_choice` nunca recibe `("device", <raw-id>)`).
- **Files modified:** app/ui/source_picker.py, tests/test_source_picker.py
- **Verification:** `python -m unittest tests.test_source_picker tests.test_e2e tests.test_wifi_source tests.test_source_content -v` → 92 tests OK (90 previos + 2 nuevos); reproducción del verificador ahora no acepta el diálogo.
- **Committed in:** 5d970b3 (gap fix)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Corrección quirúrgica del contrato no-accionable; sin cambio de superficie. No scope creep.

## Issues Encountered
- Ninguno adicional: la suite completa (92 tests) pasa en Qt offscreen; el ruido de ffprobe en test_e2e es esperado (entorno sin ffmpeg).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Flujo «Nuevo Proyecto», confirmaciones, volcado selectivo, menú y gestión de guardados listos; pendientes solo los 3 ítems de verificación humana del verificador (apariencia del wizard, posición visual del botón, cadena WiFi real con QR) recogidos en `260816-k7i-VERIFICATION.md` → Human Verification.

## Self-Check: PASSED

- FOUND: `.planning/quick/260816-k7i-corregir-hallazgos-pendientes-del-ui-rev/260816-k7i-SUMMARY.md`
- FOUND: `app/ui/source_picker.py`
- FOUND: `tests/test_source_picker.py`
- FOUND: commit `5d970b3` (guard de rol en `_accept_item` para filas Desconectados)
- Suite: `python -m unittest tests.test_source_picker tests.test_e2e tests.test_wifi_source tests.test_source_content -v` → 92 tests OK

---
*Phase: 260816-k7i-corregir-hallazgos-pendientes-del-ui-rev*
*Completed: 2026-08-16*

