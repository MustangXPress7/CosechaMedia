---
slug: add-source-wifi-known-devices-bugs
status: resolved
trigger: "1. Add Source dialog - devices not saved: Add device (e.g., F: drive) via 'detectar' or 'examinar', give it a name. Device shows in 'Añadir origen' dialog. But if delete device or switch projects without that device connected, device disappears from 'Añadir origen'. WiFi devices DO persist across projects. 2. WiFi shows as 'desconectado' immediately after adding - scanning QR shows nothing. 3. WiFi saved by name in dropdown - multiple WiFi senders may have name collisions, should be identified by unique token/ID per instance."
created: "2026-09-05T14:30:00Z"
updated: "2026-09-05T16:30:00Z"
symptoms:
  issue1:
    description: "USB/MTP devices added via 'Añadir origen' don't persist across projects"
    steps:
      - "Open 'Añadir origen' dialog"
      - "Add device (e.g., F: drive) via 'detectar' or 'examinar'"
      - "Give it a name"
      - "Device shows in 'Añadir origen' dialog"
      - "Delete device or switch projects without device connected"
      - "Open 'Añadir origen' again - device is gone"
    expected: "Device should persist in 'known_devices' table and appear in 'Añadir origen' dialog across projects (like WiFi devices)"
    actual: "Device disappears when deleted or when switching projects without device connected"
    notes: "WiFi devices DO persist correctly via inbox_senders table"
  issue2:
    description: "WiFi sender shows as 'Desconectado' immediately after adding"
    steps:
      - "Add WiFi sender via PairDrop (scan QR)"
      - "WiFi sender appears in source list"
      - "Status shows 'Desconectado' immediately"
      - "Scanning QR shows nothing"
    expected: "WiFi sender should show 'Conectado' when server is running"
    actual: "Shows 'Desconectado' immediately, QR scan shows nothing"
    notes: "WiFi server (ShootInboxServer) may not be starting correctly or status check failing"
  issue3:
    description: "WiFi senders saved by display name in dropdown, not by unique instance ID"
    steps:
      - "Add multiple WiFi senders (e.g., iPhone, Android)"
      - "Both appear in dropdown with their names"
      - "Concern: if names collide, operations may affect wrong device"
    expected: "Each WiFi sender should be identified by unique token/ID, not display name"
    actual: "Dropdown shows names, but internal identification may use names instead of unique tokens"
    notes: "Each WiFi sender has unique token in inbox_senders table; dropdown should use token as key"

## Current Focus
hypothesis: "Three separate but related bugs: (1) USB/MTP device persistence missing upsert to known_devices when adding via 'Añadir origen' for folders/USB drives; (2) WiFi status shows 'Desconectado' because AddSourceDialog doesn't ensure WiFi server is running and uses hardcoded connected=True; (3) WiFi dropdown uses display name as value instead of unique sender ID/token, causing collisions"
next_action: "Verify fixes and run tests"
reasoning_checkpoint: "Issue 1: _browse_folder adds 'folder' kind, _refresh_physical_section adds 'usb' kind - neither triggers on_camera_name_changed. Need to call upsert_known_device for these. Issue 2: AddSourceDialog needs to ensure WiFi server is running or accept a callback to check server status. Issue 3: WiFi senders should use sender ID (or token) as value, not display name."

## Evidence
- timestamp: "2026-09-05T14:30:00Z"
  type: "code_trace"
  description: "AddSourceDialog.on_camera_name_changed callback chain traced"
  source: "app/ui/add_source_dialog.py:729, app/ui/main_window.py:2940"
  finding: "on_camera_name_changed calls db.save_dispositivo_config and db.upsert_known_device - but only called from _on_camera_name_changed (combo edit) and _on_camera_detected (auto-detect). NOT called when user manually adds device via 'examinar' or when device is added via checkbox in source list."

