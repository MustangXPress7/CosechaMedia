---
phase: 260816-k7i-corregir-hallazgos-pendientes-del-ui-rev
verified: 2026-08-16T16:00:00Z
status: gaps_found
score: 5/6 must-haves verified
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "La gestión de dispositivos guardados se ejerce desde el diálogo Añadir origen (sección Desconectados + menú contextual «Eliminar guardado…») — los ítems «Desconectados» son informativos no-accionables (nunca mutan kind/value ni aceptan el diálogo) sin perder la capacidad de borrado."
    status: failed
    reason: "Un doble clic sobre un ítem «Desconectados» llega a `_accept_item` (handler de itemDoubleClicked, SIN guard de rol), que muta kind/value a ('device', <id>) y acepta el diálogo; `_apply_source_choice` (rama kind=='device') desempaqueta `value` como tupla de 3 y lanza ValueError. La mitigación T-260816-04 del plan ('un ítem no-accionable nunca habilita OK ni muta kind/value') está aplicada solo en `_update_ok_state` y `_accept_current`, no en `_accept_item`/`_set_from_item`; la afirmación del SUMMARY ('_accept_item también protegido por defensa en profundidad') es falsa. Es una regresión: antes del plan los ítems no tenían rol y `_accept_item` era no-op."
    artifacts:
      - path: "app/ui/source_picker.py"
        issue: "_accept_item (líneas 224-227) y _set_from_item (229-232) no tienen guard para rol ('device', ...); un doble clic en un ítem Desconectados acepta el diálogo con kind='device' y value=<id-string>."
      - path: "app/ui/main_window.py"
        issue: "_apply_source_choice rama kind=='device' (línea 2762-2765) desempaqueta `device_id, device_folder, device_name = value`; recibe el id en crudo (string) vía doble clic → ValueError (demostrado en runtime offscreen)."
    missing:
      - "Añadir a `_accept_item` (o `_set_from_item`) el mismo guard de `_accept_current`: `if role is not None and role[0] == 'device': return` — para que el doble clic nunca mute kind/value ni acepte."
      - "Test de regresión: `_accept_item` sobre un ítem «Desconectados» no acepta el diálogo ni muta kind/value (análogo a test_missing_item_carries_device_role pero por la vía del doble clic)."
human_verification:
  - test: "Abrir la app y pulsar «Nuevo Proyecto»: comprobar que se abre el ProjectWizard (modal, 600×520 con nombre/descripción/destino/duración/organización/fecha-metadatos) y que al confirmar se crea proyecto + sesión inicial, el combo selecciona el proyecto y los botones de gestión se habilitan; cancelar no crea nada."
    expected: "Flujo completo del wizard visible y operativo (verificación visual + funcional)."
    why_human: "El comportamiento se verificó por spot-check automático (crea proyecto+sesión, selecciona combo, habilita botones, cancel limpio) pero la apariencia visual del wizard y su modalidad requieren ojos humanos."
  - test: "Verificar visualmente que «Volcado selectivo…» aparece dentro de Acciones post-ingesta → Operaciones (junto a Reorganizar/Limpiar completados), no en la fila de escaneo."
    expected: "Botón presente en el grupo Operaciones, clickable, abre el asistente de volcado selectivo."
    why_human: "La posición en el layout se verificó por código (op_row), pero la presentación visual es humana (UI-05)."
  - test: "Comprobar la cadena WiFi: «Añadir origen… → WiFi QR» abre el panel QR y el flujo PairDrop sigue operativo."
    expected: "El diálogo unificado abre WifiMethodDialog → panel WiFi (el cableado se verificó por grep: _apply_source_choice → _pick_wifi_source → WifiMethodDialog; los tests de gating de _open_wifi_panel pasan)."
    why_human: "El panel QR real (QR renderizado, conexión de dispositivos) requiere interacción real (UI-05)."
---

# Quick k7i: Corregir hallazgos pendientes del UI-REVIEW — Verification Report

