# Coding Conventions

**Analysis Date:** 2026-08-17

## Language & Runtime Context

- Python 3.11 desktop application (PySide6/Qt), packaged with PyInstaller (`main.spec`).
- No linting or formatting configuration exists in the repo: no `pyproject.toml`, `setup.cfg`, `ruff.toml`, `.flake8`, `.pylintrc`, or `.prettierrc`. Code follows an informal PEP 8 style (4-space indent, snake_case, 88–120 char lines tolerated — e.g. `app/core/db.py:297`).
- Source modules: `app/core/` (business logic) and `app/ui/` (Qt interface). Tests in `tests/`.

## Naming Patterns

**Files:**
- snake_case matching the module's main symbol: `app/core/metadata_engine.py`, `app/core/db.py`, `app/ui/main_window.py`.
- Test files: `tests/test_<module>.py` (`test_db.py`, `test_ingestor.py`, `test_main_window.py`).

**Classes:**
- PascalCase: `DatabaseManager` (`app/core/db.py:20`), `Ingestor` (`app/core/ingestor.py:114`), `MainWindow` (`app/ui/main_window.py:157`), `DumpTarget` (`app/core/ingestor.py:91`).
- Exception classes end in `Error`: `UpdateError` (`app/core/updater.py:32`), `MtpError` (`app/core/mtp.py:29`).
- Non-exported UI/helper classes prefixed with `_`: `_SilentMessageBox` (`app/core/notifications.py:12`), `_StageWorker`, `_TaskWorker` (`app/ui/main_window.py:91,130`).
- Reusable custom `QWidget` subclasses use PascalCase without `_` prefix: `ElidedLabel` (`app/ui/main_window.py:149`) — a `QLabel` that elides text with `'...'` when it exceeds `maximumWidth()`.
- PySide6 `QObject`/`QMainWindow`/`QDialog` subclasses declare Qt signals at class level: `file_started = Signal(str)` etc. (`app/core/ingestor.py:115-121`).

**Functions/Methods:**
- snake_case: `get_connection`, `create_session`, `handle_new_file`, `date_key_for_file`.
- Module-private helpers get a leading `_`: `_free_space` (`app/core/ingestor.py:24`), `_is_system_entry` (`app/core/metadata_engine.py:26`), `_parse_version` (`app/core/updater.py:41`), `_windows_mounted_drives` (`app/core/utils.py:53`).
- Private methods of classes also use `_`: `_process_single_file`, `_copy_verified`, `_determine_date` (`app/core/ingestor.py`). Tests exercise these private methods directly (`self.ing._process_single_file(...)` in `tests/test_ingestor.py:65`) — private methods are part of the testable surface.
- MainWindow private helper methods follow `_verb_noun` pattern: `_device_key_for_source()` (`app/ui/main_window.py:2198`), `_build_source_cell()` (`app/ui/main_window.py:2082`), `_toggle_device_delicate()` (`app/ui/main_window.py:2206`), `_detect_camera_for_session()` (`app/ui/main_window.py:2309`). These are all `MainWindow` methods called internally.
- Build helper methods for table cell widgets: `_build_source_cell()`, `_build_delicate_button()`, `_build_content_button()`, `_build_remove_source_button()` — all return a `QWidget` for a `QTableWidget` cell.

**Variables:**
- snake_case instance attributes, including private ones with `_` prefix: `self._stop_event`, `self._inflight_lock`, `self._session_file` (`app/core/ingestor.py:148-181`).
- Window/panel widgets on `MainWindow` are public attributes (`self.window.btn_start`, `self.window.table`, `self.window.source_list` in `tests/test_e2e.py`, `tests/test_wifi_source.py`).

