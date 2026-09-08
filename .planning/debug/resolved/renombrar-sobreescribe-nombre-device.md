---
status: resolved
trigger: "Ha sucedido un bug algo extraño: cuando he renombrado un dispositivo y ha saltado el pop-up, se ha sobreescrito el primer nombre que yo había añadido al dispositivo. Luego, en otro proyecto, he vuelto a escribir el mismo nombre que tenía al principio, y entonces sí han coexistido tanto el primer nombre como el segundo. Crítica al pop-up: «no volver a mostrar» debería de ser un tick de confirmación y no un tercer botón."
created: 2026-09-08
updated: 2026-09-08
---

# Debug session: renombrar-sobreescribe-nombre-device

## Symptoms

- **Expected:** Al renombrar un dispositivo (USB/tarjeta) y confirmar en el pop-up, el nuevo nombre debe quedar como único nombre conocido del dispositivo. El nombre anterior no debe quedar "huérfano" ni reaparecer duplicado en los combos de «Añadir origen» de otros proyectos.
- **Actual:** El primer nombre se ve sobreescrito y, al volver a escribir el nombre original en otro proyecto, ambos nombres coexisten (primer y segundo) en el registro.
- **Error messages:** Ninguno (sin excepciones visibles).
- **Timeline:** Tras el quick 260908-f5o que introdujo el pop-up de confirmación (2026-09-08).
- **Reproduction:** Añadir un origen USB con un nombre (detección/ingesta lo guarda por serial en `sd_cards`); luego renombrar el dispositivo desde la tabla de orígenes con el pop-up «¿Guardar para futuras sesiones?» (Sí). En otro proyecto, volver a escribir el nombre original → ambos nombres aparecen en el combo de «Añadir origen».

## Current Focus

- **hypothesis:** ✅ CONFIRMADA. El nombre del dispositivo se guarda en identidades distintas sin reconciliar: por serial de tarjeta (`sd_cards`) durante detección/ingesta, y por `device_id` (`device_settings` + `known_devices`) durante el rename. El rename escribe solo una identidad, dejando la otra con el nombre viejo → coexistencia en `list_known_camera_names()` que agrega `sd_cards` + `device_settings` + `dispositivos`.
- **test:** Re-leído `_persist_camera_mapping` (camera_mixin.py:294): si hay `device_id`, decide la vía `device_id` (save_dispositivo_config + upsert known_devices); la vía serial (`save_dispositivo` → `sd_cards`) solo se usa cuando NO hay `device_id` (p.ej. sesiones USB previas a los ids `usb:`). `_on_dialog_camera_name_changed` (B-20) también escribe solo la vía `device_id`.
- **expecting:** ✅ Confirmado: el rename (pop-up y diálogo) escribe SOLO `device_settings`/`known_devices` (`usb:F:\`), dejando `sd_cards.serial` (`073e1bba`) con el nombre viejo.
- **next_action:** resuelto — fix aplicado (reconciliación serial en ambas rutas de persistencia de nombre para devices `usb:`).

## Evidence

- timestamp: 2026-09-08 — DB real: `sd_cards` serial `073e1bba` → nombre "Culote"; `device_settings` `usb:F:\` → "Pitorrote"; `known_devices` `usb:F:\` → "Pitorrote". Coexisten dos nombres para la misma tarjeta física.
- timestamp: 2026-09-08 — Causa raíz confirmada en código: `_persist_camera_mapping` (camera_mixin.py:294-313) y `_on_dialog_camera_name_changed` (camera_mixin.py:331-350) escriben solo la identidad `device_id`; `list_known_camera_names` (db.py:1218-1235) agrega `sd_cards` + `device_settings` + `dispositivos` → el nombre viejo del serial queda huérfano y reaparece en el combo de «Añadir origen».
- timestamp: 2026-09-08 — Fix: en ambas rutas, si `device_id` es `usb:*`, reconciliar `sd_cards` por serial vía `sd_reader.get_volume_serial` + `db.save_dispositivo`. Gateado a `usb:` para no contaminar `sd_cards` con el serial del disco del sistema vía staging FTP/MTP.

## Eliminated

- No es un problema de `known_devices` (no alimenta `list_known_camera_names` directamente; es redundante con `device_settings`).
- No es un fallo del pop-up en sí (Sí) — el pop-up llama correctamente a `_persist_camera_mapping`; el fallo es que la persistencia no reconcilia la otra identidad.

## Resolution

- **root_cause:** La misma tarjeta física se persiste en dos identidades independientes — `sd_cards` por serial de volumen (vía usada cuando la sesión aún no tiene `device_id`, p.ej. sesiones USB anteriores a los ids `usb:`) y `device_settings`/`known_devices` por `device_id=usb:<LETRA>:\` — y el rename escribe solo la identidad `device_id`, dejando la identidad por serial con el nombre viejo; `list_known_camera_names()` agrega ambas tablas y muestra los dos nombres en el combo de «Añadir origen».
- **fix:** `_persist_camera_mapping` y `_on_dialog_camera_name_changed` (app/ui/mixins/camera_mixin.py) ahora reconcilian la identidad por serial (`sd_cards`) cuando el `device_id` es `usb:*`: resuelven el serial desde el path/unidad y hacen `save_dispositivo(serial, nombre)`, de modo que el rename deja un único nombre conocido. Gateado a `usb:` (MTP/FTP no tienen identidad serial; su staging local no debe escribir `sd_cards`).
- **guardrail:** 3 tests de regresión en `tests/test_main_window.py` (`TestRenameDialogPersistence`): rename USB desde diálogo reconcilia serial; `_persist_camera_mapping` con `usb:` reconcilia serial; FTP NO escribe `sd_cards`. Todos verdes.
- **prevention:** why not caught: no existía gate que verificara la unicidad del nombre tras un rename entre identidades (`sd_cards` vs `device_settings`) — la detección por `device_id` ya devolvía el nombre nuevo y enmascaraba el huérfano; guard: test de regresión `test_rename_usb_reconciles_serial_identity` / `test_persist_mapping_usb_reconciles_serial`.
- **nota (fuera de alcance):** `test_rename_in_dialog_ftp_prefix` falla en HEAD limpio (pre-existente: `combo.setEditText` sobre un `QLineEdit` en la fila FTP del diálogo). `name_manager_dialog`/pop-up: la crítica UX de «no volver a mostrar» como tercer botón en vez de tick se registra como feedback, no forma parte de este fix.