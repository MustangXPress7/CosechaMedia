<!-- refreshed: 2026-08-15 -->
# Architecture

**Analysis Date:** 2026-08-15

## System Overview

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                         UI LAYER  (PySide6/Qt widgets)                   │
├──────────────────────┬───────────────────────┬──────────────────────────┤
│  MainWindow          │  Pickers / Dialogs     │  Theming & Decor         │
│  `app/ui/main_window.py` │  `app/ui/device_picker.py`  │  `app/ui/theme.py`   │
│  (orchestrator)      │  `app/ui/ftp_picker.py`       │  `app/ui/wheat_field.py`│
│                      │  `app/ui/source_picker.py`    │  `app/ui/wifi_panel.py`│
│                      │  `app/ui/selective_dump.py`   │  `app/ui/wifi_picker.py`│
│                      │  `app/ui/project_wizard.py`   │  `app/ui/about_dialog.py`│
└──────────┬───────────┴──────────────┬────────┴──────────────┬────────────┘
           │ Qt Signals / direct calls │                        │
           ▼                           ▼                        │
┌─────────────────────────────────────────────────────────────────────────┐
│                   CORE LAYER  (business logic, no widgets)               │
├──────────────────────┬───────────────────────┬──────────────────────────┤
│  Ingest pipeline      │  Device backends      │  Infrastructure          │
│  `app/core/ingestor.py`   │  `app/core/mtp.py`      │  `app/core/db.py`     │
│  `app/core/watcher.py`    │  `app/core/ftp.py`      │  `app/core/utils.py`  │
│  `app/core/metadata_engine.py` │  `app/core/shoot_inbox.py`│  `app/core/translator.py`│
│  `app/core/ffmpeg_utils.py`    │  `app/core/sd_reader.py` │  `app/core/updater.py`│
│                            │                        │  `app/core/notifications.py`│
└──────────┬───────────┴──────────────┬─────────┴──────────┬─────────────┘
           │                          │                    │
           ▼                          ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STORAGE / EXTERNAL:  SQLite `data/sd_import.db` · local caches          │
│  `data/inbox/<alias>` · `data/device_cache/<sha1>/<folder>` · Footage/   │
│  FFmpeg/ffprobe CLI · GitHub Releases API · MTP (COM) · FTP · HTTP       │
└─────────────────────────────────────────────────────────────────────────┘
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

**Overall:** Two-layer desktop app — Qt UI layer (`app/ui/`) over a business-logic layer (`app/core/`) — connected by Qt signals for threading and by module-level singleton service objects (`db`, `metadata_engine`, `ffmpeg`, `sd_reader`). The `MainWindow` is a single orchestrator that wires UI events to core services.

**Key Characteristics:**
- **Signal-driven progress:** Core emits Qt `Signal`s (e.g. `Ingestor.file_finished`, `copy_progress`, `ingest_complete`) that the UI connects to for safe cross-thread updates (`app/core/ingestor.py:115-121`, connected in `app/ui/main_window.py:1482-1494`)
- **Reactive ingestion:** `FileSystemWatcher` polls source dirs and pushes each new file into `Ingestor.handle_new_file`; the Ingestor dedupes, classifies, and dispatches to a `ThreadPoolExecutor` (`app/core/ingestor.py:235-262`)
- **Backend-interface reuse:** `MtpBackend` (interface) is implemented by `WpdBackend` (COM) and `FtpBackend` (network); both share the incremental staging engine `_stage_session` (`app/core/mtp.py:55-104`, `app/core/ftp.py:338`)
- **SQLite as system of record:** projects, sessions, files, cameras, containers, FTP profiles, inbox senders — all in one DB via `DatabaseManager` (`app/core/db.py:20`)
- **Frozen-aware paths:** `resource_path()` and `_resolve_db_path()` switch between `sys._MEIPASS`/`sys.executable` (PyInstaller) and repo-relative paths in dev (`app/core/utils.py:6-12`, `app/core/db.py:8-15`)

