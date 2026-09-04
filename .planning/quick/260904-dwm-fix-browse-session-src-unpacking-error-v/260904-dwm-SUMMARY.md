---
quick_id: 260904-dwm
slug: fix-browse-session-src-unpacking-error-v
status: complete
date: 2026-09-04
---

# Quick Task 260904-dwm: Fix _browse_session_src unpacking error

## Problem

`_browse_session_src` (app/ui/main_window.py:3256) crashed with
`ValueError: not enough values to unpack (expected 2, got 1)` at line 3262
(`kind, value = choice`) al elegir un origen en el selector de la sesión.

Root cause: `_pick_source_entry()` devuelve una **lista de dicts** de orígenes
(igual que para `_add_source_entry`), pero `_browse_session_src` la
desempaquetaba como una tupla de 2. Además, el diálogo unificado puede devolver
orígenes de tipo `device`, `usb`, `ftp_new` y `wifi` que el código no
manejaba.

## Fix

Reescrito `_browse_session_src` para iterar la lista de dicts y despachar cada
origen con el binding de sesión (espejo de `_apply_source_choice` pero
ligando a `current_session_id`):

- `folder`/`usb` -> `_assign_session_folder(current_session_id, value)`
- `browse` -> `QFileDialog` + `_assign_session_folder`
- `sender` -> `_bind_wifi_sender(value, session_id=current_session_id)`
- `ftp_profile` -> `_pick_ftp_source(preset_profile_id=value)`
- `device` -> `_register_device_source_from_picker(... WpdBackend)`
- `ftp_new` -> `_register_device_source_from_picker(... FtpBackend)`
- `wifi` -> `_pick_wifi_source()`

## Test

Nuevo `test_browse_session_src_handles_source_list` en
`tests/test_wifi_source.py` (parchea `_pick_source_entry` para devolver una
lista de dicts y verifica que despacha a `_assign_session_folder` sin
crashear).

## Verification

- `pytest tests/test_wifi_source.py -k browse_session` -> 1 passed
- `pytest tests/test_mtp.py` -> 13 passed (aislado)
- Full suite `tests/`: 342 passed, 5 skipped. Único fallo observado
  (`test_e2e.py::test_ingest_to_dump_targets`) es un flake de entorno
  (ffprobe devolvió non-zero para `clip2.MOV` una vez; reejecutado pasa).
  La contaminación cruzada `wifi_source + mtp`
  (`test_wpd_session_devicename_no_duplicate`) es pre-existente y de
  aislamiento/orden — pasa con `test_mtp.py` aislado y en el orden
  alfabético normal (< test_wifi_source), y reproduce también con el árbol
  limpio.

## Commits

- Code/test: (fix commit)
- Docs: (docs commit)
