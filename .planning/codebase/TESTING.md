# Testing Patterns

**Analysis Date:** 2026-08-17

## Test Framework

**Runner:**
- Python's standard library `unittest` (Python 3.11). Pytest is not installed and not used anywhere — all 16 test modules use `unittest.TestCase`.
- No test configuration files exist (`pytest.ini`, `setup.cfg`, `pyproject.toml`, `tox.ini` — none present).
- `tests/__init__.py` (11 lines) changes the working directory to a fresh `tempfile.mkdtemp(prefix="sdimport_tests_")` **at import time** so app code never touches the real `data/sd_import.db`, and inserts the repo root into `sys.path` so `from app.core...` imports resolve.

**Assertion Library:**
- Standard `unittest` assertions: `assertEqual`, `assertTrue`, `assertFalse`, `assertIsNone`, `assertIn`, `assertNotIn`, `assertRaises`, `assertGreater`, `assertLess`, `assertAlmostEqual`, `assertIsInstance`.
- Mock assertions: `assert_called_once_with`, `assert_called_once`, `assert_any_call` (`tests/test_updater.py`, `tests/test_metadata_engine.py`, `tests/test_ftp.py`).

**Run Commands:**
```bash
python -m unittest discover tests            # Run all tests
python -m unittest tests.test_db             # Single module
python -m unittest tests.test_db.TestDatabaseManager.test_create_session   # Single test
python -m unittest tests.test_ingestor tests.test_updater   # Multiple modules
```
- Coverage: no coverage tool installed (`coverage` is not in `requirements.txt`), no coverage config, no coverage target.

## Test File Organization

**Location:**
- All tests live in `tests/` — one file per app module, never co-located with sources.

**Naming:**
- Files: `test_<module>.py` → `tests/test_db.py`, `tests/test_ingestor.py`, `tests/test_updater.py`, `tests/test_metadata_engine.py`, `tests/test_ftp.py`, `tests/test_mtp.py`, `tests/test_shoot_inbox.py`, `tests/test_selective_dump.py`, `tests/test_source_picker.py`, `tests/test_source_content.py`, `tests/test_icons.py`, `tests/test_main_window.py`.
- `tests/test_wifi_source.py` (905 lines, the largest) covers `app/ui/wifi_panel.py` and `app/ui/wifi_picker.py`; `tests/test_e2e.py` drives the full `MainWindow`.
- Classes: `Test<Area>` — `TestDatabaseManager`, `TestIngestor`, `TestMetadataEngine`, `TestUpdater`, `TestFtpClient`, `TestFtpSyncWorker`, `TestShootInbox`, `TestDumpTarget`, `TestCameraDetectionToken`, `TestRenameCamera`, `TestFreeSpace`, `TestIntegrityReport`, `TestIcons`.
- Methods: `test_<behavior_in_english>` — descriptive snake_case like `test_copy_verified_removes_partial_on_failure`, `test_create_session_rejects_invalid_source`.

**Structure:**
```
tests/
├── __init__.py                  # chdir to temp dir + sys.path bootstrap
├── test_db.py                   # DatabaseManager unit tests
├── test_ingestor.py             # Ingestor unit tests (FakeMeta, monkeypatched db)
├── test_updater.py              # Updater unit tests (mock.patch)
├── test_metadata_engine.py      # MetadataEngine + date scanning tests
├── test_ftp.py                  # FTP client + sync worker (FakeFtpConnection)
├── test_mtp.py                  # MTP staging with fake session trees
├── test_mtp_integration.py      # Live MTP device tests (skipped without hardware)
├── test_shoot_inbox.py          # HTTP receive server tests
├── test_selective_dump.py       # Selective dump UI + worker tests
├── test_wifi_source.py          # WiFi panel/picker UI tests
├── test_source_picker.py        # Source picker dialog tests
├── test_source_content.py       # Source content dialog tests
├── test_icons.py                # SVG icon tinting + registry tests
├── test_main_window.py          # MainWindow regression tests (camera detection, rename, free space, reports)
└── test_e2e.py                  # Full offscreen ingest flow through MainWindow
```

## Test Structure

**Suite Organization:**
```python
# tests/test_db.py — setup pattern
class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sdimport_test_db_")
        self.db = DatabaseManager(db_path=os.path.join(self.tmp, "test.db"))

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.tmp, ignore_errors=True)
```

**Patterns:**
- Fixture setup in `setUp`, cleanup in `tearDown` with `shutil.rmtree(tmp, ignore_errors=True)` — every test uses an isolated temp dir.
- App-level fixture in `setUpClass` (Qt tests): `cls.app = QApplication.instance() or QApplication([])` (`tests/test_source_picker.py:14-15`, `tests/test_selective_dump.py:23`, `tests/test_wifi_source.py:47-49`, `tests/test_e2e.py:16`, `tests/test_main_window.py:30-31`, `tests/test_icons.py:33-34`).
- Module-level `_make_source()`, `_tree()`, `_assets()` helper functions build fixtures per test module (`tests/test_mtp.py:14-45`, `tests/test_wifi_source.py:90-120`).
- Regression tests named with the bug number in the docstring: `test_qr_ingest_registers_status_in_table` with `"""Bug 1: ..."""` (`tests/test_wifi_source.py:180-187`), `test_wifi_panel_stop_toggles_to_resume` with `"""Bug 6: ..."""` (`tests/test_wifi_source.py:291-295`).
- Mixed language: test method names and assertion messages in English; docstrings and inline comments mostly Spanish.