**Task Goal:** Corregir hallazgos pendientes del UI-REVIEW en main_window.py: (1) fix 2 — ProjectWizard huérfano, rewire a ProjectWizard; (2) fix 3 — copy falsa 'y todos sus archivos' al borrar sesión + apagado con default Yes → default No; (3) mover btn_selective_dump de la fila de escaneo al grupo 'Acciones post-ingesta > Operaciones'; (4) eliminar botones zombie ocultos btn_browse_source y btn_receive_wifi con su lógica cableada y migración de tests; (5) limpiar entradas redundantes del menú Ingesta y la gestión 'Dispositivos guardados'.
**Verified:** 2026-08-16
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Crear proyecto pasa por ProjectWizard (600×520); al confirmar crea proyecto + sesión inicial, el dashboard selecciona y habilita los botones de proyecto | ✓ VERIFIED | `_show_create_project` (:1195) importa `ProjectWizard`, callbacks on_finished/on_cancel, `setWindowModality(Qt.ApplicationModal)` + `show()`, ref persistente. `_on_project_wizard_finished` (:1205) crea sesión inicial, `load_existing_projects` + `project_combo.findData/setCurrentIndex`, habilita btn_delete/rename/duplicate, `update_start_button_state`, cierra wizard. **Spot-check runtime offscreen PASS:** proyecto creado, sesión «Sesión 1 - X» status active, combo == pid, botones True, cancel sin efectos. Wizard 600×520 (`setMinimumWidth(600)/setMinimumHeight(520)`, project_wizard.py:19-20); `finish_wizard` valida nombre+destino (:129) y llama `on_finished_callback(project_id)` (:166) |
| 2 | El diálogo de borrar sesión declara la consecuencia real (registros de ingesta; archivos en disco se conservan) y el apagado pregunta con default No | ✓ VERIFIED | `_delete_current_session` (:2510-2521): «¿Eliminar la sesión #%1 y sus registros de ingesta?\nLos archivos en disco se conservan.\nEsta acción no se puede deshacer.» con default `QMessageBox.No`; `db.delete_session` (db.py:544) solo borra filas de BD. `_shutdown_computer` (:1860-1864): `QMessageBox.Yes | QMessageBox.No, QMessageBox.No`. Gate: «todos sus archivos» ausente de main_window.py |
| 3 | «Volcado selectivo…» vive en Acciones post-ingesta → Operaciones y sigue abriendo el asistente | ✓ VERIFIED | `self.btn_selective_dump` definido en `op_row` (:637-640), después de `btn_clear_completed` (:635) y antes de `op_row.addStretch()` (:642); `clicked → _open_selective_dump`; fuera de la fila de escaneo (`src_scan_row.addWidget(self.btn_selective_dump` ausente). test_source_content.test_selective_dump_button_present pasa (hasattr + click) |
| 4 | No existen botones ocultos ni su lógica: btn_browse_source, btn_receive_wifi, select_source_path y _update_wifi_button_state desaparecen; el WiFi sigue por Añadir origen → WiFi QR → WifiMethodDialog | ✓ VERIFIED | Grep en app/ui/main_window.py: 0 matches de `btn_browse_source`, `btn_receive_wifi`, `select_source_path`, `_update_wifi_button_state` (8 call sites retirados). Cadena intacta: `_apply_source_choice` kind "wifi" (:2770-2771) → `_pick_wifi_source` (:3038) → `WifiMethodDialog` → `_open_wifi_panel`. `_stage_device_in_background`/`_on_stage_done` sin refs colgantes |
| 5 | El menú Ingesta conserva solo entradas no duplicadas; la gestión de dispositivos guardados se ejerce desde el diálogo Añadir origen (sección Desconectados + menú contextual «Eliminar guardado…») sin perder la capacidad de borrado | ✗ FAILED (partial) | Menú Ingesta (:2608-2638): solo `act_pick_dest`, `act_auto_detect`, `act_detect_sd`, `act_dump_targets`, `act_open_data`; Configuración sin `act_devices`. `_delete_saved_source` rama kind=="device" (:2844-2862) con confirmación veraz default No, `db.delete_ftp_profile` si `ftp:`, `db.delete_device`, refrescos; `_disconnected_devices` incluye `ftp:`; tests de borrado (confirmado/rechazado/FTP) pasan. **PERO:** doble clic en ítem «Desconectados» → `_accept_item` (sin guard) acepta el diálogo con kind="device", value=<id-string> → `_apply_source_choice` lanza ValueError (reproducido en runtime offscreen con el diálogo real). La mitigación T-260816-04 está incompleta y el SUMMARY afirma defensa en profundidad en `_accept_item` que no existe. **Regresión:** antes del plan el ítem no tenía rol (no-op); el rol añadido activa la vía rota |
| 6 | test_source_picker, test_wifi_source, test_source_content y test_e2e pasan en Qt offscreen | ✓ VERIFIED | `python -m unittest tests.test_source_picker tests.test_wifi_source tests.test_source_content tests.test_e2e` → **90 tests, OK** (ruido ffprobe esperado en e2e). Gates estructurales (Tareas 1-3, asserts de ausencia/presencia/defaults) → **ALL PASS** |

