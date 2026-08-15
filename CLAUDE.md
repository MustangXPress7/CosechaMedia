<!-- GSD:project-start source:PROJECT.md -->

## Project

**CosechaMedia**

Aplicación de escritorio (PySide6/Qt 6, Python 3.11) para producción audiovisual: ingesta verificada (MD5) de tarjetas SD, cámaras y teléfonos (MTP/USB, FTP, WiFi vía PairDrop-style HTTP) a un archivo organizado por cámara/fecha, con detección de metadatos via ffprobe, generación de proxies, rotación de discos y formateo de tarjetas. Orientada a operadores de cámara/plataforma de rodaje en local (sin nube).

**Core Value:** Que el operador de cámara pueda vaciar tarjetas SD/cámaras/móviles al archivo del proyecto de forma fiable y sin perder datos — cada archivo copiado con verificación de integridad y organizado correctamente.

### Constraints

- **Tech stack**: PySide6 (Qt 6, `>=6.5,<7`), Python 3.11 — no cambiar framework
- **Idioma fuente**: español (los strings UI son literales en ES; catálogo EN via `.ts`/`.qm`) — los textos nuevos deben pasar por `tr()`
- **Compatibilidad**: Windows (incl. MTP COM), macOS, Linux — cambios UI cross-platform
- **No refactor core**: la revisión UI no debe tocar `app/core/` salvo necesidad mínima; los cambios son de `app/ui/`
- **Estética**: mantener tema oscuro/claro + acentos existentes

<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->

## Technology Stack

## Languages

- Python 3.11 - Entire application (`main.py`, `app/`, `tools/`, `tests/`). The GitHub Actions build pins `python-version: '3.11'` in `.github/workflows/build.yml`; `tools/update_translations.ps1` references `Python311` explicitly.
- HTML/CSS/JavaScript - Embedded upload page served by the PairDrop-style WiFi inbox (`_PAGE_TEMPLATE` in `app/core/shoot_inbox.py`)
- Batch/PowerShell/Bash - Build scripts: `Compilar.bat`, `setup_mac.command`, `tools/update_translations.ps1`

## Runtime

- Desktop application distributed as a compiled binary (PyInstaller onefile) — runs on Windows, macOS, Linux. `app/core/updater.py` gates self-update on `sys.frozen`.
- `sys.executable`-adjacent `data/` directory holds runtime state (SQLite DB + caches) when frozen; `os.getcwd()`/`data/` in dev (`app/core/db.py:_resolve_db_path`).
- pip (via `python -m pip install -r requirements.txt` in `Compilar.bat` and `setup_mac.command`)
- Lockfile: missing — only `requirements.txt` with loose constraints (`PySide6>=6.5,<7`, `comtypes>=1.4.0`, `qrcode>=7.4`)

## Frameworks

- PySide6 (Qt 6, `>=6.5,<7`) - Entire UI (`app/ui/`), signals/slots, `QTranslator` i18n, `QSettings` persistence, `QApplication` in `main.py`
- PyInstaller - Packaging; config in `main.spec`; invoked by `Compilar.bat`, `setup_mac.command`, and `.github/workflows/build.yml`
- Python stdlib `unittest` - All 14 test files in `tests/` use `unittest.TestCase`; Qt widget tests use `QApplication`/`QTest` offscreen (e.g., `tests/test_selective_dump.py`, `tests/test_e2e.py`)
- `unittest.mock` - Mocking (`tests/test_updater.py`, `tests/test_ftp.py`)
- `.pytest_cache/` present — pytest can run the unittest suites (pytest runner is used, not a hard dependency)
- PyInstaller `main.spec` - Bundles `app/ui/logo.png`, `app/ui/assets`, `app/sounds`, `app/i18n` as datas
- GitHub Actions - `.github/workflows/build.yml` builds Windows/macOS/Linux on `v*` tags

## Key Dependencies

