# Codebase Structure

**Analysis Date:** 2026-08-17

## Directory Layout

```
CosechaMedia/
├── main.py                  # Application entry point (QApplication + MainWindow)
├── main.spec                # PyInstaller packaging config
├── requirements.txt         # pip dependencies (PySide6, comtypes, qrcode)
├── Compilar.bat             # Windows local build (PyInstaller)
├── setup_mac.command        # macOS local build script
├── create_sound.py          # Standalone WAV generator (notification sounds)
├── LICENSE                  # PolyForm Noncommercial 1.0.0
├── README.md                # Bilingual (EN/ES) user + build documentation
├── Lanzar_SD_IMPORT.bat     # Quick launcher for development
├── .github/
│   └── workflows/build.yml  # CI: builds Windows/macOS/Linux, publishes release on v* tags
├── app/                     # Application package (all source)
│   ├── __init__.py          # __version__ = "1.2.1" (single source of truth)
│   ├── core/                # Business logic layer (13 modules)
│   ├── ui/                  # Qt widget layer (12 modules + assets)
│   ├── i18n/                # Translation catalogs (.ts source, .qm compiled)
│   └── sounds/              # Bundled notification WAVs
├── tools/                   # Developer scripts (translation pipeline)
├── tests/                   # unittest suites (offscreen Qt)
├── data/                    # Runtime data — GITIGNORED
│   ├── sd_import.db         # SQLite database (WAL)
│   ├── inbox/<alias>/       # WiFi receive cache per sender
│   ├── device_cache/<sha1>/ # MTP/FTP staging cache (+ .sync_manifest.json)
│   └── projects/Default/    # Auto-created default project root
├── Footage/                 # Dump output root (default) — GITIGNORED
├── graphify-out/            # Knowledge-graph cache — GITIGNORED
└── .planning/               # GSD planning state — GITIGNORED
```

## Directory Purposes

**`app/core/` — business logic:**
- Purpose: Everything that is not presentation — ingest, metadata, device access, storage, updates, i18n
- Contains: One module per concern; module-level service singletons
- Key files:
  - `app/core/db.py` — `DatabaseManager` + `db` singleton; all SQLite access; tables: `projects`, `sessions`, `files`, `sd_cards`, `device_settings`, `containers`, `footage_folders`, `ftp_profiles`, `inbox_senders`, `recent_paths`, `cameras`
  - `app/core/ingestor.py` — `Ingestor`, `DumpTarget`, `copy_verified`; the verified-copy pipeline; supports delicate mode (sequential), content filters, per-device settings
  - `app/core/metadata_engine.py` — `MetadataEngine` + `metadata_engine` singleton; ffprobe wrapper
  - `app/core/mtp.py` — `MtpBackend` interface, `WpdBackend` (COM), shared `_stage_session`
  - `app/core/ftp.py` — `FtpBackend`, `FtpSession`, network discovery
  - `app/core/shoot_inbox.py` — `ShootInboxServer`, `_UploadHandler`, embedded HTML page
  - `app/core/watcher.py` — `FileSystemWatcher`
  - `app/core/ffmpeg_utils.py` — `FFmpegProcessor` + `ffmpeg` singleton
  - `app/core/sd_reader.py` — `SDReader` + `sd_reader` singleton; volume serial detection for card-to-camera mapping
  - `app/core/updater.py` — GitHub Releases update logic
  - `app/core/notifications.py` — sounds + dialogs (imports `app.ui.theme`)
  - `app/core/translator.py` — `QtString`, `tr()`, language switching
  - `app/core/utils.py` — `resource_path`, disk helpers, MD5, folder structure

