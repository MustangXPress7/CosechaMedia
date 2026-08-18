# Technology Stack

**Analysis Date:** 2026-08-17

## Languages

**Primary:**
- Python 3.11 - Entire application (`main.py`, `app/`, `tools/`, `tests/`). The GitHub Actions build pins `python-version: '3.11'` in `.github/workflows/build.yml`; `tools/update_translations.ps1` references `Python311` explicitly.

**Secondary:**
- HTML/CSS/JavaScript - Embedded upload page served by the PairDrop-style WiFi inbox (`_PAGE_TEMPLATE` in `app/core/shoot_inbox.py`)
- Batch/PowerShell/Bash - Build scripts: `Compilar.bat`, `setup_mac.command`, `tools/update_translations.ps1`

## Runtime

**Environment:**
- Desktop application distributed as a compiled binary (PyInstaller onefile) — runs on Windows, macOS, Linux. `app/core/updater.py` gates self-update on `sys.frozen`.
- `sys.executable`-adjacent `data/` directory holds runtime state (SQLite DB + caches) when frozen; `os.getcwd()`/`data/` in dev (`app/core/db.py:_resolve_db_path`).

**Package Manager:**
- pip (via `python -m pip install -r requirements.txt` in `Compilar.bat` and `setup_mac.command`)
- Lockfile: missing — only `requirements.txt` with loose constraints (`PySide6>=6.5,<7`, `comtypes>=1.4.0`, `qrcode>=7.4`)

## Frameworks

**Core:**
- PySide6 (Qt 6, `>=6.5,<7`) - Entire UI (`app/ui/`), signals/slots, `QTranslator` i18n, `QSettings` persistence, `QApplication` in `main.py`
- PyInstaller - Packaging; config in `main.spec`; invoked by `Compilar.bat`, `setup_mac.command`, and `.github/workflows/build.yml`

**Testing:**
- Python stdlib `unittest` - All 14 test files in `tests/` use `unittest.TestCase`; Qt widget tests use `QApplication`/`QTest` offscreen (e.g., `tests/test_selective_dump.py`, `tests/test_e2e.py`)
- `unittest.mock` - Mocking (`tests/test_updater.py`, `tests/test_ftp.py`)
- `.pytest_cache/` present — pytest can run the unittest suites (pytest runner is used, not a hard dependency)

**Build/Dev:**
- PyInstaller `main.spec` - Bundles `app/ui/logo.png`, `app/ui/assets`, `app/sounds`, `app/i18n` as datas
- GitHub Actions - `.github/workflows/build.yml` builds Windows/macOS/Linux on `v*` tags

## Key Dependencies

**Critical:**
- `PySide6>=6.5,<7` - The whole GUI, threading via signals, i18n, settings, `QSvgRenderer` (for tinted SVG icons in `app/ui/icons.py`)
- `comtypes>=1.4.0` - COM interop for Windows Portable Devices (MTP phone/camera access) in `app/core/mtp.py`
- `qrcode>=7.4` - Generates the QR codes for phone WiFi upload in `app/ui/wifi_panel.py`

**Infrastructure:**
- FFmpeg/ffprobe - External CLI tools (expected in `PATH`), invoked via `subprocess` for metadata (`app/core/metadata_engine.py`) and proxy generation (`app/core/ffmpeg_utils.py`). Not a pip dependency — documented requirement in `README.md`
- SQLite - stdlib `sqlite3`, WAL mode, no ORM (`app/core/db.py`)
- `ftplib` - stdlib FTP client for phone FTP ingestion (`app/core/ftp.py`)
- `http.server.ThreadingHTTPServer` - stdlib embedded HTTP server for WiFi file reception (`app/core/shoot_inbox.py`)
- `ctypes`/`winsound`/`win32` kernel32 calls - Windows-specific drive detection, volume labels, sound, volume serial detection (`app/core/utils.py`, `app/core/notifications.py`, `app/core/sd_reader.py`)

## Configuration

**Environment:**
- No `.env` files and no `os.environ` reads anywhere in `app/` — zero environment-variable configuration
- App settings persisted via Qt `QSettings` (`QSettings().value("language", ...)` in `app/core/translator.py`, `theme` key in `app/ui/theme.py`; org "Audiovisual Production", app "CosechaMedia" set in `main.py`)
- User data in `data/`: `data/sd_import.db` (SQLite), `data/inbox/<alias>` (WiFi receive cache), `data/device_cache/<sha1(device_id)>/<folder>` (MTP/FTP staging cache), `data/projects/<name>` (default project root)

**Build:**
- `main.spec` - PyInstaller analysis/EXE config
- `.github/workflows/build.yml` - Cross-platform CI build + release
- `Compilar.bat` (Windows local build), `setup_mac.command` (macOS local build)
- Version source of truth: `app/__init__.py` (`__version__ = "1.2.1"`); CI validates the git tag matches it

## Database Schema (Runtime)

**Tables** (`data/sd_import.db` via `app/core/db.py:create_tables`):