## Mocking

**Framework:** `unittest.mock` — `mock.patch`, `mock.patch.object`, `mock.MagicMock`, `mock.call` (`tests/test_updater.py`, `tests/test_metadata_engine.py`, `tests/test_ftp.py`).

**Patterns:**

Module-level singleton replacement (the dominant pattern in `tests/test_ingestor.py`):
```python
import app.core.ingestor as ingestor_module

class TestIngestor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sdimport_test_ingest_")
        self.db = DatabaseManager(db_path=os.path.join(self.tmp, "ingest.db"))
        self._orig_db = ingestor_module.db
        ingestor_module.db = self.db

    def tearDown(self):
        ingestor_module.db = self._orig_db          # restore module singleton
        self.db.close()
        shutil.rmtree(self.tmp, ignore_errors=True)
```
This works because consumers reference `from app.core.ingestor import db` — actually they use the module attribute at call time; the same pattern patches `main_window_module.db`, `selective_dump_module.db`, `mtp_module.db` (`tests/test_selective_dump.py:27-36`, `tests/test_wifi_source.py:51-57`, `tests/test_main_window.py:35-41`).

Multi-module singleton patching (for `MainWindow` tests that touch ingestor + metadata_engine):
```python
# tests/test_main_window.py:35-41 — patch all three singletons used by MainWindow
self._orig_db = mw.db
self._orig_ing_db = ingestor_module.db
self._orig_me_db = me_module.db
mw.db = self.db
ingestor_module.db = self.db
me_module.db = self.db
```

`mock.patch` / `patch.object` (used in `tests/test_updater.py`, `tests/test_metadata_engine.py`, `tests/test_ftp.py`):
```python
@mock.patch("app.core.updater.os.path.exists", return_value=True)
def test_download_file_with_existing_file(self, mock_exists):
    ...
```
```python
with mock.patch.object(ftp_module.ftplib, "FTP", return_value=fake_conn):
    ...
```

**Hand-written fakes** (interfaces are stubbed by hand, not with MagicMock, when behavior matters):
- `FakeMeta` — dict-like metadata object mimicking ffprobe output keys (`tests/test_ingestor.py:18-31`, `tests/test_selective_dump.py:80-96`).
- `FakeSession` / tree fixtures — in-memory MTP/WPD session tree with `children()`, `_resolve()`, `download()` implementing the same protocol as the real backend (`tests/test_mtp.py:14-45`).
- `FakeFtpConnection` — emulates `ftplib.FTP` interface for FTP staging (`tests/test_ftp.py:14-55`).
- `StubNotif` — replaces `NotificationManager` to capture calls (`tests/test_wifi_source.py:83-88`, `tests/test_e2e.py:24-28`).
- `FakeWorker`, `_FakeProcess` — simulate QProcess/QThread stages (`tests/test_selective_dump.py:97-111`, `tests/test_wifi_source.py:122-150`).

**What to Mock:**
- External side effects: `subprocess.run`, `ftplib.FTP`, `urllib.request.urlopen`, `QMessageBox`/`QFileDialog` (patched to return canned values without showing dialogs), `os.path.exists` for update-download paths, `sys.platform` for drive enumeration (`tests/test_db.py:40-42`).
- The module-level singletons (`db`, `metadata_engine`) when the unit under test depends on them.

**What NOT to Mock:**
- Real filesystem operations (copy/MD5/date-scan) run against real temp dirs — `test_copy_verified_*` and `test_scan_for_dates_batch_*` create real files and assert real bytes/hashes.
- Real `sqlite3` via a throwaway `DatabaseManager(db_path=...)` in a temp dir — never a mocked DB driver.

## Fixtures and Factories

**Test Data:**
```python
# tests/test_mtp.py — factory building a fake session tree
def _tree():
    return {
        "DCIM/100CANON": [
            RemoteFile(rel_path="DCIM/100CANON/IMG_0001.CR2", name="IMG_0001.CR2", size=3000, date_modified=None, is_dir=False),
            ...
        ],
        ...
    }
```
```python
# tests/test_ingestor.py — real files for copy/MD5 tests
def _make_source(self, name="IMG_0001.JPG"):
    src = os.path.join(self.tmp, name)
    with open(src, "wb") as f:
        f.write(b"fake-jpeg-data-12345")
    return src
```

**Location:**
- Fixtures are helper functions/classes defined at module level inside each test file — there is no shared `conftest.py` or `tests/fixtures/` directory (unittest style, not pytest).

## Coverage

**Requirements:** None enforced — no coverage config, no coverage dependency, no coverage command in `Compilar.bat` or `.github/workflows/build.yml`.