**Score:** 5/6 truths verified (1 behaviorally failed — truth 5)

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `app/ui/main_window.py` | Wizard rewire, confirmaciones, botón movido, zombies y menú limpio | ✓ VERIFIED | Presente y sustantivo; véase truth 1-5. Único defecto: `_apply_source_choice` kind "device" desempaqueta 3-tupla y puede recibir string (gap de truth 5) |
| `app/ui/source_picker.py` | Rol ("device", id) no-accionable en Desconectados + menú contextual «Eliminar guardado…» | ✗ STUB-like guard | `_missing_item` (:194-201) porta rol; `_update_ok_state` (:113-119) y `_accept_current` (:122-130) con guard; **`_accept_item` (:224-227) y `_set_from_item` (:229-232) SIN guard** — la vía doble clic acepta y muta kind/value |
| `tests/test_wifi_source.py` | Tests migrados: gating `_open_wifi_panel`, rama device de `_delete_saved_source` (incl. ftp:) | ✓ VERIFIED | :96-107 gating con/sin proyecto (mocks del setUp); :109-157 borrado device confirmado/rechazado/ftp-profile; docstring :7 actualizado |
| `tests/test_source_picker.py` | Helper `_missing_item` migrado a role[0]=="device"; Test 1 y Test 2 | ✓ VERIFIED | Helper :71-77; `test_missing_item_does_not_enable_ok` :126-137; `test_missing_item_carries_device_role` :139-153; `test_delete_device_item_calls_on_delete` :155-168; comentario :93-95 actualizado |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| `_show_create_project` | `ProjectWizard` → `_on_project_wizard_finished` | callbacks on_finished/on_cancel + `_close_project_wizard` | ✓ WIRED | :1198-1203, :1205-1234; verificado por spot-check runtime (proyecto+sesión+combo+botones, cancel limpio) |
| `_delete_current_session` | `db.delete_session` | copy veraz + default No | ✓ WIRED | :2514-2524; db.py:544 borra solo registros de BD |
| `btn_add_source` → `_pick_source_entry` | `SourcePickerDialog` kind "wifi" → `_apply_source_choice` → `_pick_wifi_source` | :2796-2798, :2770-2771, :3038-3047 | ✓ WIRED | Cadena WiFi intacta tras quitar el botón zombie; `_pick_wifi_source` conservado con tests (:736-753 preexistentes) |
| `SourcePickerDialog._missing_item` role ("device", id) | `on_delete` → `_delete_saved_source` kind "device" → `db.delete_device` (+ `db.delete_ftp_profile` si ftp:) | :198, :2798, :2844-2862; ftp.py:73 `profile_id_from_device_key` | ✓ WIRED (vía borrado) / ✗ BROKEN (vía doble clic) | Borrado por menú contextual funciona y está testeado; la vía `_accept_item` (doble clic) rompe el contrato no-accionable → ValueError en `_apply_source_choice` |
| `build_menu` acciones retiradas | sin referencias colgantes en `_stage_device_in_background`/`_on_stage_done` | :3444-3488 | ✓ WIRED | 0 matches de act_pick_source/act_detect_now/act_pick_device/act_devices; sin `setEnabled` colgantes |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `_missing_item` → `_accept_item` → `accept()` → `_apply_source_choice` | kind/value ("device", id-string) | role del picker | ✗ CRASH — `device_id, device_folder, device_name = value` desempaqueta el id-string → ValueError | ✗ BROKEN (doble clic) |
| `_missing_item` → `_show_item_menu` → `_delete_selected` → `_delete_saved_source` kind "device" | kind/value ("device", dev_id) | role del picker | ✓ borra `db.delete_device` (+ `db.delete_ftp_profile`) | ✓ FLOWING (menú contextual) |
| `_on_project_wizard_finished` → `db.create_session` | project_id del INSERT del wizard | `finish_wizard` (:137-166) | ✓ sesión «Sesión 1 - {name}» status active; combo findData/setCurrentIndex | ✓ FLOWING (spot-check runtime) |
| `_disconnected_devices` → `devices_missing` | ids MTP desconectados + ftp: | `db.get_sessions` + `mtp.WpdBackend().list_devices()` | ✓ sección Desconectados lista MTP y FTP (wifi: excluido) | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Flujo wizard completo (crear → confirmar → dashboard) | script offscreen: `_show_create_project` + fill + `finish_wizard` | proyecto id 2 creado; sesión «Sesión 1 - ProyectoPrueba» active; `combo.currentData() == pid`; botones True; wizard cerrado | ✓ PASS |
| Cancel del wizard | `_project_wizard._cancel()` | wizard limpiado, sin proyecto nuevo | ✓ PASS |
| Doble clic en ítem «Desconectados» (vía `_accept_item`) | diálogo real offscreen | `dlg.result()==1`, kind="device", value='usb#vid_054c&pid_0b48' → `_apply_source_choice` → **ValueError: too many values to unpack** | ✗ FAIL |
| Suite de 4 tests en Qt offscreen | `python -m unittest tests.test_source_picker tests.test_wifi_source tests.test_source_content tests.test_e2e` | 90 tests, OK | ✓ PASS |
| Gates estructurales Tareas 1-3 (ausencia/presencia/defaults) | script de asserts | ALL GATES PASS | ✓ PASS |

