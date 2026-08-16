---
phase: 260816-k7i-corregir-hallazgos-pendientes-del-ui-rev
plan: 1
type: execute
subsystem: ui
tags: [ui-review, quick, zombie-code, wizard, confirmations, source-picker]
requires: []
provides: [UI-04, UI-05]
affects: [app/ui/main_window.py, app/ui/source_picker.py, tests/test_wifi_source.py, tests/test_source_picker.py]
tech-stack:
  added: []
  patterns: []
key-files:
  created: []
  modified:
    - app/ui/main_window.py
    - app/ui/source_picker.py
    - tests/test_wifi_source.py
    - tests/test_source_picker.py
decisions:
  - "ProjectWizard reactivado como única vía de creación de proyecto (600x520, callbacks on_finished/on_cancel) en lugar de la ruta directa por defecto"
  - "Confirmaciones destructivas con mensaje de consecuencia real (registros BD vs archivos en disco) y default No para apagado"
  - "«Volcado selectivo…» migrado a Acciones post-ingesta → Operaciones; se conserva el acceso a la carpeta de datos vía el menú de destinos"
  - "Botones zombie (btn_browse_source, btn_receive_wifi) y sus handlers (select_source_path, _update_wifi_button_state) eliminados; WiFi sigue por Añadir origen → WiFi QR"
  - "Gestión de dispositivos guardados migrada del menú Configuración al diálogo Añadir origen: rol ('device', id) en sección Desconectados + menú contextual «Eliminar guardado…» con rama kind=='device' (borra perfil FTP si ftp:)"
  - "Menú Ingesta depurado: retiradas act_pick_source, act_detect_now, act_pick_device, act_devices sin referencias colgantes"
metrics:
  duration: 0
  completed_date: 2026-08-16
status: complete
actuals:
  tokens: 4841
  tasks: 3
  commits: 4
---

# Phase 260816-k7i Plan 1: Corregir hallazgos pendientes del UI-REVIEW

Limpieza del UI según hallazgos del UI-REVIEW: se reactiva el ProjectWizard como única vía de crear proyecto, se corrigen las confirmaciones destructivas, se elimina el código zombie de los menús y se migra la gestión de dispositivos guardados al diálogo unificado «Añadir origen».

## Work Summary

- **Task 1 (d7e1bf9):** `_show_create_project` vuelve a abrir `ProjectWizard` (600×520, callbacks `on_finished`/`on_cancel` → `_on_project_wizard_finished` crea proyecto + sesión inicial y habilita los botones de proyecto). Confirmación de borrado de sesión con consecuencia real; apagado con default `No`.
- **Task 2 (a1e3fda):** Botones zombie eliminados (`btn_browse_source`, `btn_receive_wifi`); `select_source_path`, `_update_wifi_button_state` y `_pick_ftp_source` refactorizada a la cadena del diálogo unificado. «Volcado selectivo…» movido a Acciones post-ingesta → Operaciones.
- **Task 3 (66fa135 RED + 7aa7f98 GREEN):** Migración de tests de guardados a rol `device` y gating de `_open_wifi_panel` (RED con 6 fallos esperados), luego implementación GREEN: `SourcePickerDialog._missing_item` asigna rol `("device", id)` no accionable (OK nunca se habilita, `_accept_current` no-op, menú contextual «Eliminar guardado…»); menú Ingesta depurado (`act_pick_source`, `act_detect_now`, `act_pick_device`, `act_devices` retirados); `_delete_saved_source` con rama `kind == "device"` (confirmación default No, borra perfil FTP si `ftp:`); `_disconnected_devices` incluye dispositivos `ftp:`; `_manage_devices`, `_pick_device_source` y el import `DevicePickerDialog` eliminados sin referencias colgantes.

## Verification