- `PySide6>=6.5,<7` - The whole GUI, threading via signals, i18n, settings
- `comtypes>=1.4.0` - COM interop for Windows Portable Devices (MTP phone/camera access) in `app/core/mtp.py`
- `qrcode>=7.4` - Generates the QR codes for phone WiFi upload in `app/ui/wifi_panel.py`
- FFmpeg/ffprobe - External CLI tools (expected in `PATH`), invoked via `subprocess` for metadata (`app/core/metadata_engine.py`) and proxy generation (`app/core/ffmpeg_utils.py`). Not a pip dependency — documented requirement in `README.md`
- SQLite - stdlib `sqlite3`, WAL mode, no ORM (`app/core/db.py`)
- `ftplib` - stdlib FTP client for phone FTP ingestion (`app/core/ftp.py`)
- `http.server.ThreadingHTTPServer` - stdlib embedded HTTP server for WiFi file reception (`app/core/shoot_inbox.py`)
- `ctypes`/`winsound`/`win32` kernel32 calls - Windows-specific drive detection, volume labels, sound (`app/core/utils.py`, `app/core/notifications.py`, `app/core/sd_reader.py`)

## Configuration

- No `.env` files and no `os.environ` reads anywhere in `app/` — zero environment-variable configuration
- App settings persisted via Qt `QSettings` (`QSettings().value("language", ...)` in `app/core/translator.py`, `theme` key in `app/ui/theme.py`; org "Audiovisual Production", app "CosechaMedia" set in `main.py`)
- User data in `data/`: `data/sd_import.db` (SQLite), `data/inbox/<alias>` (WiFi receive cache), `data/device_cache/<sha1(device_id)>/<folder>` (MTP/FTP staging cache), `data/projects/<name>` (default project root)
- `main.spec` - PyInstaller analysis/EXE config
- `.github/workflows/build.yml` - Cross-platform CI build + release
- `Compilar.bat` (Windows local build), `setup_mac.command` (macOS local build)
- Version source of truth: `app/__init__.py` (`__version__ = "1.2.1"`); CI validates the git tag matches it

## Platform Requirements

- Python 3.11
- FFmpeg and ffprobe in `PATH` (metadata + proxy generation)
- Windows: WPD COM typelibs `portabledeviceapi.dll` / `portabledevicetypes.dll` present (standard on Windows) for MTP support
- PyInstaller installed for packaging
- End users receive compiled binaries from GitHub Releases (`CosechaMedia-windows-x86_64.exe`, `CosechaMedia-macos.app.zip`, `CosechaMedia-linux-x86_64`) — no Python runtime needed
- FFmpeg/ffprobe still required at runtime on the machine
- MTP import is Windows-only; FTP/WiFi ingestion is cross-platform

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

## Language & Runtime Context

- Python 3.11 desktop application (PySide6/Qt), packaged with PyInstaller (`main.spec`).
- No linting or formatting configuration exists in the repo: no `pyproject.toml`, `setup.cfg`, `ruff.toml`, `.flake8`, `.pylintrc`, or `.prettierrc`. Code follows an informal PEP 8 style (4-space indent, snake_case, 88–120 char lines tolerated — e.g. `app/core/db.py:297`).
- Source modules: `app/core/` (business logic) and `app/ui/` (Qt interface). Tests in `tests/`.

## Naming Patterns

