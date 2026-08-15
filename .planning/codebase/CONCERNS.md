<!-- refreshed: 2026-08-15 -->
# Codebase Concerns

**Analysis Date:** 2026-08-15

## Tech Debt

**`main_window.py` god object (3870 lines):**
- Issue: `app/ui/main_window.py` mixes UI construction, business orchestration (MTP/FTP/WiFi), worker threading (`_TaskWorker`, `_StageWorker`, `_format_sources_worker`, `_reorganize_worker`), and DB calls in a single class. New features keep adding methods (rename flows, WiFi reception, staging) instead of extracting services.
- Files: `app/ui/main_window.py`
- Impact: Any change risks UI-thread freezes, cross-wiring of signals, and merge conflicts. Testability near zero (see Test Coverage Gaps).
- Fix approach: Extract `app/core/ingestion_manager.py` (orchestration + workers) and `app/ui/source_controller.py` (source panel state); keep `main_window.py` for widget assembly + slot delegation.

**Inline ALTER TABLE migrations inside `create_tables`:**
- Issue: Schema evolution is done via `cursor.execute("PRAGMA table_info(...)")` + inline `ALTER TABLE ADD COLUMN` loops inside `create_tables()` (`app/core/db.py:134-157, 174-177, 225-229`). No versioned migration table, no `PRAGMA user_version`, no rollback path.
- Files: `app/core/db.py`
- Impact: A broken `ALTER` on an existing user DB fails the whole startup silently (exception swallowed at `main.py`), leaving the app in a half-initialized state. Reordering column additions between versions is risky.
- Fix approach: Introduce `schema_version` table + ordered migration list applied in transactions; log failures loudly.

**No logging framework — bare `print()`/`traceback.print_exc()`:**
- Issue: Error reporting is scattered `print()` calls (~16 sites) plus `traceback.print_exc()` in `app/ui/selective_dump.py:122`. No `logging` module anywhere. End users get no log file to send for support.
- Files: `app/core/ingestor.py:69,299,384`, `app/core/ffmpeg_utils.py:52,55`, `app/core/metadata_engine.py:257`, `app/core/notifications.py:35,162`, `app/core/utils.py:50`, `app/core/watcher.py:27,61`, `app/ui/main_window.py:146,1714,3515,3765`, `app/ui/selective_dump.py:785`
- Impact: Silent failures in production (exceptions swallowed) with no diagnostics trail.
- Fix approach: Add a `logging` setup in `app/core/logging_setup.py` writing to `data/logs/cosechamedia.log` (rotating), and replace prints progressively.

**Duplicated device name in MTP session:**
- Issue: `app/core/mtp.py:211` builds `devicename = f"{self.name}_{self.name}_{self.serial}"` — the friendly name is duplicated, which produces odd folder names like `CANON_CANON_12345`.
- Files: `app/core/mtp.py`
- Impact: Cosmetic garbage in destination paths; may confuse operators comparing names.
- Fix approach: Use `f"{self.name}_{self.serial}"` and keep a one-time DB migration if folders already created (or accept cosmetic-only change).

**Files table FK type mismatch:**
- Issue: `files.session_id TEXT` references `sessions.id INTEGER PRIMARY KEY AUTOINCREMENT` (`app/core/db.py:163`). SQLite allows it but joins rely on string coercion.
- Files: `app/core/db.py`
- Impact: Fragile joins; future schema changes (e.g., UUIDs) will silently break.
- Fix approach: Align column types when next migration touches `files`.

**`QtString.arg` only replaces first occurrence of each `%N`:**
- Issue: `app/core/translator.py` `QtString.arg` implementation replaces only the first occurrence of each `%N` placeholder. Translations using the same placeholder twice render incorrectly.
- Files: `app/core/translator.py`, `app/i18n/cosechamedia_es.ts`, `app/i18n/cosechamedia_en.ts`
- Impact: Wrong user-facing strings in Spanish/English for some messages.
- Fix approach: Implement `replace("%1", v)` for all occurrences, or assert on leftover placeholders at load time.

