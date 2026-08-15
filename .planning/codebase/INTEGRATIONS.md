# External Integrations

**Analysis Date:** 2026-08-15

## APIs & External Services

**Updates (GitHub Releases):**
- GitHub REST API - Auto-update checks against `https://api.github.com/repos/MustangXPress7/CosechaMedia/releases/latest`, downloads the platform asset, verifies its SHA-256 against a `.sha256` sidecar published in the same release, then swaps the binary on restart
  - SDK/Client: none — stdlib `urllib.request` in `app/core/updater.py`
  - Auth: none (public repo); sends `User-Agent: CosechaMedia-Updater/<version>` and `Accept: application/vnd.github+json` headers
  - Asset naming contract: `CosechaMedia-windows-x86_64.exe`, `CosechaMedia-macos.app.zip`, `CosechaMedia-linux-x86_64` (matched by keyword in `select_platform_asset`)
  - Per-platform replace helpers: `_WINDOWS_HELPER` (cmd), `_MAC_HELPER`/`_LINUX_HELPER` (bash) in `app/core/updater.py`
  - Triggered from `app/ui/main_window.py:3712` (`_check_for_updates`) and on startup

**Media processing (FFmpeg):**
- ffprobe - Extracts format/stream metadata (camera make/model, serial, creation date, duration, codecs, fps) via JSON output (`app/core/metadata_engine.py:150`)
- ffmpeg - Generates 720p/1080p H.264 proxies with `-preset ultrafast -crf 28` (`app/core/ffmpeg_utils.py`)
  - SDK/Client: none — `subprocess` calls to `ffmpeg`/`ffprobe` binaries
  - Auth: n/a — local CLI tools required in `PATH`

**Phone/camera ingestion (MTP over Windows WPD):**
- Windows Portable Devices (WPD) COM API - USB MTP access to phones and cameras via `comtypes` against typelibs `portabledeviceapi.dll` / `portabledevicetypes.dll` (`app/core/mtp.py`)
  - SDK/Client: `comtypes>=1.4.0` (`comtypes.client.GetModule`, `comtypes.gen.PortableDeviceApiLib` / `PortableDeviceTypesLib`)
  - Auth: none — Windows system API; client registered as `"CosechaMedia"` (`WPD_CLIENT_NAME`)
  - Known constraints documented in module docstring: COM must be initialized per-thread, hung connections return `0x80070081` and require cable reconnect

**Phone ingestion over network (FTP):**
- FTP servers on mobile devices (Primitive FTPd on Android, GoFTP Server on iOS) - Lists and downloads `DCIM` folders; uses `MLSD` (RFC 3659) with `NLST`+`SIZE`+`MDTM` fallback (`app/core/ftp.py`)
  - SDK/Client: stdlib `ftplib`
  - Auth: username/password from saved FTP profiles (plain text over local network; documented in README)
  - Includes a LAN discovery scanner: probes the local /24 subnet on ports 21 and 2221 with 64 parallel workers (`scan_network_ftp`, `local_subnet_ips` in `app/core/ftp.py`)

**WiFi reception (PairDrop-style, embedded server):**
- Embedded HTTP server (stdlib `http.server.ThreadingHTTPServer`) - Phones upload files via browser after scanning a QR code; nothing installed on the phone. Serves `/` (upload page), `POST /upload` (file receive), `GET /health` (`app/core/shoot_inbox.py`)
  - SDK/Client: `qrcode>=7.4` renders the per-sender QR (`app/ui/wifi_panel.py`); server URL is `http://<local-ip>:<port>`
  - Auth: per-sender bearer token (`secrets.token_urlsafe(12)`) stored in `inbox_senders` table and embedded as `?src=<name>&token=<token>` in the QR URL; `_handle_upload` rejects mismatches with HTTP 403 (`app/core/shoot_inbox.py:354`)
  - Files land in `data/inbox/<sanitized-alias>/` as `.part` then renamed atomically

## Data Storage