| Table | Purpose | Notable columns |
|-------|---------|-----------------|
| `projects` | Project config (org, duration, dump path, proxy settings) | `dump_path`, `delicate_mode`, `camera_detection_mode`, `generate_proxies`, `proxy_resolution` |
| `sessions` | Per-source ingest sessions | `device_id`, `device_folder`, `camera_name`, `content_filter`, `delicate_mode`, `enabled` |
| `files` | Copied file records with MD5 verification | `dump_location_id` (multi-target support) |
| `sd_cards` | SD card serial→camera mapping | `serial` (UNIQUE), `camera_name` (I-03), `brand`, `model`, `capacity_gb` |
| `device_settings` | Per-device configuration (B-14) | `device_key` (TEXT PK), `delicate_mode` (INTEGER DEFAULT 0) |
| `dump_locations` | Multi-target dump paths per project | `path`, `label`, `include_date`, `include_camera`, `order_index` |
| `cameras` | Camera definitions | `name`, `folder_name` |
| `recent_paths` | MRU source/dest paths | `path`, `path_type`, `use_count` |
| `ftp_profiles` | Saved FTP connection profiles | `host`, `port`, `username`, `password`, `passive`, `timeout` |
| `inbox_senders` | WiFi upload sender identities | `name`, `location`, `token` (bearer) |
| `containers` | Recognized file extensions | `.mp4`, `.mov`, `.jpg`, `.cr2`, etc. |
| `footage_folders` | Configurable footage folder names | `Footage`, `Material`, `Rodaje`, etc. |

**Migration strategy:** additive `ALTER TABLE ... ADD COLUMN` with `PRAGMA table_info` checks plus backfill inside `create_tables()`. No version numbering; new columns are detected at startup.

## New DB Methods (Recent Additions)

- `DatabaseManager.save_card_camera(volume_serial, camera_name, brand, model)` — maps an SD card volume serial to a camera name (`app/core/db.py:914`). Upserts into `sd_cards`.
- `DatabaseManager.get_camera_for_card(volume_serial)` → `Optional[str]` — retrieves the remembered camera name for a card serial (`app/core/db.py:945`).
- `DatabaseManager.get_device_delicate(device_key)` → `Optional[int]` — reads the delicate mode flag from `device_settings` (`app/core/db.py:960`).
- `DatabaseManager.set_device_delicate(device_key, delicate)` — persists the per-device delicate mode (`app/core/db.py:974`).

## UI Components (Recent Additions)

**`ElidedLabel`** (`app/ui/main_window.py:149`):
- Custom `QLabel` subclass that elides text with `...` via `QFontMetrics.elidedText(ElideMiddle)` when the path is too long for the column width.
- Used in source_list column 0 to display long file paths without overflow.

**`source_list` QTableWidget** (`app/ui/main_window.py:420`):
- 5-column table: `[Path | Camera | Delicate toggle | Content filter | Remove]`
- Column widths: 300px (path), 150px (camera), 32px (delicate), 100px (content), 40px (remove)
- Column 0 uses a composite cell widget: checkbox + `ElidedLabel` + optional device button (QR/FTP)
- Column 1 camera cell is editable only when `camera_detection_mode == "manual"`
- Column 2 is a ⚡/🐌 toggle button for per-device delicate mode (B-14)
- Column 3 opens the content filter dialog
- Auto-sizing via `_update_source_list_height()` (B-06)

**Device Delicate Toggle** (`app/ui/main_window.py:2176`):
- `_build_delicate_button()` creates a 24×24 `QPushButton` with ⚡ (normal) or 🐌 (delicate) icon
- Reads/writes `db.get_device_delicate()` / `db.set_device_delicate()` per device key
- Device key derived from `session.device_id` or `sd_reader.get_volume_serial()` fallback
- 3-tier override chain: `device_settings` > `session.delicate_mode` > `project.delicate_mode`

**`SessionsBox`** (`app/ui/main_window.py:470`):
- `QGroupBox("Sesiones")` with `objectName = "SessionsBox"`, styled via QSS (`#SessionsPanel` in `app/ui/theme.py:584`)
- Contains: session combo (`sessions_combo`), new/delete session buttons, source label, camera name, config overrides

**`ProjectWizard`** (`app/ui/project_wizard.py:11`):
- Now inherits `QDialog` (was `QWidget`), enabling modal `exec()` behavior and proper dialog semantics (I-12 fix)

**`icons.py` SVG Icon System** (`app/ui/icons.py`):
- Replaces unicode/emoji button glyphs with tinted SVG icons from `app/ui/assets/icons/`
- Uses `QSvgRenderer` + placeholder color replacement + weakref registry for theme-aware re-tinting
- Called via `icons.apply(button, "name", size=N)` throughout UI

## Platform Requirements

**Development:**
- Python 3.11
- FFmpeg and ffprobe in `PATH` (metadata + proxy generation)
- Windows: WPD COM typelibs `portabledeviceapi.dll` / `portabledevicetypes.dll` present (standard on Windows) for MTP support
- PyInstaller installed for packaging

**Production:**
- End users receive compiled binaries from GitHub Releases (`CosechaMedia-windows-x86_64.exe`, `CosechaMedia-macos.app.zip`, `CosechaMedia-linux-x86_64`) — no Python runtime needed
- FFmpeg/ffprobe still required at runtime on the machine
- MTP import is Windows-only; FTP/WiFi ingestion is cross-platform
- Windows volume serial detection (`GetVolumeInformationW`) is Windows-only; `get_volume_serial()` returns `None` on other platforms

---

*Stack analysis: 2026-08-17*
