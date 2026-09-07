---
phase: 02-code-review
reviewed: 2026-09-07T18:30:00Z
depth: standard
files_reviewed: 17
files_reviewed_list:
  - app/ui/main_window.py
  - app/ui/mixins/__init__.py
  - app/ui/mixins/camera_mixin.py
  - app/ui/mixins/devices_mixin.py
  - app/ui/mixins/ingest_mixin.py
  - app/ui/mixins/menu_mixin.py
  - app/ui/mixins/project_mixin.py
  - app/ui/mixins/sessions_mixin.py
  - app/ui/mixins/sources_mixin.py
  - app/ui/mixins/wifi_mixin.py
  - app/ui/mixins/workers.py
  - tests/test_e2e.py
  - tests/test_main_window.py
  - tests/test_session_content_modes.py
  - tests/test_source_content.py
  - tests/test_wifi_source.py
findings:
  critical: 2
  warning: 8
  info: 12
  total: 22
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-09-07T18:30:00Z
**Depth:** standard
**Files Reviewed:** 17
**Status:** issues_found

## Summary

Reviewed 9 commits refactoring `MainWindow` (4589 → 961 lines) into 8 mixins under `app/ui/mixins/`. The refactor extracts: `CameraMixin`, `MenuMixin`, `SourcesMixin`, `ProjectMixin`, `SessionsMixin`, `DevicesMixin`, `IngestMixin`, `WifiMixin` (pre-existing). Tests pass (393 passed, 5 skipped, 1 pre-existing failure in `test_mtp.py` unrelated to refactor).

Key concerns:
1. **Critical**: Duplicate `self._source_paths = []` initialization in `MainWindow.__init__` (lines 161 and 164) — second overwrites first.
2. **Critical**: Test infrastructure now patches **10+ module namespaces** per test class (db singletons across `mw`, `camera_mixin_module`, `sessions_mixin_module`, `sources_mixin_module`, `project_mixin_module`, `devices_mixin_module`, `ingest_mixin_module`, `ingestor_module`, `me_module`, `wifi_mixin_module`) — extremely fragile maintenance burden.
3. **Warnings**: Multiple long methods (>50 lines), bare `except:` in core (pre-existing), inconsistent error handling, magic numbers, incomplete `__init__.py` exports.
4. **Positives**: All user-facing strings use `tr()`, SQL uses parameterized queries, no SQL injection/path traversal found, MRO clean with no method conflicts between mixins.

---

## Critical Issues

### CR-01: Duplicate `_source_paths` initialization in MainWindow.__init__

**File:** `app/ui/main_window.py:161,164`
**Issue:** `self._source_paths = []` appears twice (lines 161 and 164). The second assignment overwrites the first — redundant and indicates copy-paste error during refactor. While not functionally breaking (both assign empty list), it's a clear bug in the refactored code.

**Fix:**
```python
# Line 161: keep this
self._source_paths = []
self._processed_count = 0
self._total_files = 0
# Line 164: REMOVE this duplicate
# self._source_paths = []  ← DELETE
self._unknown_cameras = set()
```

---

### CR-02: Test singleton patching spans 10+ namespaces — unmaintainable

**File:** `tests/test_main_window.py` (and `test_e2e.py`, `test_wifi_source.py`, `test_session_content_modes.py`, `test_source_content.py`)
**Issue:** Every test class patches `db` in **10+ modules**:
- `mw.db`
- `camera_mixin_module.db`
- `sessions_mixin_module.db`
- `sources_mixin_module.db`
- `project_mixin_module.db`
- `devices_mixin_module.db`
- `ingest_mixin_module.db`
- `ingestor_module.db`
- `me_module.db` (metadata_engine)
- `wifi_mixin_module.db`

This is a direct consequence of the module-level singleton pattern (`db = DatabaseManager()` in `app/core/db.py:863`) combined with mixins importing `from app.core.db import db` at module level. Each mixin gets its own reference to the same singleton, but tests must patch **every reference** to isolate. Adding a new mixin = updating every test class.

**Fix:** Refactor to dependency injection — pass `db` instance to mixin methods or store on `MainWindow` and access via `self.db`. Short-term: create a test helper `patch_all_db(fake_db)` to reduce boilerplate. Long-term: eliminate module-level singletons in favor of constructor injection.