**Databases:**
- SQLite (embedded, stdlib `sqlite3`) — `data/sd_import.db` in the app directory (frozen) or CWD (dev)
  - Connection: no env var — resolved by `app/core/db.py:_resolve_db_path()`
  - Client: raw `sqlite3` with `PRAGMA journal_mode=WAL`, `check_same_thread=False`, `row_factory=sqlite3.Row`; no ORM
  - Tables: `projects`, `dump_locations`, `cameras`, `sessions`, `files`, `sd_cards`, `recent_paths`, `ftp_profiles`, `inbox_senders`, `containers`, `footage_folders`
  - Migration strategy: additive `ALTER TABLE ... ADD COLUMN` with `PRAGMA table_info` checks plus backfill (e.g., `dump_locations` → `projects.dump_path`) inside `create_tables()`

**File Storage:**
- Local filesystem only. Ingest dumps to user-chosen project roots (`Footage/<Camera>/<Date>` organization); caches under `data/` (`inbox`, `device_cache`); `_reference/` for non-media files (`app/core/ingestor.py:271`)

**Caching:**
- In-memory metadata cache (LRU, max 2000 entries, keyed by file mtime) in `app/core/metadata_engine.py`
- On-disk incremental staging manifests (`.sync_manifest.json` per device/folder) in `app/core/mtp.py` / `app/core/ftp.py`
- Ingestion resume state: `.sdimport_session_<id>.json` listing verified copied files (`app/core/ingestor.py`)

## Authentication & Identity

**Auth Provider:**
- Custom (local), no external identity provider
  - Implementation: per-sender bearer tokens for the WiFi inbox (`secrets.token_urlsafe(12)` in `app/core/db.py:691`, checked in `app/core/shoot_inbox.py:360`)
  - FTP profiles authenticate with username/password stored in the local SQLite `ftp_profiles` table (plain text)
  - SD-card identity derived from ffprobe metadata (serial/make/model) via `app/core/sd_reader.py`

## Monitoring & Observability

**Error Tracking:**
- None. No Sentry/rollbar/telemetry; errors surface via `print()` to stdout and Qt dialog boxes (`app/core/notifications.py`)

**Logs:**
- `print()` statements scattered in core modules (`app/core/ingestor.py`, `app/core/metadata_engine.py`, `app/core/watcher.py`)
- Updater helper scripts write `update_log.txt` next to the binary on Windows (`app/core/updater.py:_WINDOWS_HELPER`)
- No structured logging module

## CI/CD & Deployment

**Hosting:**
- GitHub Releases (binaries distributed from `https://github.com/MustangXPress7/CosechaMedia/releases`); source hosted at `https://github.com/MustangXPress7/CosechaMedia.git`

**CI Pipeline:**
- GitHub Actions - `.github/workflows/build.yml`: triggered on `v*` tags; validates the tag matches `app/__init__.py.__version__`; builds Windows (`windows-latest`), macOS (`macos-latest`), Linux (`ubuntu-latest`) with Python 3.11 + PyInstaller; generates `.sha256` sidecars; publishes assets via `softprops/action-gh-release@v2`
- Local builds: `Compilar.bat` (Windows), `setup_mac.command` (macOS)

## Environment Configuration

**Required env vars:**
- None — the application reads no environment variables (verified: no `os.environ` usage in `app/`)

**Secrets location:**
- No `.env` file, no secret files
- WiFi inbox tokens and FTP passwords live in the local SQLite DB (`data/sd_import.db`, tables `inbox_senders` / `ftp_profiles`) — plain text, single-user desktop context

## Webhooks & Callbacks

**Incoming:**
- Local embedded HTTP endpoints only (not public webhooks): `GET /` upload page, `POST /upload` file receive, `GET /health` — `app/core/shoot_inbox.py`

**Outgoing:**
- None. The only outbound HTTP is the GitHub Releases API check/download in `app/core/updater.py`

---

*Integration audit: 2026-08-15*