**View Coverage:** Not available without installing `coverage`:
```bash
python -m pip install coverage
python -m coverage run -m unittest discover tests
python -m coverage report
```

## Test Types

**Unit Tests:**
- DB layer: full CRUD against real SQLite temp files — `TestDatabaseManager` covers sessions, configs, FTP profiles, QR payloads, migrations (`tests/test_db.py`).
- Pure logic: version parsing/comparison (`tests/test_updater.py`), date scanning (`tests/test_metadata_engine.py`), sanitizers (`tests/test_shoot_inbox.py`, `tests/test_db.py:185-210`), `DumpTarget` date/organize resolution (`tests/test_ingestor.py:198-240`).
- Copy path: real-file copy with MD5 verification, partial-copy cleanup on failure (`tests/test_ingestor.py`).
- Icon system: SVG tinting, weakref registry, `refresh_all()` dead-ref cleanup (`tests/test_icons.py`).
- MainWindow regression: camera detection token race prevention, `rename_camera` separator handling, `_free_space` edge cases, `generate_integrity_report` CSV output (`tests/test_main_window.py`).

**Integration Tests:**
- MTP staging walk/download with fake session trees but real cache-dir logic (`tests/test_mtp.py`).
- FTP sync worker with `FakeFtpConnection` + real temp dirs (`tests/test_ftp.py`).
- `tests/test_shoot_inbox.py` runs a **real** `http.server` on `127.0.0.1` port 0 in a thread and posts real multipart uploads.
- `tests/test_wifi_source.py` runs a real socket listener to probe `tcp_open()` banner detection.

**E2E Tests:**
- `tests/test_e2e.py` (130 lines): instantiates the real `MainWindow` offscreen, calls `start_ingest()`, and polls with `QApplication.processEvents()` + `time.sleep(0.05)` until `window.finished` (async ingest driven to completion).
- `tests/test_selective_dump.py` (421 lines): drives the `SelectiveDump` UI offscreen with `QTest.mouseClick` on real buttons.

**Device-Dependent Tests:**
- `tests/test_mtp_integration.py` (70 lines) is skipped when no MTP device is present:
```python
@unittest.skipUnless(_MTP_AVAILABLE, "comtypes o WPD no disponibles")
class TestMtpIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ...
        if not cls.devices:
            cls.skipTest("sin dispositivo MTP conectado")
```
- Run these only on a machine with a real MTP device attached; they will silently skip elsewhere.

## Common Patterns

**Async/Threaded Testing:**
```python
# tests/test_e2e.py — pump the Qt event loop until an async worker finishes
def _wait_done(self, window, timeout=10.0):
    deadline = time.time() + timeout
    while not window.finished and time.time() < deadline:
        QApplication.processEvents()
        time.sleep(0.05)
    self.assertTrue(window.finished, "ingesta no terminó en {timeout}s")
```

**Error Testing:**
```python
# tests/test_updater.py
with self.assertRaises(UpdateError):
    updater.download_file("http://127.0.0.1:1/nope.exe", dest)

# tests/test_shoot_inbox.py — HTTP error surfaced
with self.assertRaises(urllib.error.HTTPError):
    ...
```

**Qt Event-Loop Testing:**
- Set the offscreen platform **before** importing PySide6, at the very top of the module:
```python
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
```
(see `tests/test_e2e.py:1-8`, `tests/test_wifi_source.py:1-9`, `tests/test_selective_dump.py:1-12`, `tests/test_main_window.py:14`, `tests/test_icons.py:17`).
- Use `QTest.mouseClick(widget, Qt.LeftButton)` for real widget interaction and `QApplication.processEvents()` to flush pending signals.
- Assert UI state directly on widgets: `window.btn_start.text()`, `window.table.rowCount()`, `window.status_label.text()` (`tests/test_wifi_source.py`).

**subTest for Parameterized Checks:**
```python
# tests/test_icons.py:36-39 — iterate catalog without separate test methods
def test_icon_returns_non_null_for_all_names(self):
    for name in ICON_NAMES:
        with self.subTest(name=name):
            self.assertFalse(icons.icon(name).isNull())
```

## Coverage Gaps

- **CI runs no tests**: `.github/workflows/build.yml` only installs deps and runs PyInstaller — a regression can be merged without any test execution.
- `app/ui/main_window.py` (~4000 lines) has `test_main_window.py` (10 tests) plus indirect coverage from `test_e2e.py`, `test_wifi_source.py`, `test_source_content.py`, and `test_selective_dump.py`. No dedicated test for session management UI, formatting flows, or the new QSplitter/delicate toggle layout.
- `app/core/watcher.py` and `app/core/notifications.py` (sound/dialog paths) have no direct tests; `app/core/sd_reader.py` (card brand detection) has none.
- `app/ui/icons.py` is tested but only for the 13-icon catalog — edge cases like missing SVG directory, corrupted SVG, or concurrent `refresh_all()` during widget creation are not covered.
- No coverage measurement exists, so untested branches are invisible.

---

*Testing analysis: 2026-08-17*