### Probe Execution

Sin probes declarados (quick task sin `scripts/*/tests/probe-*.sh`). N/A.

### Deviation Review (Rule 2 — `_pick_device_source` y `DevicePickerDialog` retirados de main_window.py)

| Check | Result | Evidence |
| ----- | ------ | -------- |
| Sin referencias colgantes de `_pick_device_source` | ✓ | 0 matches en `app/` y `tests/` |
| `DevicePickerDialog` importable donde se necesita | ✓ | `app/ui/source_picker.py:22` import + :140 uso (`_pick_device`); `tests/test_source_picker.py` parchea `app.ui.source_picker.DevicePickerDialog` (:195-226) |
| Capacidad preservada (D-03) | ✓ | `_pick_device_source` pre-cambio (git show 7aa7f98^): DevicePickerDialog → cache_dir → `_register_device_source`. Vía superviviente: `_apply_source_choice` kind "device" (:2762-2765) → `_register_device_source_from_picker` (mismo cache_dir + backend WpdBackend). Funcionalmente equivalente — no se pierde selección ni registro de dispositivos |
| i18n | ✓ | `cosechamedia_en.ts` conserva el contexto `DevicePickerDialog` (:167) — la clase sigue viva en device_picker.py; sin rotura del catálogo |
| Segunda desviación (default No en borrado de device) | ✓ | :2845-2850 `QMessageBox.Yes | QMessageBox.No, QMessageBox.No` — coherente con D-09 y con el fix 3b |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| UI-04 | 260816-k7i-PLAN | Se implementan las reubicaciones acordadas sin romper flujos existentes | ⚠️ PARTIAL | Reubicaciones implementadas (wizard, botón, menú, zombies) pero el flujo «añadir origen» tiene la regresión del doble clic (ValueError) — un flujo roto |
| UI-05 | 260816-k7i-PLAN | Verificación visual y funcional post-cambio; tests pasan con Qt offscreen | ✓ SATISFIED (automático) | 90 tests OK offscreen; parte visual → ver Human Verification |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| app/ui/source_picker.py | 224-232 | `_accept_item`/`_set_from_item` sin guard de rol device (solo `_accept_current` guardado) | 🛑 BLOCKER | Doble clic en «Desconectados» acepta el diálogo con kind="device"/value-id → ValueError en `_apply_source_choice`; contradice T-260816-04 y la afirmación del SUMMARY |
| app/ui/main_window.py | 2762-2765 | Desempaquetado de tupla sin defensa en rama kind "device" | 🛑 BLOCKER (consecuencia) | Recibe value en forma inesperada (string) y crashea con ValueError |
| app/ui/main_window.py | 1205-1227 | `_on_project_wizard_finished` retorna silencioso si `not row` (sin feedback) | ℹ️ Info | Aceptable (mitigación de spoofing T-260816-02); solo alcanzable si el INSERT del wizard y el SELECT del callback usan DBs distintas (no ocurre en producción, ambos usan el singleton `app.core.db.db`) |