- snake_case matching the module's main symbol: `app/core/metadata_engine.py`, `app/core/db.py`, `app/ui/main_window.py`.
- Test files: `tests/test_<module>.py` (`test_db.py`, `test_ingestor.py`).
- PascalCase: `DatabaseManager` (`app/core/db.py:20`), `Ingestor` (`app/core/ingestor.py:114`), `MainWindow` (`app/ui/main_window.py:149`), `DumpTarget` (`app/core/ingestor.py:91`).
- Exception classes end in `Error`: `UpdateError` (`app/core/updater.py:32`), `MtpError` (`app/core/mtp.py:29`).
- Non-exported UI/helper classes prefixed with `_`: `_SilentMessageBox` (`app/core/notifications.py:12`), `_StageWorker`, `_TaskWorker` (`app/ui/main_window.py:91,130`).
- PySide6 `QObject`/`QMainWindow`/`QDialog` subclasses declare Qt signals at class level: `file_started = Signal(str)` etc. (`app/core/ingestor.py:115-121`).
- snake_case: `get_connection`, `create_session`, `handle_new_file`, `date_key_for_file`.
- Module-private helpers get a leading `_`: `_free_space` (`app/core/ingestor.py:24`), `_is_system_entry` (`app/core/metadata_engine.py:26`), `_parse_version` (`app/core/updater.py:41`), `_windows_mounted_drives` (`app/core/utils.py:53`).
- Private methods of classes also use `_`: `_process_single_file`, `_copy_verified`, `_determine_date` (`app/core/ingestor.py`). Tests exercise these private methods directly (`self.ing._process_single_file(...)` in `tests/test_ingestor.py:65`) — private methods are part of the testable surface.
- snake_case instance attributes, including private ones with `_` prefix: `self._stop_event`, `self._inflight_lock`, `self._session_file` (`app/core/ingestor.py:148-181`).
- Window/panel widgets on `MainWindow` are public attributes (`self.window.btn_start`, `self.window.table`, `self.window.source_list` in `tests/test_e2e.py`, `tests/test_wifi_source.py`).
- UPPER_SNAKE constants at module level: `WIFI_DEVICE_ID = "wifi:pairdrop"` (`app/core/db.py:18`), `VIDEO_EXTENSIONS` (`app/core/metadata_engine.py:11`), `_SYSTEM_DIR_NAMES` (`app/core/metadata_engine.py:17`), `DEFAULT_THEME`, `ACCENTS` (`app/ui/theme.py`).
- Type hints are used throughout (PEP 484 with `from typing import Optional, Dict, List, Tuple, Callable, Set` — see `app/core/ingestor.py:8`, `app/core/db.py:6`). Newer code also uses bare builtins in annotations (`metadata: dict` in `app/core/metadata_engine.py:76`, `set` return in `app/core/metadata_engine.py:386`). Prefer `Optional[X]` for nullable values; `-> None` on mutating methods.
- `@dataclass` used for value objects: `DeviceInfo`, `RemoteFile` (`app/core/mtp.py:33-48`).

## Code Style

- No formatter is configured. Follow the existing style: 4-space indentation, two blank lines between top-level defs, blank line before class methods.
- Quote style: single quotes dominate (`app/core/ingestor.py:44`, `app/core/metadata_engine.py:11`) but double quotes appear in QSS strings and some dict literals (`app/ui/theme.py`, `app/core/db.py`). Match the surrounding file.
- Long SQL/string literals are broken with implicit concatenation across lines (`app/core/db.py:433-438`).
- Not detected — no linter config or linter dependency in `requirements.txt`. There is a `__pycache__` for Python 3.11 (`.pyc` files in `app/core/__pycache__/`).

## Import Organization

- No path aliases — imports are relative to repo root via the `app` package: `from app.core.db import db`, `from app.ui import theme`, `from app.core import ftp, mtp`.
- `tests/__init__.py:11` inserts the repo root into `sys.path` so `from app...` imports work under `python -m unittest`.
- Platform-specific or one-off heavy modules are imported inside functions: `import ctypes` (`app/core/utils.py:54,124`), `import shutil` (`app/core/sd_reader.py:46`), `import hashlib` (`app/core/ingestor.py:36`), `import subprocess` (`app/ui/main_window.py:54`). Follow this pattern for platform-gated code.

## Error Handling

- Core modules catch broad `Exception`, log via `print(f"Error <action> <path>: {e}")`, and return safe defaults — the desktop app must never crash:
- Bare `except:` is used in a few places to deliberately swallow errors: `app/core/ingestor.py:201,520` (session save, file move), `app/core/sd_reader.py:73,88,100,112,124` (best-effort card detection). Avoid adding new bare `except:`; use `except Exception` with a comment when swallowing is intentional.
- Custom exception types for domain errors that must propagate: `UpdateError` (`app/core/updater.py`), `MtpError` (`app/core/mtp.py`).
- Background work pattern: QObject worker classes catch exceptions in `run()` and emit them through Qt signals — `self.done.emit(False, str(e))` (`app/ui/main_window.py:106-147`, `_StageWorker`, `_TaskWorker`).
- User-facing errors: `QMessageBox` for blocking UI (`app/ui/notifications.py`, `app/ui/main_window.py`) and `raise RuntimeError(translator.tr("..."))` for precondition violations (`app/ui/main_window.py:50`).
- Long-running operations report progress via callback or dict-return instead of exceptions: `Ingestor._stats` with `processed/errors/skipped` (`app/core/ingestor.py:167-172`), `stage_device_folder` results dict with `errors` (`app/core/mtp.py`, `app/core/ftp.py`).