**`app/ui/` — Qt widgets:**
- Purpose: Windows, dialogs, theming, decorative painting, icons
- Contains: One file per window/dialog plus theme, background art, and icon tinting
- Key files:
  - `app/ui/main_window.py` — `MainWindow` (4,131 lines): the orchestrator; dashboard view, menus, all flows; contains `ElidedLabel` (line 149), `DashboardBackground` (line 121), `_StageWorker` (line 90), `_TaskWorker` (line 129)
  - `app/ui/theme.py` — `DARK`/`LIGHT` palettes, `ACCENTS`, QSS template, `apply_theme()`
  - `app/ui/icons.py` — SVG icon tinting with theme palette; weakref registry for automatic re-tint on theme change
  - `app/ui/selective_dump.py` — `SelectiveDumpAssistant` (date-picker dump + content filter) with `DateSelectCalendar`
  - `app/ui/device_picker.py` — `DevicePickerDialog` (MTP folder tree)
  - `app/ui/ftp_picker.py` — `FtpPickerDialog` (profile form + network scan + folder tree)
  - `app/ui/source_picker.py` — `SourcePickerDialog` (choose folder/sender/FTP profile as source)
  - `app/ui/wifi_panel.py` — `ShootInboxPanel` (floating QR panel), `SenderEditDialog`
  - `app/ui/wifi_picker.py` — `WifiMethodDialog` (PairDrop vs Classic FTP)
  - `app/ui/about_dialog.py` — `AboutDialog` with update-check/download workers
  - `app/ui/project_wizard.py` — `ProjectWizard` (first-run setup; `QDialog` subclass for proper QSS styling)
  - `app/ui/wheat_field.py` — `paint_wheat_field()` animated background
  - `app/ui/assets/` — `wheat_ear.svg` tiles; `logo.png` / `logo.ico` / `logo.icns`; `icons/` directory with SVG icon sources

**`app/i18n/`:**
- Purpose: Qt translation catalogs
- Contains: `cosechamedia_en.ts` (source catalog) and `cosechamedia_en.qm` (compiled)
- Note: Spanish is the source language and needs no catalog

**`app/sounds/`:**
- Purpose: Bundled notification sounds (`complete.wav`, `error.wav`, `stop.wav`)
- Note: `NotificationManager` copies them next to the executable at runtime and regenerates them with `create_sound.py`-style square waves if missing (`app/core/notifications.py:130-163`)

**`tools/`:**
- Purpose: Developer-only scripts, not shipped
- Contains: `update_translations.ps1` (lupdate → translate_en.py → lrelease) and `translate_en.py` (English catalog auto-translation)

**`tests/`:**
- Purpose: Unit + offscreen E2E tests; one file per core module plus `test_main_window.py` and `test_icons.py`
- Contains: `test_db.py`, `test_ingestor.py`, `test_metadata_engine.py`, `test_mtp.py`, `test_mtp_integration.py`, `test_ftp.py`, `test_shoot_inbox.py`, `test_wifi_source.py`, `test_updater.py`, `test_selective_dump.py`, `test_source_picker.py`, `test_source_content.py`, `test_e2e.py`, `test_main_window.py`, `test_icons.py`, plus `__init__.py`
- Pattern: `unittest.TestCase`; Qt tests set `QT_QPA_PLATFORM=offscreen` and share one `QApplication` (`tests/test_e2e.py:11-24`); module singletons are monkey-patched per test

**`data/` (gitignored):**
- Purpose: All runtime data; path resolved by `_resolve_db_path()` (`app/core/db.py:8-15`)
- Contains: `sd_import.db` (SQLite WAL), `inbox/<alias>` (WiFi cache), `device_cache/<sha1(device_id)>/<folder>` with `.sync_manifest.json`, `projects/<name>` (default project roots)

## Key File Locations

**Entry Points:**
- `main.py`: `main()` — the only process entry point
- `app/ui/main_window.py:1414`: `MainWindow.start_ingest` — ingest pipeline entry
- `app/core/shoot_inbox.py:441`: `ShootInboxServer.start` — WiFi server entry
- `app/ui/main_window.py:233`: `_auto_sync_check` — device auto-sync entry
- `app/core/updater.py:98`: `check_for_updates` — update flow entry

**Configuration:**
- `app/__init__.py`: version (validated against git tag by CI)
- `main.spec`: PyInstaller datas (logo, assets, sounds, i18n)
- `.github/workflows/build.yml`: cross-platform build + release
- `requirements.txt`: runtime deps
- Qt `QSettings` (not files): theme/accent (`app/ui/theme.py:8-13`), language (`app/core/translator.py:38`), window geometry, update check flag