## Layers

**UI Layer:**
- Purpose: Present the interface, capture user intent, render progress
- Location: `app/ui/`
- Contains: `MainWindow`, picker dialogs, wizard, wifi panel, theme, wheat-field background painter, logos
- Depends on: `app/core` (all modules), Qt
- Used by: `main.py` only (`app/ui/main_window.py` imports every other UI module)

**Core Layer:**
- Purpose: Business logic — ingest, metadata, device access, storage, updates, i18n
- Location: `app/core/`
- Contains: 12 modules; the only Qt dependency is `QObject`/`Signal` (in `app/core/ingestor.py` and `app/core/translator.py`) plus `QMessageBox` (in `app/core/notifications.py`)
- Depends on: stdlib (`sqlite3`, `subprocess`, `ftplib`, `http.server`, `threading`, `concurrent.futures`), `PySide6.QtCore`, `comtypes` (Windows), external CLIs (ffmpeg/ffprobe), GitHub API
- Used by: `app/ui/`, `tests/`

**Data/Storage Layer:**
- Purpose: Persistent state and media output
- Location: `data/` (runtime, gitignored)
- Contains: `data/sd_import.db` (SQLite, WAL), `data/inbox/<alias>` (WiFi receive cache), `data/device_cache/<sha1(device_id)>/<folder>` (MTP/FTP staging + `.sync_manifest.json`), `data/projects/<name>` (default project roots), plus the configured `Footage/` dump roots

## Data Flow

### Primary Request Path — SD card ingest

1. `MainWindow.start_ingest()` collects active sessions from `db.get_sessions()`, builds one `Ingestor` per active source, and connects its signals to UI handlers (`app/ui/main_window.py:1366-1495`)
2. A `FileSystemWatcher` per source starts on a daemon thread, walks the dir, and calls `ingestor.handle_new_file(path)` for every new non-system file (`app/core/watcher.py:25-57`)
3. `Ingestor.handle_new_file` dedupes (`processed_files`, `_copied_files`), applies the content filter, classifies via `metadata_engine.get_file_type_info`, and submits `_process_single_file` to a `ThreadPoolExecutor` (`app/core/ingestor.py:235-262`)
4. `_run_single_file` resolves camera (known map → ffprobe metadata → default → `camera_rename_needed` signal), determines the shoot date (metadata → manual → today), picks a dump target (`_pick_dump_target` rotates across `DumpTarget`s when a disk fills), and performs the MD5-verified copy (`app/core/ingestor.py:315-400`)
5. On success the `files` row is inserted via `db` and `file_finished` is emitted; the UI updates the table row and progress (`app/core/ingestor.py:361-381`, `app/ui/main_window.py:1596-1639`)
6. When all watchers complete and no file is in flight, `ingest_complete` fires; `_finalize_ingest` runs queued post-actions (format sources, generate proxies, shutdown) (`app/core/ingestor.py:208-229`, `app/ui/main_window.py:1647-1737`)

### Device staging flow (MTP/USB and FTP/WiFi)

1. `MainWindow._pick_device_source` opens `DevicePickerDialog`; `_pick_ftp_source` opens `FtpPickerDialog` (network scan via `scan_network_ftp`) (`app/ui/main_window.py:2901-2930`, `app/ui/main_window.py:3274-3296`)
2. The chosen folder is staged in the background: `_StageWorker` (QThread) calls `backend.stage()` which walks the device tree and downloads incrementally into `data/device_cache/<sha1>/<folder>`, tracked by `.sync_manifest.json` (size+mtime) (`app/ui/main_window.py:91-121`, `app/core/mtp.py:597-638`)
3. `_register_device_source` creates a `sessions` row with `device_id` (`MTP PnP id` or `ftp:<profile_id>`) and `source_path` = cache dir; later ingestion treats the cache like a card (`app/ui/main_window.py:3297-3330`)
4. `MainWindow._auto_sync_check` runs every 5 s (throttled to 60 s per device) and re-stages any reachable device with sessions (`app/ui/main_window.py:223-259`)