- `python -m unittest tests.test_source_picker tests.test_wifi_source tests.test_source_content tests.test_e2e` → **90 tests, OK** (Qt offscreen).
- Gates estructurales de la Task 3 (14 asserts sobre `main_window.py`/`source_picker.py`) → **ALL GATES PASS**: `act_pick_source`/`act_detect_now`/`act_pick_device`/`act_devices`/`select_source_path`/`_manage_devices`/`_pick_device_source`/`DevicePickerDialog` ausentes; `role[0] == "device"` y `("device", dev["id"])` en source_picker; `kind == "device"` y `did.startswith("ftp:")` en main_window; confirmación con default `No`; sin `act_pick_device.setEnabled`.
- Los 6 tests que fallaban en RED pasan en GREEN (`test_missing_item_*`, `test_delete_device_item_calls_on_delete`, `test_missing_section_lists_devices`, `test_delete_saved_device_*`).
- Nota: ruido de ffprobe en `test_e2e` es esperado (clips falsos sin metadatos reales).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing cleanup] Eliminados `_pick_device_source` y el import `DevicePickerDialog`**
- **Found during:** Task 3 (GREEN)
- **Issue:** El plan retiraba `act_pick_device` y sus `setEnabled`, pero `_pick_device_source` (único handler del action retirado) y el import `from app.ui.device_picker import DevicePickerDialog` quedaban como código zombie sin llamadores — exactamente el patrón que el plan elimina (truth 4/5).
- **Fix:** Borrados `_pick_device_source` (:3109-3129) y el import. `DevicePickerDialog` sigue vivo en `source_picker.py` (diálogo unificado), verificado por grep de referencias en `app/` y `tests/`.
- **Files modified:** `app/ui/main_window.py`
- **Commit:** 7aa7f98

**2. [Rule 2 - Default seguro] Confirmación de borrado de dispositivo con default `No`**
- **Found during:** Task 3 (GREEN)
- **Issue:** El borrado de dispositivo guardado es destructivo (borra sesiones + perfil FTP); sin default seguro el Enter podría borrar por accidente.
- **Fix:** `QMessageBox.question(..., QMessageBox.Yes | QMessageBox.No, QMessageBox.No)` en la rama `kind == "device"` (mismo patrón que remitentes WiFi).
- **Files modified:** `app/ui/main_window.py`
- **Commit:** 7aa7f98

### Auth Gates

Ninguno.

## Decisions Made

- **ProjectWizard es la única vía de creación de proyecto** (restaura el comportamiento previo al fix 2 del UI-REVIEW); el dashboard selecciona el nuevo proyecto y habilita los botones.
- **Gestión de dispositivos guardados vive en «Añadir origen»** (sección Desconectados + menú contextual «Eliminar guardado…») — sustituye a «Configuración → Dispositivos guardados» sin perder capacidad de borrado (incluido FTP via `delete_ftp_profile`).
- **Los ítems `device` son no-accionables**: nunca habilitan OK ni se aceptan (doble clic/Enter no-op); solo borrado vía menú contextual. `_accept_item` también protegido por defensa en profundidad (T-260816-04).
- **`_disconnected_devices` incluye `ftp:`**: los perfiles FTP con sesiones se listan siempre (no hay forma fiable de saber si el servidor está "desconectado"), para que sigan siendo borrables.

## Known Stubs

Ninguno. Todos los flujos están cableados (proyecto → sesión inicial, WiFi → WifiMethodDialog, borrado device → db + FTP profile).

## Threat Flags

Ninguno. La superficie de red no cambia (sin endpoints nuevos); solo se retiran menús y se mueve el borrado de dispositivos al diálogo unificado, sin nuevas rutas de confianza.

## Self-Check: PASSED

- `app/ui/main_window.py` existe, `app/ui/source_picker.py` existe, `tests/test_wifi_source.py` existe, `tests/test_source_picker.py` existe.
- Commits verificados en `git log`: `7aa7f98`, `66fa135`, `a1e3fda`, `d7e1bf9`.
- 90/90 tests OK; gates estructurales OK.