**Core Logic:**
- `app/core/ingestor.py` — copy/verification/organization pipeline
- `app/core/db.py` — schema + all persistence (988 lines, 10 tables)
- `app/core/metadata_engine.py` — ffprobe metadata + file classification
- `app/core/mtp.py` + `app/core/ftp.py` — device staging (shared engine)
- `app/core/shoot_inbox.py` — WiFi upload server

**Testing:**
- `tests/` — all suites; `tests/test_e2e.py` drives `MainWindow.start_ingest` offscreen; `tests/test_main_window.py` tests `MainWindow` methods including `_detect_camera_for_session`

## UI Component Layout (source_list columns)

The `source_list` (`QTableWidget`) has 5 columns (`app/ui/main_window.py:420-448`):

| Col | Header | Content | Width | Resize |
|-----|--------|---------|-------|--------|
| 0 | "Ruta de origen" | Checkbox + `ElidedLabel` path + device button (QR/FTP) | 300px | Interactive |
| 1 | "Cámara" | Camera name (editable in manual mode) | 150px | Interactive |
| 2 | "" | Delicate mode toggle (🐌/⚡ icon button) | 32px | Fixed |
| 3 | "Contenido" | Content filter button | 100px | Interactive |
| 4 | "" | Delete source button (trash icon) | 40px | Fixed |

Column 0 is built by `_build_source_cell()` (`app/ui/main_window.py:2082-2137`) which creates a composite widget with checkbox, elided path label, and optional device button.
Column 2 is built by `_build_delicate_button()` (`app/ui/main_window.py:2176-2196`) which reads per-device delicate mode from `db.get_device_delicate()`.

## Naming Conventions

**Files:**
- `snake_case.py` for all modules — one concern per file (`ingestor.py`, `watcher.py`, `metadata_engine.py`)
- Test files: `test_<module>.py` mirroring the module name (`test_ingestor.py` → `app/core/ingestor.py`); integration-style suites suffix with `_integration` (`test_mtp_integration.py`)
- Catalogs: `cosechamedia_<locale>.ts/.qm`

**Directories:**
- `app/core/` and `app/ui/` are the two fixed layers; no feature folders — every feature spans one core module + MainWindow methods
- Runtime dirs under `data/` use the schema `inbox/<alias>` and `device_cache/<sha1(device_id)>/<device_folder>`

**Classes:**
- `PascalCase` for widget classes (`MainWindow`, `Ingestor`, `FtpPickerDialog`, `ShootInboxServer`, `ElidedLabel`)
- Private classes prefixed with `_` (`_StageWorker`, `_TaskWorker`, `_UploadHandler`, `_WpdSession`, `_Bridge`, `_SilentMessageBox`)
- Service instances are module-level `snake_case` singletons (`db`, `metadata_engine`, `ffmpeg`, `sd_reader`)

**Methods (MainWindow and dialogs):**
- `_build_ui` / `_build_<page>`: UI construction
- `_build_<widget>`: Widget factory methods (e.g. `_build_source_cell`, `_build_delicate_button`, `_build_content_button`, `_build_remove_source_button`)
- `on_<event>` / `_on_<event>`: signal handlers (`on_file_started`, `_on_ingestor_complete`, `_on_source_toggle`)
- `_open_<x>` / `_show_<x>` / `_pick_<x>`: dialog openers
- `_refresh_<x>` / `_load_<x>`: view/data sync
- `select_<thing>` / `_browse_<thing>`: path selection
- `_toggle_<x>`: state toggle methods (e.g. `_toggle_device_delicate`)
- `_detect_<x>`: detection methods (e.g. `_detect_camera_for_session`)
- `_device_key_for_source()`: helper to derive stable device key from session

**Variables:**
- `snake_case`; instance state stored as `self._private` attributes

## Where to Add New Code

**New Feature:**
- Primary code: `app/core/<feature>.py` for the business logic (plain functions/classes + optional module singleton), then wire it into `MainWindow` methods in `app/ui/main_window.py` (menu/dialog/button + signal handlers)
- Tests: `tests/test_<feature>.py` using `unittest.TestCase`; monkey-patch module singletons or pass fakes in `setUp`, restore in `tearDown` (see `tests/test_ingestor.py:28-51`)

