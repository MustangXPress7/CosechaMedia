---
phase: quick-260908-f5o
plan: 01
subsystem: ui
tags: [camera-mixin, add-source-dialog, QSettings, device-registry, usb]

# Dependency graph
requires:
  - phase: quick-260906-fgl
    provides: CameraMixin with _prompt_rename_camera and _persist_camera_mapping
  - phase: 01.6.0
    provides: known_devices table + usb_device_id normalization + get_dispositivo_for_device
provides:
  - Persistent camera rename via double-click (device_settings + known_devices, not just session)
  - Configurable confirm popup (Yes/No/Discard) with "No volver a preguntar" persisted in QSettings
  - USB known-name auto-fill in Add Source dialog (mirrors existing MTP behavior)
affects: [add-source-dialog, camera-mixin, sources-mixin, devices-mixin]

# Actuals (#2632) — chars/4 over the realized diff of the 4 task commits
actuals:
  tokens: 11840
  tasks: 2
  commits: 5

# Tech tracking
tech-stack:
  added: []
  patterns:
    - QSettings boolean gate (camera/skip_rename_confirm) to suppress a confirm popup after user chooses "Discard"
    - USB camera name lookup mirrors MTP lookup: db.get_dispositivo_for_device(usb_device_id(path)) before defaulting

key-files:
  created:
    - tests/test_camera_mixin.py
  modified:
    - app/ui/mixins/camera_mixin.py
    - app/ui/add_source_dialog.py
    - tests/test_add_source_dialog.py

key-decisions:
  - "Discard ('No volver a preguntar') both persists globally AND sets the QSettings skip flag (matches plan spec: update_session_config + _persist_camera_mapping + setValue)"
  - "USB prefill applied in both _populate (usb_connected path) and _refresh_physical_section (Detectar path) — root-cause consistency, not just the plan's line 724-736 block"
  - "Empty/whitespace rename early-returns before updating session config (plan behavior 5: no persistence at all)"

patterns-established:
  - "USB rows in Add Source consult known device name exactly like MTP rows before falling back to 'Sin nombre'"

requirements-completed: [I-03, I-14, REQ-09]

coverage:
  - id: D1
    description: "Double-click rename persists device name globally (device_settings + known_devices) when user confirms Yes or Discard"
    requirement: I-03
    verification:
      - kind: unit
        ref: "tests/test_camera_mixin.py#test_yes_persists_globally"
        status: pass
      - kind: unit
        ref: "tests/test_camera_mixin.py#test_discard_sets_skip_flag_and_persists"
        status: pass
    human_judgment: false
  - id: D2
    description: "Confirm popup with Yes/No/Discard; Discard sets QSettings camera/skip_rename_confirm and subsequent renames skip the popup while persisting directly"
    requirement: I-14
    verification:
      - kind: unit
        ref: "tests/test_camera_mixin.py#test_discard_sets_skip_flag_and_persists"
        status: pass
      - kind: unit
        ref: "tests/test_camera_mixin.py#test_skip_flag_bypasses_popup"
        status: pass
    human_judgment: false
  - id: D3
    description: "Empty rename does not persist anything (early return)"
    verification:
      - kind: unit
        ref: "tests/test_camera_mixin.py#test_empty_name_persists_nothing"
        status: pass
    human_judgment: false
  - id: D4
    description: "USB rows in Add Source pre-fill known camera name from device_settings/known_devices via usb_device_id(path)"
    requirement: REQ-09
    verification:
      - kind: unit
        ref: "tests/test_add_source_dialog.py#test_usb_known_name_prefills_combo"
        status: pass
      - kind: unit
        ref: "tests/test_add_source_dialog.py#test_usb_known_name_prefills_after_detect"
        status: pass
    human_judgment: false
  - id: D5
    description: "USB row without known name keeps 'Sin nombre'"
    verification:
      - kind: unit
        ref: "tests/test_add_source_dialog.py#test_usb_unknown_keeps_sin_nombre"
        status: pass
    human_judgment: false

