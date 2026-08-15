# Technology Stack

**Analysis Date:** 2026-08-15

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
- `PySide6>=6.5,<7` - The whole GUI, threading via signals, i18n, settings
- `comtypes>=1.4.0` - COM interop for Windows Portable Devices (MTP phone/camera access) in `app/core/mtp.py`
- `qrcode>=7.4` - Generates the QR codes for phone WiFi upload in `app/ui/wifi_panel.py`

**Infrastructure:**
- FFmpeg/ffprobe - External CLI tools (expected in `PATH`), invoked via `subprocess` for metadata (`app/core/metadata_engine.py`) and proxy generation (`app/core/ffmpeg_utils.py`). Not a pip dependency — documented requirement in `README.md`
- SQLite - stdlib `sqlite3`, WAL mode, no ORM (`app/core/db.py`)
- `ftplib` - stdlib FTP client for phone FTP ingestion (`app/core/ftp.py`)
- `http.server.ThreadingHTTPServer` - stdlib embedded HTTP server for WiFi file reception (`app/core/shoot_inbox.py`)
- `ctypes`/`winsound`/`win32` kernel32 calls - Windows-specific drive detection, volume labels, sound (`app/core/utils.py`, `app/core/notifications.py`, `app/core/sd_reader.py`)

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

---

*Stack analysis: 2026-08-15*