### WiFi inbox flow (PairDrop-style)

1. `_ensure_wifi_server` starts `ShootInboxServer` (`ThreadingHTTPServer` in a daemon thread) (`app/ui/main_window.py:2989-3002`, `app/core/shoot_inbox.py:421-472`)
2. Each sender is a row in `inbox_senders` with a `secrets.token_urlsafe(12)` token; `url_for_sender` builds `/?src=<alias>&token=<token>`; `ShootInboxPanel` renders the QR (`app/core/shoot_inbox.py:486-493`, `app/ui/wifi_panel.py`)
3. The phone POSTs to `/upload`; `_UploadHandler` writes to `.part` then renames atomically into `data/inbox/<alias>`, then invokes the callback (`app/core/shoot_inbox.py:347-412`)
4. `MainWindow._on_wifi_file_received` starts/refeeds a per-session `Ingestor` watching that inbox dir; after completion the cache is cleaned (`app/ui/main_window.py:3221-3263`)

**State Management:**
- **Persistent state:** SQLite via `DatabaseManager` (`app/core/db.py`) — projects, sessions, files, containers, footage folders, FTP profiles, inbox senders
- **Resume state:** `Ingestor` persists copied-file sets to `.sdimport_session_<id>.json` beside the destination root; a legacy `.sdimport_session.json` is also read (`app/core/ingestor.py:155-202`)
- **In-memory UI state:** `MainWindow` attributes for project/session config, `_ingestors`, `watchers`, `_file_row_map` (`app/ui/main_window.py:163-191`)
- **Settings:** Qt `QSettings` (org "Audiovisual Production", app "CosechaMedia") — language, theme, accent, camera detection mode, window geometry (`app/ui/theme.py:8-13`, `app/core/translator.py:38`)
- **Thread-state:** `_inflight`, `_remaining_watchers`, `_complete_emitted` guarded by `_inflight_lock` to decide when an ingest is truly complete (`app/core/ingestor.py:178-233`)

## Key Abstractions

**`MtpBackend` (device access interface):**
- Purpose: Uniform access to phones/cameras, whether over USB (WPD/COM) or FTP
- Examples: `app/core/mtp.py` (interface + `WpdBackend`), `app/core/ftp.py` (`FtpBackend`)
- Pattern: Backend classes expose `list_devices()` and `_open_session()`; sessions must provide `storages()`, `_resolve()`, `_enum_children()`, `download()`. The shared staging engine `_stage_session` consumes only that session surface (`app/core/mtp.py:597-638`). FTP identity is `ftp:<profile_id>`; MTP identity is the WPD PnP id (`app/core/ftp.py:68-79`)

**`Ingestor` (verified copy pipeline):**
- Purpose: Copy any source (card, inbox cache, device cache) into the project with MD5 verification, camera/date organization, disk rotation, and progress signals
- Examples: `app/core/ingestor.py`, reused by `MainWindow.start_ingest`, `_start_wifi_ingestor`, `_ensure_wifi_ingestion`
- Pattern: `QObject` + `ThreadPoolExecutor`; external events (`handle_new_file`) are serialized through `processed_files` and a stop event; completion is tracked with an inflight/watcher counter

**Module-level singletons:**
- Purpose: One shared service instance across UI and core
- Examples: `db = DatabaseManager()` (`app/core/db.py:863`), `metadata_engine = MetadataEngine()` (`app/core/metadata_engine.py:429`), `ffmpeg = FFmpegProcessor()` (`app/core/ffmpeg_utils.py:59`), `sd_reader = SDReader()` (`app/core/sd_reader.py:179`)
- Pattern: module-scope instance; tests monkey-patch the module attribute to inject fakes (e.g. `ingestor_module.db = self.db` in `tests/test_ingestor.py:40`)