Sin markers TBD/FIXME/XXX/PLACEHOLDER en los 4 archivos de la fase (los únicos matches de «placeholder» están en `wheat_field.py`, constante de color, fuera de la fase).

### Human Verification Required

1. **Visual del ProjectWizard** — Test: pulsar «Nuevo Proyecto» en la app. Expected: wizard modal 600×520 con nombre/descripción/destino/duración/organización/fecha-metadatos; al confirmar, proyecto + sesión inicial creados, combo selecciona y botones habilitados; cancelar sin efectos. Why human: el comportamiento se probó por spot-check automático; la apariencia/modalidad visual es humana.
2. **Posición de «Volcado selectivo…»** — Test: mirar Acciones post-ingesta → Operaciones. Expected: botón junto a Reorganizar/Limpiar completados, clickable, abre el asistente. Why human: la posición se verificó por código (op_row); la presentación es visual.
3. **Cadena WiFi operativa** — Test: «Añadir origen… → WiFi QR». Expected: WifiMethodDialog → panel QR PairDrop funcional. Why human: el cableado está verificado (grep + tests de gating); el QR real y la conexión de dispositivos requieren interacción real.

### Gaps Summary

**1 gap bloqueante:**

**Truth 5 (parcial) — la vía de doble clic de los ítems «Desconectados» rompe el contrato no-accionable del diálogo Añadir origen.** El rol `("device", dev_id)` añadido a `_missing_item` (Tarea 3) convierte la vía `_accept_item` (itemDoubleClicked) en una ruta de aceptación: el diálogo se cierra con `kind="device"` y `value=<id en crudo>`, y `_apply_source_choice` lanza `ValueError: too many values to unpack (expected 3)` al desempaquetar `device_id, device_folder, device_name = value`. Reproducido en runtime offscreen con el diálogo real. La mitigación T-260816-04 del propio plan («un ítem no-accionable nunca habilita OK ni muta kind/value») se aplicó solo a `_update_ok_state` y `_accept_current`; la afirmación del SUMMARY («_accept_item también protegido por defensa en profundidad») no se sostiene: no hay guard en `_accept_item`/`_set_from_item`. Es una regresión respecto al estado previo (sin rol, `_accept_item` era no-op).

**Remediación (surgical):** guard `if role is not None and role[0] == "device": return` al inicio de `_accept_item` (o en `_set_from_item`), idéntico al de `_accept_current`; añadir un test de regresión que invoque `_accept_item` sobre un ítem «Desconectados» y verifique que no muta kind/value ni acepta. El resto de la truth 5 está VERIFICADO (menú limpio, borrado por menú contextual funcional y testeado, MTP+FTP, default No).

**Resumen de lo logrado:** fix 2 (wizard) ✓, fix 3 (confirmaciones) ✓, item 3 (volcado selectivo en Operaciones) ✓, item 4 (zombies eliminados, WiFi intacto) ✓, item 5 (menú limpio + gestión migrada; con la regresión del doble clic) ⚠️, tests 90/90 ✓. Las 2 desviaciones documentadas son consistentes (sin refs colgantes, capacidad preservada, default No coherente con D-09).

---

_Verified: 2026-08-16_
_Verifier: the agent (gsd-verifier)_