## Known Bugs

**`rename_camera` uses forward-slash LIKE pattern that never matches Windows paths:**
- Symptoms: Renaming a camera does not update `files.source_path`/`dest_path` rows on Windows.
- Files: `app/core/ingestor.py` (`rename_camera`), invoked from `app/ui/main_window.py` `_on_camera_rename_needed` (1877-1885)
- Trigger: User renames a camera after files ingested; DB UPDATE uses `LIKE '%/{old}/%'` with `/` separators while stored paths use `\`.
- Workaround: None; paths stay stale. Manual DB edit required.
- Fix approach: Use `os.sep`/both separators or `instr()` checks per row with Python-side path normalization.

**`_free_space` returns 0 on error → dump targets treated as full:**
- Symptoms: "Disco lleno" messages and file dump failure even though the drive has space.
- Files: `app/core/ingestor.py` (`_free_space`, used by `_pick_dump_target` / `_copy_verified_with_progress`)
- Trigger: Any exception in `shutil.disk_usage` (permission, exotic volume) → 0 → target skipped; if all targets are 0, ingest aborts.
- Workaround: Re-select dump paths / restart.
- Fix approach: Distinguish "unknown" (−1) from "full" (0) and treat unknown as last-resort target.

**Camera detection race in `_detect_camera_for_session`:**
- Symptoms: Wrong camera assigned to a session, or camera prompt shown twice; `_cam_done` flag is shared across sessions and never reset between runs.
- Files: `app/ui/main_window.py:2130-2163` (`_detect_camera_for_session`, `_prompt_unknown_camera`), called from ~6 paths (2189, 2337, 2790, 2814, 3378, 3797)
- Trigger: Multiple sessions start ingesting concurrently, or user starts a new session while a previous detection timer is pending. The single-shot `_cam_timer` is recreated per call, so earlier timers can fire after later ones and overwrite state.
- Workaround: Restart app; detection result is written to DB so a manual rename fixes the session.
- Fix approach: Guard with a per-session token/id; cancel pending timers before starting a new detection; reset `_cam_done` when a detection completes or times out.

**DB path depends on working directory when not frozen:**
- Symptoms: Two launches from different directories use different `data/sd_import.db` files → "lost" sessions/projects.
- Files: `app/core/db.py:8-30` (`_resolve_db_path`)
- Trigger: Running `python main.py` from a different CWD than the packaged app uses.
- Workaround: Always launch from the same directory.
- Fix approach: Anchor to `Path(__file__).resolve().parents[2]` (project root) for dev, exe dir only when frozen.

**Watcher re-ingests files after `scanned_files` pruning:**
- Symptoms: Files already copied get copied again (duplicates with new MD5 rows) after a long idle session.
- Files: `app/core/watcher.py` (`_watch`, prunes `scanned_files` at 10000 entries; comment "Keep set size")
- Trigger: SD folder with >10k entries, or watcher left running for a long time while the source directory churns.
- Workaround: None; the `files` table check may skip some via MD5 but paths differ.
- Fix approach: Prune by age (drop oldest known paths) instead of hard cap, or persist scanned inventory to DB.

**FFprobe timeout yields silent "Unknown" metadata + `file_size=0`:**
- Symptoms: Files categorized as "Unknown" camera and `size 0` rows in `files`, breaking post-ingest organization and reports.
- Files: `app/core/metadata_engine.py:110-155` (`_finalize_dates`, `get_video_metadata`, 10 s subprocess timeout + `-read_intervals %+0.5`)
- Trigger: Large/high-bitrate MXF or corrupted video where ffprobe exceeds 10 s.
- Workaround: None visible; re-run detection doesn't revisit completed files.
- Fix approach: Retry with longer timeout or duration-only probe; fall back to mtime+extension with a visible warning flag instead of silent 0.

**Ingestor ThreadPoolExecutor never shut down:**
- Symptoms: `ThreadPoolExecutor` created in `Ingestor.__init__` (`app/core/ingestor.py:110-150`) is never `shutdown()`; `.stop()` only sets `_stop_event` and saves state. Threads linger until process exit.
- Files: `app/core/ingestor.py`
- Trigger: Every ingest; heavy on repeated start/stop cycles.
- Workaround: None (bounded workers, but still leaked threads across sessions).
- Fix approach: `shutdown(wait=False)` in `stop()`; recreate pool per ingest run.

## Security Considerations

**FTP passwords and inbox tokens stored plaintext:**
- Risk: `ftp_profiles.password` (`app/core/db.py:202-214`) and `inbox_senders.token` (`app/core/db.py:217-224`) are plaintext in `data/sd_import.db`. Any reader of the file (backup, crash dump, debugger) gets credentials.
- Files: `app/core/db.py`, `app/core/ftp.py:340-380`, `app/core/shoot_inbox.py:330-493`
- Current mitigation: SQLite file permissions only.
- Recommendations: Encrypt at rest with a key derived from machine/user (e.g., DPAPI on Windows via `ctypes` or `keyring`); never write token/password to logs.

**ShootInboxServer: unauthenticated upload on 0.0.0.0, token in URL:**
- Risk: The HTTP server binds `0.0.0.0` (`app/core/shoot_inbox.py`), token is passed as a query-string parameter in `url_for_sender`, and upload path checks are a non-constant-time `!=` compare. Anyone on the same network who sees the URL (QR screenshot, browser history, proxy logs) can upload to that sender's cache; no TLS, no rate limit, no max upload size.
- Files: `app/core/shoot_inbox.py` (`do_GET` routes `/` + `/health`, `do_POST /upload`, `_handle_upload` token check, sanitize_alias/sanitize_relative_path)
- Current mitigation: Random token per sender; `sanitize_relative_path` blocks traversal; Content-Length parsed; target dir restricted to `wifi_cache_dir/<sender>`.
- Recommendations: Constant-time compare (`secrets.compare_digest`), per-IP rate limit, optional max size, document that WiFi inbox is for trusted LAN only; consider binding to the LAN IP only.

**Destructive `format` command via `cmd`:**
- Risk: `_format_drive` (`app/ui/main_window.py` `_format_sources_worker`) shells out `cmd /c echo S | format <drive> /FS:exFAT [/Q]`. A path-injection or a wrong drive letter erases a full card/volume with no recovery.
- Files: `app/ui/main_window.py` (format flow 1786-1815, `_on_format_finished` 1817-1822)
- Current mitigation: Only enabled for removable drives + explicit confirmation dialog.
- Recommendations: Validate drive is a fixed set of expected letters, quote path, and add "type FORMAT" confirmation like Windows Explorer; log command without volume label secrets.

**Shell-outs with interpolated paths:**
- Risk: `open_data_folder` uses `os.system('open ...')`/`xdg-open` with an unquoted path from config (`app/ui/main_window.py:3545`), and `notifications.play_sound_file` interpolates a sound path into `os.system('afplay ...')` (`app/core/notifications.py:35`).
- Files: `app/ui/main_window.py:3545`, `app/core/notifications.py:35,162`
- Current mitigation: `os.startfile` on Windows (safe); POSIX branches are the risky ones.
- Recommendations: Use `subprocess.run([...])` with argument lists (no shell), or `QDesktopServices.openUrl` on all platforms.

**Updater downloads and executes platform binaries:**
- Risk: `app/core/updater.py` fetches GitHub release assets + `.sha256`, verifies checksum, then runs a generated helper script (`_WINDOWS_HELPER` bat waits for exit, moves `CosechaMedia.new.exe`, relaunches, deletes itself; mac/linux bash equivalents) and uses `zipfile.extractall` on macOS. If GitHub or DNS is compromised and the checksum check is bypassed, arbitrary code runs.
- Files: `app/core/updater.py:200-262`, `app/ui/about_dialog.py` (`_CheckWorker`/`_DownloadWorker`, `_prompt_install`)
- Current mitigation: `.sha256` sidecar verification before install; user confirmation dialog.
- Recommendations: Pin the release tag/hash allowlist; verify signature if releases are signed; run extraction in a temp dir with `zipfile` safe extraction (no path traversal).

## Performance Bottlenecks

**Double full-file MD5 read per copy:**
- Problem: Each copied file is hashed twice — once after write in `copy_verified` (progress emit) and again in `_run_single_file` via `calculate_md5(dest)` for the `files` row. For a 128 GB SD card this doubles read time of the destination disk.
- Files: `app/core/ingestor.py` (`copy_verified_with_progress`, `_run_single_file`, `app/core/utils.py:calculate_md5`)
- Cause: Verification re-reads the destination instead of reusing the source hash (source read is unavoidable; destination re-read is not, if verified from the source hash + size check).
- Improvement path: Hash source once, store in row, verify destination size + spot-check only; or hash destination in the same pass as copy (stream-through) to avoid a second read.

**UI-thread device polling (`_auto_sync_check`):**
- Problem: A 5 s QTimer on the UI thread calls `mtp.WpdBackend().list_devices()` (per-call COM init) and `FtpBackend.is_reachable()` (network timeout ~3 s). UI freezes when no device is present or network is unreachable.
- Files: `app/ui/main_window.py:223-259`
- Cause: Synchronous COM + socket calls in the Qt event loop; throttled to 1/min/device only after first failure.
- Improvement path: Move checks to a `QThread`/worker emitting signals; increase interval; skip FTP reachability when no ftp profiles exist.

**Per-file ffprobe in batch detection:**
- Problem: `detect_camera_batch` (`app/core/metadata_engine.py:260-303`) probes first 10 files per session with 8 workers, each subprocess up to 10 s, plus `-read_intervals %+0.5` per file during date scan — slow on first ingest of a session.
- Files: `app/core/metadata_engine.py`
- Cause: Metadata needed before organization; cache is per-run mtime-keyed.
- Improvement path: Probe only the first 1-3 files; cache results in DB keyed by (path, mtime, size) so re-ingests skip probing.

**FTP network scan with 64 threads:**
- Problem: `scan_network_ftp` uses `ThreadPoolExecutor(max_workers=64)` probing a /24 range on ports 21/2221 (`app/core/ftp.py:120-161`) — bursts of traffic on camera networks.
- Files: `app/core/ftp.py`
- Cause: Needs quick discovery, but 64 concurrent sockets is aggressive on production WiFi.
- Improvement path: Reduce to 16-24 workers; add per-host timeout and abort when a session is already picked.

**Watcher does full `os.walk` per pass:**
- Problem: `app/core/watcher.py` polling loop re-walks the whole source tree every interval, building `scanned_files` up to 10k entries.
- Files: `app/core/watcher.py`
- Cause: Polling design (no OS notifications on all platforms).
- Improvement path: Cache directory mtimes, skip subtrees unchanged since last pass; increase interval during idle.

**MTP download uses full-file block size:**
- Problem: `app/core/mtp.py` `_stage_one` downloads whole files (block size = file size) with no chunked streaming, so progress is coarse and large files can stall perceived progress.
- Files: `app/core/mtp.py:640-682`
- Cause: Simplest WPD API usage.
- Improvement path: Read in 1-4 MB chunks and emit progress per chunk.

## Fragile Areas

**Shared camera-detection state (`_cam_done`, `_cam_timer`):**
- Files: `app/ui/main_window.py:2130-2163`
- Why fragile: Single flag + single-shot timer reused by many call sites; no ownership tracking; races between timer fire, scan thread completion, and `_prompt_unknown_camera`.
- Safe modification: Add a monotonically increasing detection token; only the latest token may set `_cam_done` or show the prompt; cancel timers on token change.
- Test coverage: None (see gaps).

**Global COM singleton `mtp._DEVICE_MANAGER`:**
- Files: `app/core/mtp.py` (`_manager()`), used from `main_window` (UI thread) and worker threads.
- Why fragile: COM object created once, reused across threads with per-call `CoInitialize`/`CoUninitialize`; `_value_to_filetime` reads a generated inner COM attribute (`__MIDL____MIDL_itf_PortableDeviceApi_0001_00000001`) that may differ across comtypes/Windows versions.
- Safe modification: Keep all WPD calls on one dedicated thread; wrap `_manager()` in a lock; replace direct inner-attr access with a getattr fallback.
- Test coverage: `tests/test_mtp.py` 203 lines (mock-based), `tests/test_mtp_integration.py` 60 lines (hardware-dependent, skipped in CI-less env).

**Cross-thread SQLite with `check_same_thread=False`:**
- Files: `app/core/db.py:32-53` (`get_connection`), used by watcher thread, ingestor threads, worker threads.
- Why fragile: Connection-per-call mitigates it, but WAL + concurrent writers can hit `database is locked` (timeout=5 s then error); no `PRAGMA foreign_keys=ON` so orphaned rows accumulate silently.
- Safe modification: Single writer serialization (lock around writes), enable `foreign_keys`, surface lock errors instead of swallowing.
- Test coverage: `tests/test_db.py` 186 lines — happy-path CRUD only.

**Network calls on UI thread (beyond auto-sync):**
- Files: `app/ui/main_window.py` (WiFi panel, FTP picker `app/ui/ftp_picker.py:120-156` connect button, `_sync_wifi_sessions`), `app/core/ftp.py:340-380`
- Why fragile: Any 15 s `timeout` in FTP profile blocks the UI thread (dialog "connect" status, panel refresh).
- Safe modification: Route connect/list through `_AssistantWorker`-style QThread (pattern already in `app/ui/selective_dump.py:104-123`).

**Updater helper scripts (bat/bash) per platform:**
- Files: `app/core/updater.py:200-262`
- Why fragile: Script text embedded in Python; quoting edge cases (spaces in paths, non-ASCII temp dirs) can break the move/relaunch; `zipfile.extractall` on macOS has traversal risk.
- Safe modification: Keep scripts minimal, use `subprocess` list-args, test in non-ASCII paths, prefer `os.replace` loops over bat for move.

## Scaling Limits

**`recent_paths` capped at 10 per type:**
- Files: `app/core/db.py:296-299`
- Current capacity: 10 rows per `path_type`; older entries deleted on each save.
- Limit: Operators with many sources lose history quickly.
- Scaling path: Raise cap or drop to on-demand pruning.

**Watcher `scanned_files` set capped at 10k:**
- Files: `app/core/watcher.py`
- Current capacity: 10,000 entries before pruning → potential re-ingest (see Known Bugs).
- Limit: SD cards with >10k files (RAW+video sets) exceed this.
- Scaling path: Persist scanned inventory per source; prune oldest by first-seen time.

**Inbox tokens never rotate/expire:**
- Files: `app/core/db.py` (`inbox_senders.token`), `app/core/shoot_inbox.py`
- Current capacity: One permanent token per sender name.
- Limit: A leaked token (shared QR) grants permanent upload access to that sender's cache dir.
- Scaling path: Add token expiry + regeneration button in WiFi panel; per-URL nonce.

**Single-dump target rotation for full disks:**
- Files: `app/core/ingestor.py` (`_pick_dump_target`, `_full_targets`)
- Current capacity: Rotates among configured targets; when all report full → abort with "Disco lleno".
- Limit: No auto-switch to a new folder on the same disk (only other configured targets).
- Scaling path: Allow on-the-fly target addition during ingest; retry later instead of hard abort.

## Dependencies at Risk

**`comtypes` runtime type generation:**
- Risk: `_ensure_types()` calls `comtypes.client.GetModule("portabledeviceapi.dll")` at runtime (`app/core/mtp.py:157-167`); generated gen-code depends on comtypes version and Windows SDK state. Broken generation = MTP support dies with obscure import errors.
- Impact: SD-card-via-USB ingest unavailable.
- Migration plan: Pin `comtypes` version in `requirements.txt`; cache generated modules in the freeze; add a smoke test that imports `PortableDeviceApiLib` early.

**PySide6 range `>=6.5,<7`:**
- Risk: Broad version range; Qt private API use (e.g., `selective_dump.py` `_find_grid` hack for `QCalendarWidget.hitTest` not exposed in 6.11) breaks across minor upgrades.
- Impact: Silent visual/behavioral regressions in calendar and dialogs.
- Migration plan: Pin tested minor (e.g., `>=6.7,<6.12`), run UI review after each bump (see `tests/test_e2e.py` for a start).

**PyInstaller freeze assumptions:**
- Risk: `_resolve_db_path` branches on `getattr(sys, "frozen", False)` (`app/core/db.py:8-30`); `notifications` looks for sounds relative to exe dir; `wheat_field` loads `wheat_ear.svg` via `resource_path`.
- Impact: Dev vs packaged behavior drift (different DB file, missing sounds, missing background).
- Migration plan: Centralize resource/dir resolution in `app/core/utils.py:resource_path` and assert all data dirs are created at startup.

## Missing Critical Features

**No log file / diagnostics:**
- Problem: Production crashes and silent failures (see Tech Debt: no logging) leave users with no way to report what happened. Support can't diagnose DB lock or MTP errors.
- Blocks: Reliable bug triage and remote debugging.

**Inbox server has no rate limit or max upload size:**
- Problem: `app/core/shoot_inbox.py` `_handle_upload` accepts any Content-Length; a rogue client can fill the cache disk.
- Blocks: Safe use on shared networks.

**No "re-ingest/reorganize after metadata fix" flow:**
- Problem: Files ingested with wrong metadata (timeout fallback "Unknown", file_size 0) cannot be re-scanned without a full re-ingest workaround.
- Blocks: Recovery from metadata-engine fallback bugs without deleting rows.

## Test Coverage Gaps

**`main_window.py` (3870 lines) — untested:**
- What's not tested: Session start/stop flow, camera detection races, WiFi reception lifecycle, format/shutdown actions, auto-sync polling, rename flows.
- Files: `app/ui/main_window.py`
- Risk: The two confirmed bugs in this file (`_cam_done` race, rename LIKE pattern) shipped without detection; UI-thread freezes go unnoticed.
- Priority: High

**Watcher + notifications + theme + wifi_panel:**
- What's not tested: `app/core/watcher.py` pruning/re-ingest, `app/core/notifications.py` sound play (thread), `app/ui/wifi_panel.py` QR/URL rendering, `app/ui/theme.py` QSS palettes.
- Files: `app/core/watcher.py`, `app/core/notifications.py`, `app/ui/wifi_panel.py`, `app/ui/theme.py`
- Risk: Silent behavior regressions in ingest triggering and cross-platform sound.
- Priority: Medium

**DB edge cases:**
- What's not tested: Migration `ALTER` paths on legacy DBs, lock contention, `_resolve_db_path` frozen/non-frozen, plaintext secret handling.
- Files: `tests/test_db.py` (186 lines), `app/core/db.py`
- Risk: Migration failures on upgrade are the most common support incident for desktop apps.
- Priority: High

**Metadata fallback paths:**
- What's not tested: ffprobe timeout → "Unknown" fallback, `file_size=0`, `date_source` mtime fallback, `detect_camera_batch` confidence with <10 files.
- Files: `tests/test_metadata_engine.py` (205 lines), `app/core/metadata_engine.py`
- Risk: Silent miscategorization corrupts downstream organization reports.
- Priority: Medium

**No CI workflow:**
- What's not tested: Nothing runs automatically on push; `tests/` (all `unittest`) rely on the developer running them manually.
- Files: (no `.github/workflows/`)
- Risk: Regressions reach users untested.
- Priority: High

---

*Concerns audit: 2026-08-15*