**Theme palette + QSS template:**
- Purpose: Single source of color truth; a QSS template with `@key` placeholders is filled per theme/accent
- Examples: `app/ui/theme.py` (`DARK`/`LIGHT` palettes, `ACCENTS`, `_QSS_TEMPLATE`), `theme.color(...)` used throughout UI files
- Pattern: palettes are dicts; `apply_theme(app)` renders the template with the selected palette + accent tint (`app/ui/theme.py:17-120`)

**`tr()` / `QtString`:**
- Purpose: i18n with Qt-style `%1` placeholders; every dialog defines a `tr` method and core modules use `translator.tr(...)`
- Examples: `app/core/translator.py` (`QtString`, `tr()`), `app/core/updater.py:102`
- Pattern: `QtString(str)` subclass with `.arg(*values)`; source language is Spanish (no `.qm` for `es`); `cosechamedia_en.qm` is compiled from the `.ts` (`tools/update_translations.ps1`)

## Entry Points

**Application entry (`main.py`):**
- Location: `main.py`
- Triggers: `python main.py` or the PyInstaller binary
- Responsibilities: Create `QApplication`, set font/org/app names, load translation, apply theme + icon, instantiate and show `MainWindow`, run the event loop (`main.py:11-28`)

**Ingest start (`MainWindow.start_ingest`):**
- Location: `app/ui/main_window.py:1366`
- Triggers: "INICIAR INGESTA" button (`btn_start`)
- Responsibilities: Validate sources, reset UI state, build per-source `Ingestor`s, start `FileSystemWatcher`s, mark sessions active

**WiFi server (`ShootInboxServer.start`):**
- Location: `app/core/shoot_inbox.py:441`
- Triggers: `MainWindow._ensure_wifi_server` when the user opens the WiFi panel
- Responsibilities: Bind `ThreadingHTTPServer` on `0.0.0.0:0`, serve upload page + `/upload` + `/health`

**Auto device sync (`MainWindow._auto_sync_check`):**
- Location: `app/ui/main_window.py:223`
- Triggers: 5-second `QTimer`; throttled per device to 60 s
- Responsibilities: Detect reachable MTP/FTP devices with sessions and re-stage their folders incrementally

**Update check (`updater.check_for_updates`):**
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

**What happens:** `app/ui/main_window.py` is 3,870 lines: UI construction (`setup_views`), project CRUD, session management, ingest orchestration, WiFi/QR, MTP/FTP staging, auto-sync, formatting, shutdown scheduling, proxy generation, camera detection, update checks — all methods on one class.
**Why it's wrong:** Any change touches a huge, low-cohesion class; the orchestrator cannot be reused or tested in isolation; signal wiring is dense (one method per handler).
**Do this instead:** Split into focused controllers (e.g. an `IngestController`, `DeviceSyncController`, `WifiController`) that own the flow and emit signals, with `MainWindow` only composing views. `app/ui/selective_dump.py` (assistant dialog with its own worker) is the existing pattern worth following.

### Core layer importing the UI layer

**What happens:** `app/core/notifications.py:8` does `from app.ui import theme` and uses `QMessageBox`/`QDialog` (`app/core/notifications.py:5-9`), so business logic depends on presentation.
**Why it's wrong:** Breaks the core→UI dependency direction; the core package can't run headless without Qt widgets and the theme, which complicates testing and reuse.
**Do this instead:** Keep `notifications.py` UI-free (play sounds only) and let the UI layer build the dialogs from `ingest_complete` stats — matching how `MainWindow._on_ingestor_complete` already receives stats.

### Swallowed exceptions with `print`