---

## Warnings

### WR-01: `start_ingest` method is 179 lines — exceeds recommended 50-line limit

**File:** `app/ui/mixins/ingest_mixin.py:36`
**Issue:** `start_ingest` does session validation, UI reset, ingestor creation, signal wiring, watcher startup, and button state management. Hard to read, test, and maintain.

**Fix:** Split into `_validate_ingest_sources`, `_create_ingestors`, `_wire_ingestor_signals`, `_start_watchers`, `_update_ingest_ui_state`.

---

### WR-02: `build_menu` method is 162 lines — exceeds recommended 50-line limit

**File:** `app/ui/mixins/menu_mixin.py:16`
**Issue:** Constructs 5 menus (Archivo, Ingesta, Configuración, Herramientas, Vista, Ayuda, Idioma) with 20+ actions in one method.

**Fix:** Extract `_build_file_menu`, `_build_ingest_menu`, `_build_config_menu`, `_build_tools_menu`, `_build_view_menu`, `_build_help_menu`, `_build_lang_menu`.

---

### WR-03: `_finalize_ingest` method is 73 lines — mixes UI, notifications, post-actions

**File:** `app/ui/mixins/ingest_mixin.py:384`
**Issue:** Stops watchers/ingestors, updates UI, computes stats, fires notifications, shows blockers dialog, queues post-actions (format, proxies, report, shutdown). Violates single responsibility.

**Fix:** Split into `_stop_ingestion_workers`, `_compute_final_stats`, `_notify_ingest_result`, `_queue_post_actions`.

---

### WR-04: `delete_current_project` is 69 lines, `delete_all_projects` is 53 lines

**File:** `app/ui/mixins/project_mixin.py:435,504`
**Issue:** Both methods duplicate COM cleanup (`_reset_mtp_thread_local`, `_reset_ingestors`, `_reset_wifi_ingestors`), DB deletion logic, and UI reset. Error handling repeated.

**Fix:** Extract `_cleanup_before_project_delete()` and `_reset_project_ui_state()` helpers.

---

### WR-05: `_on_source_widget_check_changed` is 65 lines — complex nested logic

**File:** `app/ui/mixins/sources_mixin.py:211`
**Issue:** Handles checkbox enable/disable, auto-session creation, WiFi ingestor cleanup, session deletion, and UI refresh in one method with 4 nesting levels.

**Fix:** Extract `_enable_source_path`, `_disable_source_path`, `_cleanup_wifi_ingestor_for_session`.

---

### WR-06: `_delete_saved_source` handles 5 `kind` cases in 64 lines

**File:** `app/ui/mixins/sources_mixin.py:561`
**Issue:** Large `if/elif` chain for `folder`, `ftp_profile`, `sender`, `device`, with repeated confirmation dialogs. Violates open/closed principle.

**Fix:** Use strategy pattern — `_delete_folder_source`, `_delete_ftp_profile`, `_delete_wifi_sender`, `_delete_device` — dispatch via dict.

---

### WR-07: `_ingestor_for_wifi_session` is 68 lines — duplicates `start_ingest` ingestor config

**File:** `app/ui/mixins/wifi_mixin.py:280`
**Issue:** Nearly identical `Ingestor` construction logic exists in `IngestMixin.start_ingest` (lines 163-180). Any change to ingestor params must be updated in two places.

**Fix:** Extract `_build_ingestor_config(session, camera_map)` returning kwargs dict, used by both.

---

### WR-08: Incomplete `__init__.py` exports only 3 of 8 mixins

**File:** `app/ui/mixins/__init__.py:1-5`
**Issue:** `__all__ = ["WifiMixin", "CameraMixin", "SessionsMixin"]` omits `MenuMixin`, `DevicesMixin`, `SourcesMixin`, `ProjectMixin`, `IngestMixin`. Inconsistent public API.

**Fix:**
```python
from app.ui.mixins.wifi_mixin import WifiMixin
from app.ui.mixins.camera_mixin import CameraMixin
from app.ui.mixins.menu_mixin import MenuMixin
from app.ui.mixins.sources_mixin import SourcesMixin
from app.ui.mixins.project_mixin import ProjectMixin
from app.ui.mixins.sessions_mixin import SessionsMixin
from app.ui.mixins.devices_mixin import DevicesMixin
from app.ui.mixins.ingest_mixin import IngestMixin

__all__ = ["WifiMixin", "CameraMixin", "MenuMixin", "DevicesMixin", 
           "SourcesMixin", "ProjectMixin", "SessionsMixin", "IngestMixin"]
```