## Logging

- `print(f"Error <action> <path/context>: {e}")` in exception handlers (16 call sites, e.g. `app/core/ingestor.py:69,299,384`, `app/core/utils.py:50`, `app/core/metadata_engine.py:257`, `app/ui/main_window.py:146`).
- `print(f"Watcher started on: {self.source_dir}")` for lifecycle info (`app/core/watcher.py:27`).
- Do not add a logging framework without a deliberate decision; match the `print(f"...")` style.

## Comments

- Comments explain **why**, not what: e.g. `app/core/metadata_engine.py:31` explains why system dirs must be skipped; `app/core/watcher.py:39-41` explains a Windows path-checking pitfall.
- Section separator banners with `# -----...` used in `app/core/mtp.py:51-53,107-109`.
- Comments are predominantly **Spanish**; English appears in older code. Match the dominant language of the file (Spanish).
- Not applicable (Python). Docstrings are triple-quoted (`"""..."""`) and predominantly Spanish:

## Function Design

- Constructors with many optional parameters use keyword defaults: `Ingestor.__init__` takes 14 parameters (`app/core/ingestor.py:123-132`); `DatabaseManager(db_path=None)` (`app/core/db.py:21`).
- Callbacks are passed as keyword args with `None` defaults: `progress_cb`, `cancel_cb`, `on_error` (throughout `app/core/`).
- Public DB methods use `**kwargs` with an allowlist filter (`update_session_config` at `app/core/db.py:503-511`, `update_ftp_profile` at `app/core/db.py:653`).
- Success/failure as booleans (`copy_verified` returns `bool`), dicts with status keys, or `None` for "not found" (`get_session` returns `None`, `app/core/db.py:479`).
- Consistent stats dict shapes across stages: `{"staged", "skipped", "errors"}` for MTP/FTP staging; `{"processed", "errors", "skipped"}` for ingest.

## Module Design

- Modules define classes and module-level singleton instances: `db = DatabaseManager()` (`app/core/db.py:863`), `metadata_engine = MetadataEngine()` (`app/core/metadata_engine.py:429`), `sd_reader = SDReader()` (`app/core/sd_reader.py:179`).
- Consumer modules import the singleton and call it directly: `from app.core.db import db`, `from app.core.metadata_engine import metadata_engine` (`app/core/ingestor.py:9-11`, `app/ui/main_window.py:17-22`).
- Tests monkeypatch attributes of these singletons or replace the module-level reference (`ingestor_module.db = self.db` in `tests/test_ingestor.py:40`) — keep singletons attribute-replaceable at module scope.

## Cross-Cutting Conventions

- Every user-facing string goes through translation: `translator.tr("...")` at module level or `self.tr("...")` inside QWidget/QObject classes (`app/core/translator.py:69-71`). Interpolation uses Qt placeholders: `translator.tr("Formateando %1 (%2/%3)...").arg(path).arg(i).arg(len(paths))` (`app/ui/main_window.py:67`).
- Default language is Spanish (`DEFAULT_LANGUAGE = "es"`, `app/core/translator.py:15`). New UI text must be wrapped in `tr()` or it will not appear in Spanish/English switch.
- `sys.platform` branching with dedicated per-platform helpers (`app/core/utils.py:53-119`, `app/core/updater.py:77-82`).
- PyInstaller detection via `getattr(sys, "frozen", False)` for resource paths (`app/core/utils.py:9`, `app/core/db.py:9`, `app/core/updater.py:170`).
- Use `resource_path()` (`app/core/utils.py:6`) for any bundled asset path.
- Qt signals for cross-thread UI updates; `threading.Lock` for shared counters/sets (`Ingestor._inflight_lock`, `_target_lock` in `app/core/ingestor.py`).
- SQLite connections created per-operation with `check_same_thread=False` and `WAL` (`app/core/db.py:26-28`); always `conn.commit()` then `conn.close()` after use.

<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

## System Overview