# Metrics
duration: 24min
completed: 2026-09-08
status: complete
---

# Quick 260908-f5o: Renombrar dispositivo en la tabla de orígenes — Summary

**Rename por doble clic ahora persiste en el registro global (device_settings + known_devices) con popup configurable Yes/No/«No volver a preguntar» (QSettings), y las filas USB de Añadir origen auto-rellenan el nombre conocido como ya hacía MTP**

## Performance

- **Duration:** 24 min
- **Started:** 2026-09-08T09:22:41Z
- **Completed:** 2026-09-08T09:46:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- `_prompt_rename_camera` persiste en registro global vía `_persist_camera_mapping` cuando el usuario elige «Sí» o «No volver a preguntar» (antes solo `update_session_config` — se perdía entre sesiones/proyectos)
- Popup `QMessageBox.question` con 3 botones (Yes/No/Discard) tras el InputDialog; el flag `camera/skip_rename_confirm` en QSettings suprime el popup en sucesivos renames y persiste directamente
- Filas USB en Añadir origen consultan `db.get_dispositivo_for_device(usb_device_id(path))` en ambas rutas (`_populate` por usb_connected y `_refresh_physical_section` por «Detectar»), mostrando el nombre conocido en lugar de «Sin nombre»
- Import de `usb_device_id` añadido en add_source_dialog.py — ya se usaba en línea 732 sin import (NameError latente tragado por try/except, de quick 260907-fb2 pendiente)
- Suite de 58 tests (test_camera_mixin + test_add_source_dialog) pasa; test_usb_identity.py pasa

## Task Commits

Cada tarea se commiteó atómicamente (TDD: test → feat):

1. **Task 1: Persistir rename en registro global + popup de confirmación**
   - `8c589e7` (test: RED — tests failing para _prompt_rename_camera)
   - `88e456e` (feat: GREEN — popup + persistencia global + flag QSettings)
   - `fe23bf6` (test: default QSettings skip-flag mock a False — fix de test para que los mocks de QMessageBox no devuelvan truthy por defecto)
2. **Task 2: Auto-fill nombre conocido para USB en Añadir origen**
   - `3b3bcfd` (test: RED — tests failing para prefill USB)
   - `865f373` (feat: GREEN — prefill USB en _populate + _refresh_physical_section + import usb_device_id)

**Plan metadata:** docs commit gestionado por el orquestador (no incluido aquí)

## Files Created/Modified
- `app/ui/mixins/camera_mixin.py` - `_prompt_rename_camera` reescrito: skip-flag QSettings, popup Yes/No/Discard, persistencia global condicional, early return en nombre vacío
- `app/ui/add_source_dialog.py` - import `usb_device_id`; prefill de nombre conocido en bloques USB de `_populate` y `_refresh_physical_section`; upsert known_devices de USB usa el nombre resuelto
- `tests/test_camera_mixin.py` - nuevo: 5 tests de `TestPromptRenameCamera` (harness de mixin con db mockeado)
- `tests/test_add_source_dialog.py` - 3 tests nuevos USB (known prefill construcción, known prefill tras Detectar, unknown mantiene Sin nombre)

## Decisions Made
- «No volver a preguntar» (Discard) persiste globalmente Y activa el flag — coincide con la spec del plan (update_session_config + _persist_camera_mapping + setValue)
- Prefill USB aplicado en ambas rutas de creación de fila (construcción y Detectar) para consistencia root-cause, no solo el bloque 724-736 del plan
- Nombre vacío: early return sin tocar la sesión (comportamiento 5 del plan: «no persiste nada»)
- Flag QSettings escrito con constructor explícito `QSettings("Audiovisual Production", "CosechaMedia")` — consistente con el resto del codebase

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Import de `usb_device_id` ausente en add_source_dialog.py**
- **Found during:** Task 2 (implicaba tocar el bloque USB)
- **Issue:** La línea 732 ya llamaba `usb_device_id(drive_path)` (introducida por cambios sin commitear de quick 260907-fb2) sin importarla; el NameError resultante quedaba tragado por el try/except que rodea el upsert de known_devices — el upsert USB nunca funcionaba en runtime.
- **Fix:** Añadido `usb_device_id` al import de `app.core.db` en el módulo.
- **Files modified:** app/ui/add_source_dialog.py
- **Verification:** Los 3 tests USB nuevos pasan y ejercitan el lookup con mock de `dlgmod.usb_device_id`; test_usb_identity.py sigue pasando.
- **Committed in:** 865f373 (Task 2 commit)

