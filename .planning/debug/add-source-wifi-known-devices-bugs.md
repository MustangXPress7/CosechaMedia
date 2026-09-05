---
slug: add-source-wifi-known-devices-bugs
status: investigating
trigger: "1. Add Source dialog - devices not saved: Add device (e.g., F: drive) via 'detectar' or 'examinar', give it a name. Device shows in 'Añadir origen' dialog. But if delete device or switch projects without that device connected, device disappears from 'Añadir origen'. WiFi devices DO persist across projects. 2. WiFi shows as 'desconectado' immediately after adding - scanning QR shows nothing. 3. WiFi saved by name in dropdown - multiple WiFi senders may have name collisions, should be identified by unique token/ID per instance."
created: "2026-09-05T14:30:00Z"
updated: "2026-09-05T14:30:00Z"
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
hypothesis: "Three separate but related bugs: (1) USB/MTP device persistence missing upsert to known_devices when adding via 'Añadir origen'; (2) WiFi status check fails because ShootInboxServer not running or status probe uses wrong endpoint; (3) WiFi dropdown uses display name as key instead of unique token, causing potential collisions"
next_action: "gather initial evidence - trace the code paths for device persistence in AddSourceDialog, WiFi status check, and WiFi sender registration"
reasoning_checkpoint: "Need to trace three code paths: (1) AddSourceDialog → on_camera_name_changed → upsert_known_device for USB/MTP; (2) WiFi status check in _refresh_source_list / _build_path_widget; (3) AddSourceDialog WiFi row population uses sender name as value instead of token"

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

## Eliminated
- hypothesis: "on_camera_name_changed not called for auto-detect"
  reason: "Fixed in commit 99bba16 - _on_camera_detected now calls on_camera_name_changed callback"

- hypothesis: "known_devices table not created"
  reason: "Table created in db.py create_tables(), migration sync_device_settings_to_known runs on DB init"

## Resolution
root_cause: ""
fix: ""
verification: ""
files_changed: []