**What happens:** Pervasive `except Exception:` / `except:` with `print(...)` or silent pass: `ingestor.py:_save_copied_files` (`except:` pass), `reorganize_by_metadata` (`except: pass`), `mtp.py:_enum_children` (`except Exception: pass`), `sd_reader.py` (`except: pass`).
**Why it's wrong:** Failures (corrupt DB, missing files, COM errors) disappear; the `files` table may silently lack rows while the UI shows success.
**Do this instead:** Log with the `logging` module at minimum (`logger.warning(...)`) and surface recoverable errors through the existing signal channels (e.g. `dump_progress`, `file_finished(ok=False)`).

### Module monkey-patching instead of dependency injection

**What happens:** Tests replace module globals (`ingestor_module.db = self.db`, `ingestor_module.metadata_engine = FakeMeta()`) and restore them in `tearDown` (`tests/test_ingestor.py:36-51`; same in `tests/test_e2e.py:42-49`).
**Why it's wrong:** Test setup is coupled to import order; parallel or async tests can race; a production code path that imports the singleton after patching sees the original.
**Do this instead:** Accept explicit collaborators in constructors (e.g. `Ingestor(..., db=None, metadata_engine=None)` defaulting to the singletons), which the tests can inject directly.

## Error Handling

**Strategy:** Defensive per-file/per-operation try/except; failures are counted in `Ingestor._stats["errors"]` and reported via signals; the verified-copy path deletes partial destinations (`app/core/ingestor.py:31-74`).

**Patterns:**
- Per-file isolation: `_run_single_file` wraps the whole pipeline so one bad file doesn't stop the ingest (`app/core/ingestor.py:315-386`)
- Partial-copy cleanup: `copy_verified` removes the destination on hash mismatch or exception (`app/core/ingestor.py:61-74`)
- Fallback chains: metadata date → mtime (`_finalize_dates`, `app/core/metadata_engine.py:119-137`); MLSD → NLST+SIZE+MDTM (`app/core/ftp.py:293-297`); passive → active mode flip (`app/core/ftp.py:360-387`)
- Retry with reconnect: WPD staging reopens the device once on `0x80070081` (`app/core/mtp.py:497-510`); FTP reopens and flips passive mode (`app/core/ftp.py:430-466`)
- Cancellation: `_stop_event` + `cancel_cb` polling throughout scans and staging (`app/core/ingestor.py:204-206`, `app/core/metadata_engine.py:298-336`)
- Custom exceptions: `MtpError` (`app/core/mtp.py:29`), `UpdateError` (`app/core/updater.py:32`); the UI maps these to `QMessageBox`

## Cross-Cutting Concerns

**Logging:** `print()` only — no `logging` module anywhere in `app/` (`app/core/ingestor.py:69`, `app/core/metadata_engine.py:257`, `app/core/watcher.py:27`). Server request logs are silenced via `log_message` override (`app/core/shoot_inbox.py:303-304`).
**Validation:** Path sanitization helpers (`_sanitize_camera_name` in `app/core/ingestor.py:439`, `sanitize_alias`/`sanitize_relative_path` in `app/core/shoot_inbox.py:252-274`, `_sanitize_component` in `app/core/mtp.py:111`); token auth for WiFi uploads (`app/core/shoot_inbox.py:356-362`); version compare in `app/core/updater.py:58-61`.
**Authentication:** WiFi uploads use per-sender bearer tokens from `inbox_senders` (`app/core/db.py:686-696`); FTP uses profile username/password stored in the DB (`app/core/db.py:202-214`); no other auth surface.
**Internationalization:** Every user-facing string goes through `tr()`; the UI dialog classes define a `tr` instance method returning `QtString`; catalogs in `app/i18n/`; translation pipeline in `tools/update_translations.ps1` + `tools/translate_en.py`.
**Persistence of runtime data:** all under `data/` next to the DB — inbox caches, device staging caches with `.sync_manifest.json` manifests (`app/core/mtp.py:573-594`), and session resume JSON.

---

*Architecture analysis: 2026-08-15*