**New Dialog/Window:**
- Implementation: `app/ui/<feature>_picker.py` (or reuse the dialog pattern in `app/ui/device_picker.py`) — `QDialog` subclass with a `tr()` method, `_build_ui()`, and `accept()` returning the selected value
- Use `QDialog` (not `QWidget`) for proper QSS styling and window modal semantics — see `app/ui/project_wizard.py:11` as the reference pattern
- Add its source path to `tools/update_translations.ps1` `$sources` list so `lupdate` picks up new strings

**New Device Backend (MTP/FTP-style):**
- Implementation: subclass `MtpBackend` in `app/core/<proto>.py`, implement `list_devices()` + `_open_session()` returning a session with `storages()`, `_resolve()`, `_enum_children()`, `download()` — staging is then free via `_stage_session` (see `app/core/ftp.py:338-477` as the template)
- Use a stable `device_id` prefix (`ftp:` pattern in `app/core/ftp.py:68-79`) so sessions and the cache dir keying stay deterministic

**New DB Table:**
- Add `CREATE TABLE IF NOT EXISTS` in `DatabaseManager.create_tables()` (`app/core/db.py:31-290`)
- Add migration with `PRAGMA table_info()` + `ALTER TABLE ADD COLUMN` for any new columns
- Add CRUD methods on `DatabaseManager` following the existing pattern (get_connection → cursor → execute → commit → close)

**New Per-Device Setting:**
- Add column to `device_settings` table (`app/core/db.py:247-251`)
- Add `get_<setting>()` / `set_<setting>()` methods on `DatabaseManager` (`app/core/db.py:960-985` pattern)
- Read in `MainWindow.start_ingest()` to override session-level defaults (`app/ui/main_window.py:1496-1499`)
- Add toggle button in `source_list` column 2 via `_build_<setting>_button()` pattern (`app/ui/main_window.py:2176-2196`)

**Utilities:**
- Shared helpers: `app/core/utils.py` (path/disk/MD5 helpers); translation helpers belong in `app/core/translator.py`; theme colors in `app/ui/theme.py` — never hardcode colors in widgets
- Icon SVGs: add to `app/ui/assets/icons/` with `#FF00FF` placeholder color; `app/ui/icons.py` auto-tints them

**New Background Work:**
- Short tasks: `_TaskWorker`/`_StageWorker` QThread pattern in `app/ui/main_window.py:91-147`
- Continuous polling: daemon `threading.Thread` loop like `FileSystemWatcher` (`app/core/watcher.py`) or `ShootInboxServer` (`app/core/shoot_inbox.py:441-472`)
- Camera detection: background thread with `QTimer` timeout and token-based cancellation (`app/ui/main_window.py:2309-2378`)

## Special Directories

**`data/`:**
- Purpose: Runtime state — SQLite DB, inbox cache, device staging cache, default project roots
- Generated: Yes (at runtime, first launch)
- Committed: No (gitignored via `data/` in `.gitignore`)

**`Footage/`:**
- Purpose: Default dump output root (`<project>/Footage/<Camera>/<Date>`)
- Generated: Yes
- Committed: No (`Footage/` in `.gitignore`)

**`graphify-out/`:**
- Purpose: Knowledge-graph cache generated by the graphify tooling
- Generated: Yes
- Committed: No (`graphify-out/` in `.gitignore`)

**`app/i18n/`:**
- Purpose: Translation catalogs; `.ts` is source, `.qm` is compiled and shipped
- Generated: Partial (`.qm` is produced by `tools/update_translations.ps1`; `.ts` is maintained via lupdate + `tools/translate_en.py`)
- Committed: Yes (both `.ts` and `.qm` are versioned)

**`app/sounds/`:**
- Purpose: Bundled notification sounds
- Generated: No (checked in), but `NotificationManager` regenerates copies at runtime if missing
- Committed: Yes

**`app/ui/assets/`:**
- Purpose: SVG tiles for the animated wheat background, logo variants, and icon SVGs
- Generated: No
- Committed: Yes

**`app/ui/assets/icons/`:**
- Purpose: SVG icon sources with `#FF00FF` placeholder color, tinted by `app/ui/icons.py`
- Generated: No
- Committed: Yes

**`__pycache__/`, `.pytest_cache/`:**
- Purpose: Python bytecode and pytest caches
- Generated: Yes
- Committed: No (gitignored)

---

*Structure analysis: 2026-08-17*
