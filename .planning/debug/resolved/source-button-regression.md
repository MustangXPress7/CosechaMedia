---
status: resolved
trigger: "User reports a regression after plan 01.6.0-03-05 (SourcePanel implementation): WiFi and FTP were moved to the main window (embedded, per DEC-DIR-4). Now the 'origen' (source/add source) button doesn't open any window/dialog."
created: "2026-09-02T09:15:00.000Z"
updated: "2026-09-02T10:15:00.000Z"
---

## Current Focus
hypothesis: "The '+ Origen' button (btn_add_source) is connected to _add_source_entry -> _pick_source_entry which only commits CHECKED rows from SourcePanel. There's no UI to ADD new sources to the SourcePanel. The old AddSourceDialog (which opened a tabbed dialog to choose folder/MTP/WiFi/FTP) was deleted in plan 05, but no replacement menu/dialog was wired to the button."
test: "Check if btn_add_source should show a QMenu with options to add new sources (Carpeta, USB/MTP, WiFi, FTP) similar to old AddSourceDialog tabs"
expecting: "btn_add_source should open a menu/dialog to add new sources, which then appear in SourcePanel as checked rows"
next_action: "Implement a QMenu on btn_add_source with options to add new sources (folder, MTP, WiFi, FTP)"

## Symptoms
expected: "Clicking 'Añadir origen' button should open source selection dialog/window to add new sources"
actual: "'Añadir origen' button does nothing - no dialog/window opens, only commits already-checked rows"
errors: ""
reproduction: "1. Open app 2. Click 'Añadir origen' button in toolbar/menu 3. Nothing happens (no dialog to add new source)"
started: "After plan 01.6.0-03-05 (SourcePanel implementation)"

## Eliminated
<!-- APPEND only - prevents re-investigating -->

- hypothesis: "SourcePanel should be shown in a dialog/window when button clicked"
  evidence: "SourcePanel is already embedded in main window (left_col.addWidget(self.source_panel) line 559), not a dialog"
  timestamp: "2026-09-02T09:30:00Z"

- hypothesis: "btn_add_source should call _open_add_source_dialog"
  evidence: "No such method exists; AddSourceDialog was deleted in plan 05"
  timestamp: "2026-09-02T09:35:00Z"

- hypothesis: "SourcePanel.add_source_requested signal should be connected"
  evidence: "Signal exists but never emitted; no UI in SourcePanel to trigger it"
  timestamp: "2026-09-09:40:00Z"

## Evidence
<!-- APPEND only - facts discovered -->

- timestamp: "2026-09-02T09:30:00Z"
  checked: "app/ui/main_window.py btn_add_source wiring (lines 537-541)"
  found: "btn_add_source.clicked.connect(self._add_source_entry) -> _pick_source_entry() which only commits checked rows from SourcePanel"
  implication: "Button doesn't open any dialog/menu to ADD new sources"

- timestamp: "2026-09-02T09:35:00Z"
  checked: "app/ui/source_panel.py add_source_requested signal (line 48)"
  found: "Signal defined but NEVER EMITTED in SourcePanel"
  implication: "No UI triggers the 'add source' action from the panel itself"

- timestamp: "2026-09-02T09:40:00Z"
  checked: "git history - old _pick_source_entry (commit 75d1d0a)"
  found: "Old implementation opened AddSourceDialog (tabbed dialog with Guardados/Añadir tabs) to select/add sources"
  implication: "Plan 05 replaced dialog with SourcePanel but forgot to wire 'add new source' functionality to the button"

- timestamp: "2026-09-02T09:45:00Z"
  checked: "Plan 01.6.0-03-05-PLAN.md (T1 tracer task)"
  found: "Says 'la opción USB/MTP embebe MtpDevicePane en un QStackedWidget; al aceptar se commitea' - implies a menu/dialog should open from the button"
  implication: "Design intended a menu on '+ Origen' button to add new sources, but implementation only has commit logic"

- timestamp: "2026-09-02T10:00:00Z"
  checked: "Fix implementation - added _show_add_source_menu, _add_folder_source, _add_mtp_source, _add_wifi_source, _add_ftp_source, _on_mtp_pane_accepted, _on_ftp_pane_accepted, _check_newly_added_row"
  found: "Added QMenu on btn_add_source with 4 options: Carpeta, Dispositivo USB/MTP, WiFi, FTP. Each opens appropriate dialog/pane and adds source to project, then refreshes SourcePanel and checks the new row."
  implication: "Fix restores the 'add new source' functionality that was lost when AddSourceDialog was replaced by SourcePanel"

## Resolution
root_cause: "Plan 05 (commit 96d35bd) replaced the tabbed AddSourceDialog with SourcePanel (embedded table), but the '+ Origen' button (btn_add_source) was only wired to commit checked rows (_pick_source_entry), not to ADD new sources. The AddSourceDialog provided the UI to choose folder, MTP device, WiFi sender, or FTP profile - this functionality was lost."
fix: "Added _show_add_source_menu() that shows a QMenu on btn_add_source click with 4 options: 'Carpeta…', 'Dispositivo USB/MTP…', 'WiFi (PairDrop)…', 'Servidor FTP…'. Each option opens the appropriate dialog/pane (QFileDialog, MtpDevicePane, SenderEditDialog, FtpDevicePane), creates the session, refreshes SourcePanel, and auto-checks the new row so the user can commit with another click on '+ Origen'."
verification: "All existing tests pass (test_main_window: 50 OK, test_source_panel: 20 OK, test_wifi_source: 55 OK, full suite: 125+ OK). The fix restores the 'add new source' functionality while keeping the new SourcePanel-based commit flow."
files_changed: ["app/ui/main_window.py"]