**Types:**
- UPPER_SNAKE constants at module level: `WIFI_DEVICE_ID = "wifi:pairdrop"` (`app/core/db.py:18`), `VIDEO_EXTENSIONS` (`app/core/metadata_engine.py:11`), `_SYSTEM_DIR_NAMES` (`app/core/metadata_engine.py:17`), `DEFAULT_THEME`, `ACCENTS` (`app/ui/theme.py`).
- Type hints are used throughout (PEP 484 with `from typing import Optional, Dict, List, Tuple, Callable, Set` — see `app/core/ingestor.py:8`, `app/core/db.py:6`). Newer code also uses bare builtins in annotations (`metadata: dict` in `app/core/metadata_engine.py:76`, `set` return in `app/core/metadata_engine.py:386`). Prefer `Optional[X]` for nullable values; `-> None` on mutating methods.
- `@dataclass` used for value objects: `DeviceInfo`, `RemoteFile` (`app/core/mtp.py:33-48`).

## Code Style

**Formatting:**
- No formatter is configured. Follow the existing style: 4-space indentation, two blank lines between top-level defs, blank line before class methods.
- Quote style: single quotes dominate (`app/core/ingestor.py:44`, `app/core/metadata_engine.py:11`) but double quotes appear in QSS strings and some dict literals (`app/ui/theme.py`, `app/core/db.py`). Match the surrounding file.
- Long SQL/string literals are broken with implicit concatenation across lines (`app/core/db.py:433-438`).

**Linting:**
- Not detected — no linter config or linter dependency in `requirements.txt`. There is a `__pycache__` for Python 3.11 (`.pyc` files in `app/core/__pycache__/`).

## Import Organization

**Order:**
1. Standard library modules (`os`, `sys`, `json`, `time`, `threading`, `tempfile`, `subprocess`).
2. Third-party/PySide6 imports (`PySide6.QtWidgets`, `PySide6.QtCore`).
3. First-party `app.*` imports.

Example from `app/ui/main_window.py:1-39` and `app/core/ingestor.py:1-13`.

**Path Aliases:**
- No path aliases — imports are relative to repo root via the `app` package: `from app.core.db import db`, `from app.ui import theme`, `from app.core import ftp, mtp`.
- `tests/__init__.py:11` inserts the repo root into `sys.path` so `from app...` imports work under `python -m unittest`.

**Local (function-level) imports:**
- Platform-specific or one-off heavy modules are imported inside functions: `import ctypes` (`app/core/utils.py:54,124`), `import shutil` (`app/core/sd_reader.py:46`), `import hashlib` (`app/core/ingestor.py:36`), `import subprocess` (`app/ui/main_window.py:54`). Follow this pattern for platform-gated code.

## Error Handling

**Patterns:**
- Core modules catch broad `Exception`, log via `print(f"Error <action> <path>: {e}")`, and return safe defaults — the desktop app must never crash:
  - `app/core/utils.py:49-51` returns `""` on MD5 failure.
  - `app/core/ingestor.py:68-74` returns `False` and removes the partial destination.
  - `app/core/metadata_engine.py:250-258` returns an empty/default metadata dict on ffprobe failure.
- Bare `except:` is used in a few places to deliberately swallow errors: `app/core/ingestor.py:201,520` (session save, file move), `app/core/sd_reader.py:73,88,100,112,124` (best-effort card detection). Avoid adding new bare `except:`; use `except Exception` with a comment when swallowing is intentional.
- Custom exception types for domain errors that must propagate: `UpdateError` (`app/core/updater.py`), `MtpError` (`app/core/mtp.py`).
- Background work pattern: QObject worker classes catch exceptions in `run()` and emit them through Qt signals — `self.done.emit(False, str(e))` (`app/ui/main_window.py:106-147`, `_StageWorker`, `_TaskWorker`).
- User-facing errors: `QMessageBox` for blocking UI (`app/ui/notifications.py`, `app/ui/main_window.py`) and `raise RuntimeError(translator.tr("..."))` for precondition violations (`app/ui/main_window.py:50`).
- Long-running operations report progress via callback or dict-return instead of exceptions: `Ingestor._stats` with `processed/errors/skipped` (`app/core/ingestor.py:167-172`), `stage_device_folder` results dict with `errors` (`app/core/mtp.py`, `app/core/ftp.py`).

## Logging

**Framework:** `console` — plain `print()`; the `logging` module is not used anywhere.

