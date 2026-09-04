---
slug: add-source-origin-bugs
status: resolved
trigger: >-
  5 bugs reportados en la tabla de orígenes y el diálogo Añadir origen tras la
  tarea 2026-09-04-bugs-add-source-dialog. Relacionados con la gestión de
  dispositivos MTP/FTP/WiFi: borrado, categorización, botón borrar tras detectar,
  y borrado WiFi en la tabla de orígenes.
created: 2026-09-04
updated: 2026-09-04
---

## Symptoms

1. **MTP auto-creation + camera persistence:** Los dispositivos MTP se crean automáticamente de las ubicaciones de disco y parecen conservar datos de cámara aunque se haya solicitado ser borrados (desde Herramientas > Borrar dispositivos guardados).
2. **Origin table delete (related to BUG-2 previous task):** El BUG-2 resuelto en la última tarea se refería sobre todo a la tabla de origen (source_list en main_window), no solo al diálogo. En la tabla de orígenes, borrar no funciona correctamente.
3. **New devices default to FTP section:** Los nuevos dispositivos añadidos a la ventana de añadir origen aparecen por defecto en la sección de FTP, y no categorizados en su apartado (MTP/USB).
4. **Delete button broken after Detectar:** Se sigue creando mal el botón de borrar al hacer click en "Detectar", haciendo que no se pueda borrar un dispositivo recién detectado en el diálogo.
5. **WiFi can't be deleted from origin table:** En la tabla de orígenes, se puede deseleccionar WiFi correctamente, pero no se puede eliminar WiFi. Relacionado con el punto 2.

## Known Context

Previous quick task: `2026-09-04-bugs-add-source-dialog` (commit `b853589`) fixed bugs/improvements in AddSourceDialog. These are NEW bugs found after that task.

### Key files
- `app/ui/add_source_dialog.py` (668 lines) — dialog with flat table, 3 sections, 5 columns
- `app/ui/main_window.py` (4849 lines) — main window with origin table (`source_list`) and `_apply_source_choice`
- `app/core/db.py` — `DatabaseManager`, `delete_device`, `delete_all_saved_devices`, `delete_inbox_sender`, `get_sessions`

### Key functions to investigate
- `_delete_source_at_row(row)` at main_window.py:2912 — calls `_hide_source_path(path)`
- `_hide_source_path(path)` at main_window.py:2966 — removes from `_source_paths` list + refreshes UI, but does NOT delete sessions
- `_remove_source_path(path)` at main_window.py:2934 — proper deletion: deletes sessions + WiFi senders
- `_populate_source_paths_from_sessions()` at main_window.py:3443 — rebuilds `_source_paths` from sessions
- `_append_raw_source(src)` at add_source_dialog.py:430 — adds rows at `self.table.rowCount()` (END of table, after all sections)
- `_refresh_physical_section()` at add_source_dialog.py:467 — calls `_append_raw_source` for new devices
- `_on_delete_clicked(kind, value)` at add_source_dialog.py:397 — calls `on_delete` callback then `_remove_row`
- `_apply_source_choice(src)` at main_window.py:3458 — processes dialog results by kind

## Hypotheses

### H1: Origin table delete just hides, doesn't persist
- `_delete_source_at_row` → `_hide_source_path` only removes from `_source_paths` (in-memory list)
- Does NOT delete sessions from DB
- `_populate_source_paths_from_sessions` rebuilds from sessions → source reappears on next refresh
- This explains bugs 1, 2, and 5

### H2: WiFi delete needs sender cleanup
- `_hide_source_path` doesn't handle WiFi sender deletion
- `_remove_source_path` (the proper one at line 2934) DOES handle sender cleanup
- Bug 5: WiFi "deletion" only hides visually, sender+session persist

### H3: _append_raw_source appends at end of table (after FTP)
- `_append_raw_source` uses `self.table.rowCount()` → inserts after all existing rows
- New detected devices appear below the FTP section
- This is bug 3

### H4: Trash button after Detectar may have row index issues
- `_append_raw_source` creates trash button with lambda capturing kind/value (OK)
- But `_remove_row` uses index from `_row_sources` iteration (OK for kind/value match)
- Potential issue: section spans (setSpan) not updated after append

### H5: MTP devices recreated by auto-detect timer
- Auto-detect timer runs periodically → calls MTP listing → recreates devices
- Even after DB deletion, timer + sessions = devices reappear

## Current Focus

- hypothesis: RESOLVED — origin-table delete not permanent (sessions/WiFi senders persisted); `_append_raw_source` appended at table end (wrong section); `delete_device` didn't clear `device_settings` (camera name resurrected)
- next_action: confirm fix + full test suite (345 OK)

## Evidence

- Confirmed: `_delete_source_at_row` (main_window.py) called `_hide_source_path` which only removed from in-memory `_source_paths` without deleting sessions/WiFi senders. Sessions survived and `_populate_source_paths_from_sessions` rebuilt the source on next refresh → bugs 1/2/5.
- Confirmed: `_remove_source_path` (main_window.py:2934) properly deletes sessions + WiFi senders but was NOT called by the delete action.
- Confirmed: `_append_raw_source` inserted at `self.table.rowCount()` (end of table, after FTP) instead of within the correct section → bug 3. Fixed by adding `insert_before_row` + `_section_start_row` helper; detected MTP/USB rows now go before the WiFi section, new WiFi rows before the FTP section.
- Confirmed: `delete_device` (db.py) did not clean `device_settings` for the device, so re-detected devices resurrected the saved camera name → bug 1. Added `DELETE FROM device_settings WHERE device_key=?`.
- Root cause for all: session/device lifecycle wasn't permanent on delete; row insertion always appended at table end.

## Root Cause

Multiple related root causes:
1. **Origin-table delete was not permanent**: `_delete_source_at_row` → `_hide_source_path` removed only the visible list entry; the session (and WiFi sender) persisted in DB, so sources reappeared on refresh.
2. **`_append_raw_source` appended at table end** (after the FTP section) instead of the matching section → detected/new devices appeared under FTP.
3. **`delete_device` didn't clear `device_settings`** → re-detected MTP devices reloaded the stored camera name.

## Fixes

1. `_delete_source_at_row` now calls `_remove_source_path` (deletes sessions + WiFi senders) and updates the confirmation text to reflect permanent deletion.
2. `add_source_dialog._append_raw_source` gained `insert_before_row`; `_refresh_physical_section`/`_add_wifi_row`/`_browse_folder` pass the matching section offset, so rows land in the correct section.
3. `db.delete_device` also deletes the device's `device_settings` row (camera name cache).
4. `_append_raw_source` trash button now uses the same icon-button style as `_add_source_row` (broken button after "Detectar" fixed).

## Verification

- Added tests: `test_detected_device_inserted_in_physical_section`, `test_wifi_row_inserted_in_wifi_section`, `test_detected_device_delete_button_works` (add_source_dialog); `delete_device` device_settings cleanup (test_db); updated `test_source_delete_button_removes_source_and_sessions` (test_source_content).
- Full suite: 345 tests OK (2 skipped).