```text

```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| `MainWindow` | Orchestrates everything: project/session CRUD, source registration, ingest start/stop, wifi/FTP/MTP flows, post-ingest actions, auto-sync, updates | `app/ui/main_window.py` |
| `Ingestor` | Verified (MD5) file copy pipeline, camera/date resolution, multi-disk rotation, resume state, Qt signals for UI progress | `app/core/ingestor.py` |
| `FileSystemWatcher` | Polls a source dir on a daemon thread and feeds new files to an `Ingestor` | `app/core/watcher.py` |
| `MetadataEngine` | ffprobe metadata extraction (camera, date, codec, fps), LRU cache with mtime invalidation, file type classification | `app/core/metadata_engine.py` |
| `FFmpegProcessor` | Proxy (720p/1080p) generation via `ffmpeg` subprocess | `app/core/ffmpeg_utils.py` |
| `DatabaseManager` | SQLite schema, migrations (ALTER TABLE backfill), sessions/projects/files/containers/FTP profiles/inbox senders | `app/core/db.py` |
| `MtpBackend` / `WpdBackend` | Device abstraction interface + real Windows WPD COM implementation; incremental staging with manifest | `app/core/mtp.py` |
| `FtpBackend` | FTP implementation of the MtpBackend session interface; subnet discovery; passive/active auto-flip | `app/core/ftp.py` |
| `ShootInboxServer` | Embedded `ThreadingHTTPServer` receiving phone uploads (PairDrop-style); per-sender tokens; `.part` uploads | `app/core/shoot_inbox.py` |
| `SDReader` | SD card info detection (brand/model/serial from filesystem + video metadata) | `app/core/sd_reader.py` |
| `NotificationManager` | Ingest-complete/error sounds + dialogs | `app/core/notifications.py` |
| `updater` | GitHub Releases check, SHA-256 verify, platform install helpers (Windows/macOS/Linux) | `app/core/updater.py` |
| `theme` | Single palette source; QSS template with `@key` placeholders; dark/light + accents | `app/ui/theme.py` |
| Dialogs | `DevicePickerDialog`, `FtpPickerDialog`, `SourcePickerDialog`, `SelectiveDumpAssistant`, `WifiMethodDialog`, `ShootInboxPanel`, `AboutDialog`, `ProjectWizard` | `app/ui/*.py` |

## Pattern Overview

- **Signal-driven progress:** Core emits Qt `Signal`s (e.g. `Ingestor.file_finished`, `copy_progress`, `ingest_complete`) that the UI connects to for safe cross-thread updates (`app/core/ingestor.py:115-121`, connected in `app/ui/main_window.py:1482-1494`)
- **Reactive ingestion:** `FileSystemWatcher` polls source dirs and pushes each new file into `Ingestor.handle_new_file`; the Ingestor dedupes, classifies, and dispatches to a `ThreadPoolExecutor` (`app/core/ingestor.py:235-262`)
- **Backend-interface reuse:** `MtpBackend` (interface) is implemented by `WpdBackend` (COM) and `FtpBackend` (network); both share the incremental staging engine `_stage_session` (`app/core/mtp.py:55-104`, `app/core/ftp.py:338`)
- **SQLite as system of record:** projects, sessions, files, cameras, containers, FTP profiles, inbox senders — all in one DB via `DatabaseManager` (`app/core/db.py:20`)
- **Frozen-aware paths:** `resource_path()` and `_resolve_db_path()` switch between `sys._MEIPASS`/`sys.executable` (PyInstaller) and repo-relative paths in dev (`app/core/utils.py:6-12`, `app/core/db.py:8-15`)

## Layers

- Purpose: Present the interface, capture user intent, render progress
- Location: `app/ui/`
- Contains: `MainWindow`, picker dialogs, wizard, wifi panel, theme, wheat-field background painter, logos
- Depends on: `app/core` (all modules), Qt
- Used by: `main.py` only (`app/ui/main_window.py` imports every other UI module)
- Purpose: Business logic — ingest, metadata, device access, storage, updates, i18n
- Location: `app/core/`
- Contains: 12 modules; the only Qt dependency is `QObject`/`Signal` (in `app/core/ingestor.py` and `app/core/translator.py`) plus `QMessageBox` (in `app/core/notifications.py`)
- Depends on: stdlib (`sqlite3`, `subprocess`, `ftplib`, `http.server`, `threading`, `concurrent.futures`), `PySide6.QtCore`, `comtypes` (Windows), external CLIs (ffmpeg/ffprobe), GitHub API
- Used by: `app/ui/`, `tests/`
- Purpose: Persistent state and media output
- Location: `data/` (runtime, gitignored)
- Contains: `data/sd_import.db` (SQLite, WAL), `data/inbox/<alias>` (WiFi receive cache), `data/device_cache/<sha1(device_id)>/<folder>` (MTP/FTP staging + `.sync_manifest.json`), `data/projects/<name>` (default project roots), plus the configured `Footage/` dump roots