**Patterns:**
- `print(f"Error <action> <path/context>: {e}")` in exception handlers (16 call sites, e.g. `app/core/ingestor.py:69,299,384`, `app/core/utils.py:50`, `app/core/metadata_engine.py:257`, `app/ui/main_window.py:146`).
- `print(f"Watcher started on: {self.source_dir}")` for lifecycle info (`app/core/watcher.py:27`).
- Do not add a logging framework without a deliberate decision; match the `print(f"...")` style.

## Comments

**When to Comment:**
- Comments explain **why**, not what: e.g. `app/core/metadata_engine.py:31` explains why system dirs must be skipped; `app/core/watcher.py:39-41` explains a Windows path-checking pitfall.
- Section separator banners with `# -----...` used in `app/core/mtp.py:51-53,107-109`.
- Comments are predominantly **Spanish**; English appears in older code. Match the dominant language of the file (Spanish).

**JSDoc/TSDoc:**
- Not applicable (Python). Docstrings are triple-quoted (`"""..."""`) and predominantly Spanish:
  - Module docstrings for non-obvious modules: `app/core/mtp.py:1-17`, `app/core/updater.py:1-7`, `app/ui/theme.py:1-6`, `app/ui/icons.py:1-12`.
  - Function docstrings for non-trivial behavior, often documenting callbacks and return shapes: `scan_for_dates_batch` (`app/core/metadata_engine.py:298-312`), `get_or_create_wifi_session` (`app/core/db.py:714-724`), `copy_verified` (`app/core/ingestor.py:31-35`).
  - One-line docstrings for simple functions: `resource_path` (`app/core/utils.py:7`).

## Function Design

**Size:** Functions are small and focused. Complex flows are decomposed into private methods (`Ingestor._run_single_file`, `_pick_dump_target`, `_copy_verified` in `app/core/ingestor.py`). Module-level free functions hold pure logic: `_human_bytes`, `_free_space`, `copy_verified` (`app/core/ingestor.py:16-74`), `compare_versions`, `download_file`, `sha256sum` (`app/core/updater.py`).

**Parameters:**
- Constructors with many optional parameters use keyword defaults: `Ingestor.__init__` takes 14 parameters (`app/core/ingestor.py:123-132`); `DatabaseManager(db_path=None)` (`app/core/db.py:21`).
- Callbacks are passed as keyword args with `None` defaults: `progress_cb`, `cancel_cb`, `on_error` (throughout `app/core/`).
- Public DB methods use `**kwargs` with an allowlist filter (`update_session_config` at `app/core/db.py:503-511`, `update_ftp_profile` at `app/core/db.py:653`).

**Return Values:**
- Success/failure as booleans (`copy_verified` returns `bool`), dicts with status keys, or `None` for "not found" (`get_session` returns `None`, `app/core/db.py:479`).
- Consistent stats dict shapes across stages: `{"staged", "skipped", "errors"}` for MTP/FTP staging; `{"processed", "errors", "skipped"}` for ingest.

## Module Design

**Exports:**
- Modules define classes and module-level singleton instances: `db = DatabaseManager()` (`app/core/db.py:988`), `metadata_engine = MetadataEngine()` (`app/core/metadata_engine.py:429`), `sd_reader = SDReader()` (`app/core/sd_reader.py:179`).
- Consumer modules import the singleton and call it directly: `from app.core.db import db`, `from app.core.metadata_engine import metadata_engine` (`app/core/ingestor.py:9-11`, `app/ui/main_window.py:17-22`).
- Tests monkeypatch attributes of these singletons or replace the module-level reference (`ingestor_module.db = self.db` in `tests/test_ingestor.py:40`) — keep singletons attribute-replaceable at module scope.

**Barrel Files:** Not used. `app/__init__.py` only holds `__version__` (`app/__init__.py:3`). Import directly from the defining module.

## Database Patterns