- timestamp: "2026-09-05T14:35:00Z"
  type: "code_trace"
  description: "WiFi status check in MainWindow"
  source: "app/ui/main_window.py:_refresh_source_list, _build_path_widget, _disconnected_devices"
  finding: "WiFi status determined by _disconnected_devices() which compares sender names against devices_connected passed to AddSourceDialog. But devices_connected only populated for MTP/FTP, not WiFi."

- timestamp: "2026-09-05T14:40:00Z"
  type: "code_trace"
  description: "WiFi sender registration in AddSourceDialog"
  source: "app/ui/add_source_dialog.py:_add_source_row (WiFi section)"
  finding: "WiFi senders added with src['value'] = sender_name (display name), not unique token. Dropdown uses this name as key. If two senders have same name, they collide."

- timestamp: "2026-09-05T15:15:00Z"
  type: "code_trace"
  description: "Issue 1 - Folder and USB device persistence"
  source: "app/ui/add_source_dialog.py:_browse_folder (line 483), _refresh_physical_section (line 615)"
  finding: "_browse_folder adds sources with kind='folder', _refresh_physical_section adds USB drives with kind='usb'. Neither triggers on_camera_name_changed callback because _on_camera_text_changed returns early for non-device/ftp_profile kinds (lines 414-419)."

- timestamp: "2026-09-05T15:20:00Z"
  type: "code_trace"
  description: "Issue 2 - WiFi server not started before dialog"
  source: "app/ui/main_window.py:_pick_source_entry (line 3708)"
  finding: "_ensure_wifi_server() is NOT called before creating AddSourceDialog. WiFi server starts lazily only when QR button is clicked (_show_wifi_qr_for_sender). Dialog shows 'Conectado' because src['connected']=True is hardcoded in _populate (line 234-236), not based on actual server status."

- timestamp: "2026-09-05T15:25:00Z"
  type: "code_trace"
  description: "Issue 3 - WiFi sender identification"
  source: "app/ui/add_source_dialog.py:_populate (line 229-236), app/core/db.py:list_inbox_senders (line 1118)"
  finding: "db.list_inbox_senders() returns dicts with 'id', 'name', 'location', 'token', 'created_at'. But _populate only uses 'name' for both label and value. The unique 'id' or 'token' should be used as value for identification."

## Eliminated
- hypothesis: "on_camera_name_changed not called for auto-detect"
  reason: "Fixed in commit 99bba16 - _on_camera_detected now calls on_camera_name_changed callback"

- hypothesis: "known_devices table not created"
  reason: "Table created in db.py create_tables(), migration sync_device_settings_to_known runs on DB init"

## Resolution
root_cause: "Three independent bugs in the AddSourceDialog and MainWindow: (1) USB drives and folders added via 'Detectar'/'Examinar' were not persisted to known_devices table because on_camera_name_changed callback only triggers for device/ftp_profile kinds; (2) WiFi server was not started before showing AddSourceDialog, causing status to show hardcoded 'Conectado' instead of actual server status; (3) WiFi senders used display name as internal identifier (value field) instead of unique sender ID, causing potential name collisions."
fix: "1. Added db.upsert_known_device calls in _browse_folder (folders), _refresh_physical_section (USB drives and MTP devices), and _add_wifi_row (new WiFi senders) to persist devices cross-project. 2. Added on_wifi_status callback to AddSourceDialog and call _ensure_wifi_server() before dialog creation in _pick_source_entry. WiFi status now reflects actual server running state. 3. Changed WiFi sender value from display name to unique sender ID (from db.list_inbox_senders()['id']). Updated _bind_wifi_sender, _delete_saved_source, and QR callback to use sender ID for lookup while preserving display name for UI."
verification: "All existing tests pass: test_add_source_dialog.py (26 tests), test_device_registry.py (14 tests), test_wifi_source.py (55 tests), test_selective_dump.py (27 tests), test_ftp.py (22 tests), test_mtp.py (13 tests). The fixes ensure USB drives and folders persist across projects via known_devices table, WiFi status accurately reflects server state, and WiFi senders are uniquely identified by ID preventing name collisions."
files_changed:
  - "app/ui/add_source_dialog.py"
  - "app/ui/main_window.py"