## Data Flow

### Primary Request Path — SD card ingest

### Device staging flow (MTP/USB and FTP/WiFi)

### WiFi inbox flow (PairDrop-style)

- **Persistent state:** SQLite via `DatabaseManager` (`app/core/db.py`) — projects, sessions, files, containers, footage folders, FTP profiles, inbox senders
- **Resume state:** `Ingestor` persists copied-file sets to `.sdimport_session_<id>.json` beside the destination root; a legacy `.sdimport_session.json` is also read (`app/core/ingestor.py:155-202`)
- **In-memory UI state:** `MainWindow` attributes for project/session config, `_ingestors`, `watchers`, `_file_row_map` (`app/ui/main_window.py:163-191`)
- **Settings:** Qt `QSettings` (org "Audiovisual Production", app "CosechaMedia") — language, theme, accent, camera detection mode, window geometry (`app/ui/theme.py:8-13`, `app/core/translator.py:38`)
- **Thread-state:** `_inflight`, `_remaining_watchers`, `_complete_emitted` guarded by `_inflight_lock` to decide when an ingest is truly complete (`app/core/ingestor.py:178-233`)

## Key Abstractions

- Purpose: Uniform access to phones/cameras, whether over USB (WPD/COM) or FTP
- Examples: `app/core/mtp.py` (interface + `WpdBackend`), `app/core/ftp.py` (`FtpBackend`)
- Pattern: Backend classes expose `list_devices()` and `_open_session()`; sessions must provide `storages()`, `_resolve()`, `_enum_children()`, `download()`. The shared staging engine `_stage_session` consumes only that session surface (`app/core/mtp.py:597-638`). FTP identity is `ftp:<profile_id>`; MTP identity is the WPD PnP id (`app/core/ftp.py:68-79`)
- Purpose: Copy any source (card, inbox cache, device cache) into the project with MD5 verification, camera/date organization, disk rotation, and progress signals
- Examples: `app/core/ingestor.py`, reused by `MainWindow.start_ingest`, `_start_wifi_ingestor`, `_ensure_wifi_ingestion`
- Pattern: `QObject` + `ThreadPoolExecutor`; external events (`handle_new_file`) are serialized through `processed_files` and a stop event; completion is tracked with an inflight/watcher counter
- Purpose: One shared service instance across UI and core
- Examples: `db = DatabaseManager()` (`app/core/db.py:863`), `metadata_engine = MetadataEngine()` (`app/core/metadata_engine.py:429`), `ffmpeg = FFmpegProcessor()` (`app/core/ffmpeg_utils.py:59`), `sd_reader = SDReader()` (`app/core/sd_reader.py:179`)
- Pattern: module-scope instance; tests monkey-patch the module attribute to inject fakes (e.g. `ingestor_module.db = self.db` in `tests/test_ingestor.py:40`)
- Purpose: Single source of color truth; a QSS template with `@key` placeholders is filled per theme/accent
- Examples: `app/ui/theme.py` (`DARK`/`LIGHT` palettes, `ACCENTS`, `_QSS_TEMPLATE`), `theme.color(...)` used throughout UI files
- Pattern: palettes are dicts; `apply_theme(app)` renders the template with the selected palette + accent tint (`app/ui/theme.py:17-120`)
- Purpose: i18n with Qt-style `%1` placeholders; every dialog defines a `tr` method and core modules use `translator.tr(...)`
- Examples: `app/core/translator.py` (`QtString`, `tr()`), `app/core/updater.py:102`
- Pattern: `QtString(str)` subclass with `.arg(*values)`; source language is Spanish (no `.qm` for `es`); `cosechamedia_en.qm` is compiled from the `.ts` (`tools/update_translations.ps1`)

## Entry Points