**Schema additions:**
- New tables are added to `_init_schema()` in `app/core/db.py` via `CREATE TABLE IF NOT EXISTS`. Example: `device_settings` table with `device_key TEXT PRIMARY KEY` (`app/core/db.py:247-250`).
- Table naming: lowercase plural (`device_settings`, `sessions`, `projects`).
- Primary key convention: `device_key TEXT PRIMARY KEY` for composite identifiers (e.g. FTP profile IDs, WPD PnP IDs, volume serials).

**CRUD pattern:**
- Each table gets a pair of getter/setter methods on `DatabaseManager`: `get_device_delicate(device_key)` / `set_device_delicate(device_key, delicate)` (`app/core/db.py:960-985`).
- Getter returns the value or `None` if not found. Setter uses `INSERT OR REPLACE`.
- Always `conn.commit()` then `conn.close()` in the setter; getter calls `conn.close()` after fetching.

## UI Patterns

**Source list columns (QTableWidget, 5 columns):**
| Column | Content | Resize | Widget |
|--------|---------|--------|--------|
| 0 | Source path (text item + cell widget with checkbox + path label + optional device button) | Interactive, 300px | `QTableWidgetItem` (hidden text) + `_build_source_cell()` widget |
| 1 | Camera name | Interactive, 150px | `QTableWidgetItem` (editable in manual mode) |
| 2 | Delicate mode toggle | Fixed, 32px | `_build_delicate_button()` → `QPushButton` |
| 3 | Content filter | Interactive, 100px | `_build_content_button()` |
| 4 | Remove source | Fixed, 40px | `_build_remove_source_button()` → icon `QPushButton` |

Configured at `app/ui/main_window.py:420-447`. Refreshed by `_refresh_source_list()` (`app/ui/main_window.py:2032-2070`).

**Custom reusable widgets:**
- `ElidedLabel` (`app/ui/main_window.py:149-154`): `QLabel` subclass that overrides `setText()` to elide text with `'...'` via `fontMetrics().elidedText()` when text exceeds `maximumWidth()`. Use for truncated paths in table cells.

**Icon system:**
- SVG icons rendered from `app/ui/assets/icons/*.svg` with `#FF00FF` placeholder replaced by palette color (`app/ui/icons.py:24`).
- `icons.apply(button, name, size)` sets the icon and registers the button for `refresh_all()` re-tinting on theme change (`app/ui/icons.py:82-85`).
- 13 icons in catalog: `refresh`, `plus`, `minus`, `x`, `pencil`, `copy`, `folder`, `gear`, `trash`, `camera`, `phone`, `wifi`, `globe` (`tests/test_icons.py:25-28`).

## Cross-Cutting Conventions

**Internationalization:**
- Every user-facing string goes through translation: `translator.tr("...")` at module level or `self.tr("...")` inside QWidget/QObject classes (`app/core/translator.py:69-71`). Interpolation uses Qt placeholders: `translator.tr("Formateando %1 (%2/%3)...").arg(path).arg(i).arg(len(paths))` (`app/ui/main_window.py:67`).
- Default language is Spanish (`DEFAULT_LANGUAGE = "es"`, `app/core/translator.py:15`). New UI text must be wrapped in `tr()` or it will not appear in Spanish/English switch.

**Platform handling:**
- `sys.platform` branching with dedicated per-platform helpers (`app/core/utils.py:53-119`, `app/core/updater.py:77-82`).
- PyInstaller detection via `getattr(sys, "frozen", False)` for resource paths (`app/core/utils.py:9`, `app/core/db.py:9`, `app/core/updater.py:170`).
- Use `resource_path()` (`app/core/utils.py:6`) for any bundled asset path.

**Threading:**
- Qt signals for cross-thread UI updates; `threading.Lock` for shared counters/sets (`Ingestor._inflight_lock`, `_target_lock` in `app/core/ingestor.py`).
- SQLite connections created per-operation with `check_same_thread=False` and `WAL` (`app/core/db.py:26-28`); always `conn.commit()` then `conn.close()` after use.

**UI construction:** Widgets are built programmatically (no `.ui` files); QSS theming centralized in `app/ui/theme.py` with `@placeholder` tokens resolved by `build_qss()`.

---

*Convention analysis: 2026-08-17*