**2. [Rule 1 - Bug] Prefill USB solo en `_refresh_physical_section` dejaría la ruta `usb_connected` (construcción) sin nombre conocido**
- **Found during:** Task 2
- **Issue:** El plan apuntaba solo al bloque 724-736 (`_refresh_physical_section`), pero el flujo primario «Añadir origen» crea filas USB vía `_populate` con `usb_connected` — quedarían con «Sin nombre» aunque el dispositivo fuera conocido.
- **Fix:** Aplicada la misma consulta en ambos bloques USB (root-cause, no parche localizado).
- **Files modified:** app/ui/add_source_dialog.py
- **Verification:** test_usb_known_name_prefills_combo (ruta usb_connected) y test_usb_known_name_prefills_after_detect (ruta Detectar) ambos pasan.
- **Committed in:** 865f373 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 missing critical, 1 bug)
**Impact on plan:** Correcciones necesarias para que el feature funcione en todas las rutas de entrada. Sin scope creep.

## Issues Encountered

- **Test pre-existente roto (out of scope):** `tests/test_main_window.py::TestRenameDialogPersistence::test_rename_in_dialog_ftp_prefix` falla con `'QLineEdit' object has no attribute 'setEditText'` — causado por los cambios sin commitear previos en `app/ui/add_source_dialog.py` (cambio readonly FTP de quick 260907-fb2 pendiente), no por este quick task. Registrado en `deferred-items.md` del directorio de la tarea.
- **Edición de import colateral:** mi primera edición del import `from app.core.db import db` golpeó el import local en `_known_camera_names` en lugar del top-level (ambos coinciden textualmente); detectado por IndentationError al correr pytest y corregido restaurando ambos imports. Fix-at-failure dentro del mismo ciclo RED/GREEN, sin commit extra.

## Known Stubs

None — no stubs introducidos. Los placeholders «Sin nombre»/«Detectando…» de add_source_dialog.py son validaciones pre-existentes intencionales.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| | | Ninguna superficie nueva: el flag QSettings `camera/skip_rename_confirm` es local (T-260908-f5o-01 aceptado); la escritura de nombres sigue pasando por `save_dispositivo_config`/`upsert_known_device` que sanitizan en la capa de datos |

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Listo para verificar manualmente: doble clic en cámara en tabla → popup 3 botones → «Sí» → nombre visible en Añadir origen al próximo launch; «No volver a preguntar» → sin popup en siguientes renames
- El commit del orquestador (docs) debe incluir el resumen + STATE.md
- Blocker pendiente no relacionado: los cambios sin commitear de quick 260907-fb2 en device_registry.py/sources_mixin.py/db.py quedan intactos fuera del scope de esta tarea

---
*Phase: quick-260908-f5o*
*Completed: 2026-09-08*

## Self-Check: PASSED

- FOUND: app/ui/mixins/camera_mixin.py
- FOUND: app/ui/add_source_dialog.py
- FOUND: tests/test_camera_mixin.py
- FOUND: tests/test_add_source_dialog.py
- FOUND: .planning/quick/260908-f5o-renombrar-dispositivo-en-la-tabla-de-or-/260908-f5o-SUMMARY.md
- FOUND commits: 8c589e7 (RED cam), 88e456e (GREEN cam), fe23bf6 (test QSettings mock fix), 3b3bcfd (RED asd), 865f373 (GREEN asd)