- Location: `main.py`
- Triggers: `python main.py` or the PyInstaller binary
- Responsibilities: Create `QApplication`, set font/org/app names, load translation, apply theme + icon, instantiate and show `MainWindow`, run the event loop (`main.py:11-28`)
- Location: `app/ui/main_window.py:1366`
- Triggers: "INICIAR INGESTA" button (`btn_start`)
- Responsibilities: Validate sources, reset UI state, build per-source `Ingestor`s, start `FileSystemWatcher`s, mark sessions active
- Location: `app/core/shoot_inbox.py:441`
- Triggers: `MainWindow._ensure_wifi_server` when the user opens the WiFi panel
- Responsibilities: Bind `ThreadingHTTPServer` on `0.0.0.0:0`, serve upload page + `/upload` + `/health`
- Location: `app/ui/main_window.py:223`
- Triggers: 5-second `QTimer`; throttled per device to 60 s
- Responsibilities: Detect reachable MTP/FTP devices with sessions and re-stage their folders incrementally
- Location: `app/core/updater.py:98`
- Triggers: Startup (3 s `QTimer`, frozen builds only) and the About dialog button
- Responsibilities: Query GitHub `releases/latest`, compare versions, select platform asset, verify SHA-256, install on restart via helper scripts

## Architectural Constraints

- **Threading:** UI runs on the Qt main thread. Background work: `ThreadPoolExecutor` (default `max_workers=4`, `1` in delicate mode) inside `Ingestor` (`app/core/ingestor.py:145`); polling daemon threads for `FileSystemWatcher` (`app/core/watcher.py:19`) and `ShootInboxServer` (`app/core/shoot_inbox.py:453`); `QThread` + `_TaskWorker`/`_StageWorker` for staging and post-ingest jobs (`app/ui/main_window.py:91-147`); COM must be initialized on the thread that uses it — `_WpdSession` pairs `CoInitialize`/`CoUninitialize` (`app/core/mtp.py:192-222`)
- **Global state:** module-level singletons `db`, `metadata_engine`, `ffmpeg`, `sd_reader`; `_translator` in `app/core/translator.py:17`; `_DEVICE_MANAGER` and `_types_loaded` in `app/core/mtp.py:153-154,439`. Tests rely on replacing module attributes
- **Circular imports:** none detected — `app/core/` imports only from `app.core` and Qt; `app/ui/` imports from `app.core` and `app.ui`. `shoot_inbox` imports `ftp.local_ip`; `ingestor` imports `metadata_engine` which imports `db`
- **Frozen vs dev paths:** every path helper must honor `sys.frozen` (`resource_path`, `_resolve_db_path`, `application_dir`); the DB lives next to the executable when frozen, in CWD in dev (`app/core/db.py:8-15`)
- **Spanish is the source language:** UI strings are Spanish literals; the English catalog is `app/i18n/cosechamedia_en.ts` → `.qm` (`app/core/translator.py:56-66`)

## Anti-Patterns

### God object `MainWindow`

### Core layer importing the UI layer

### Swallowed exceptions with `print`

### Module monkey-patching instead of dependency injection

## Error Handling

- Per-file isolation: `_run_single_file` wraps the whole pipeline so one bad file doesn't stop the ingest (`app/core/ingestor.py:315-386`)
- Partial-copy cleanup: `copy_verified` removes the destination on hash mismatch or exception (`app/core/ingestor.py:61-74`)
- Fallback chains: metadata date → mtime (`_finalize_dates`, `app/core/metadata_engine.py:119-137`); MLSD → NLST+SIZE+MDTM (`app/core/ftp.py:293-297`); passive → active mode flip (`app/core/ftp.py:360-387`)
- Retry with reconnect: WPD staging reopens the device once on `0x80070081` (`app/core/mtp.py:497-510`); FTP reopens and flips passive mode (`app/core/ftp.py:430-466`)
- Cancellation: `_stop_event` + `cancel_cb` polling throughout scans and staging (`app/core/ingestor.py:204-206`, `app/core/metadata_engine.py:298-336`)
- Custom exceptions: `MtpError` (`app/core/mtp.py:29`), `UpdateError` (`app/core/updater.py:32`); the UI maps these to `QMessageBox`

## Cross-Cutting Concerns

<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