---

## Info

### IN-01: Magic number `720` for default proxy resolution

**File:** `app/ui/mixins/ingest_mixin.py:718`
**Issue:** `return int(self.project_proxy_resolution.replace("p", "")) if self.project_proxy_resolution else 720` — `720` should be a constant `DEFAULT_PROXY_HEIGHT = 720`.

---

### IN-02: Magic number `100.0` for percentage calculation

**File:** `app/ui/mixins/ingest_mixin.py:315-316`
**Issue:** `pct = int(copied_bytes * 100.0 / total_bytes); pct = max(0, min(100, pct))` — `100` appears 3 times. Define `PERCENT_SCALE = 100`.

---

### IN-03: Hardcoded timeout `5000` ms in `_sync_timer`

**File:** `app/ui/main_window.py:203`
**Issue:** `self._sync_timer.setInterval(5000)` — should be `AUTO_SYNC_INTERVAL_MS = 5000` constant.

---

### IN-04: Hardcoded `60` second throttle in `_process_device_poll`

**File:** `app/ui/main_window.py:730`
**Issue:** `if now - self._last_device_sync.get(did, 0) < 60:` — should be `DEVICE_SYNC_THROTTLE_SEC = 60`.

---

### IN-05: Hardcoded `0.03` (3%) splitter threshold

**File:** `app/ui/main_window.py:752`
**Issue:** `threshold = total * 0.03` — should be `SPLITTER_HIDE_THRESHOLD_RATIO = 0.03`.

---

### IN-06: Bare `except:` blocks in `app/core/sd_reader.py` (pre-existing, 5 occurrences)

**File:** `app/core/sd_reader.py:73,103,115,127,139`
**Issue:** Convention says "avoid adding new bare `except:`; use `except Exception` with comment when swallowing is intentional." These pre-date the refactor but should be fixed.

---

### IN-07: `QSettings` org/app strings duplicated in multiple files

**File:** `app/ui/main_window.py:187`, `app/ui/mixins/menu_mixin.py:53,148`, `app/ui/mixins/project_mixin.py:359`
**Issue:** `"Audiovisual Production"`, `"CosechaMedia"` repeated 4×. Should be constants in `app/core/constants.py` or `app/ui/theme.py`.

---

### IN-08: `ORG_TYPE_MAP` duplicated in `main_window.py:53` and `ingest_mixin.py:25`

**File:** `app/ui/main_window.py:53`, `app/ui/mixins/ingest_mixin.py:25`
**Issue:** Same dict defined in two places. Single source of truth needed.

---

### IN-09: `_format_drive` uses `subprocess.run(["cmd", "/c", f"echo S | {cmd}"])` with string interpolation

**File:** `app/ui/main_window.py:65-72`
**Issue:** While `drive` is validated as `X:`, the pattern `echo S | format ...` via `cmd /c` is fragile. Prefer `subprocess.run(["format", drive, "/FS:exFAT", "/Q"], input=b"S\n", ...)` without shell.

---

### IN-10: Spanish comments mixed with English in some files

**File:** `app/ui/mixins/workers.py:8-10` (English docstring), `app/ui/mixins/menu_mixin.py:1` (English module docstring)
**Issue:** Conventions state "Comments are predominantly Spanish; English appears in older code. Match the dominant language of the file (Spanish)."

---

### IN-11: `wifi_mixin.py` imports `theme` but only uses `theme.get_theme()`

**File:** `app/ui/mixins/wifi_mixin.py:8`
**Issue:** Minor unused import surface — `theme` used only once. Acceptable but could import `from app.ui.theme import get_theme`.

---

### IN-12: `menu_mixin.py` imports `db` but never uses it directly

**File:** `app/ui/mixins/menu_mixin.py:10`
**Issue:** `from app.core.db import db` imported but no `db.` references in the file. Likely leftover from move.

---

---

_Reviewed: 2026-09-07T18:30:00Z_
_Reviewer: gsd-code-reviewer agent_
_Depth: standard_