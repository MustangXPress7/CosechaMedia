---
phase: 260816-mcj-arreglar-mtp-manager-com-por-hilo-y-reub
verified: 2026-08-16T00:00:00Z
status: passed
score: 6/6 truths verified
behavior_unverified: 0
overrides_applied: 0
---

# Quick 260816-mcj Verification Report

**Goal:** Arreglar MTP (manager COM por hilo) y reubicar volcado selectivo a orígenes, añadir columnas de borrado por fila y hacer la columna de ruta resizable
**Verified:** 2026-08-16
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1 | MTP detecta dispositivos: `_manager()` usa `threading.local()` (`_manager_local`), NO existe `_DEVICE_MANAGER` global en mtp.py; `devicename` usa `f"{name}_{serial}"` sin duplicado | ✓ VERIFIED | `app/core/mtp.py:157` `_manager_local = threading.local()`; `_manager()` :432-439 lee/escribe `_manager_local.device_manager`; `grep _DEVICE_MANAGER` → 0 matches en mtp.py; `self.devicename = f"{self.name}_{self.serial}"` :214; consumidores `WpdBackend.list_devices()` :452 y `_WpdSession._friendly_name()` :238 pasan ambos por `_manager()`. Comportamiento probado por test que pasa: `test_manager_is_thread_local` (mismo objeto en mismo hilo, objeto distinto en otro hilo, 2 creaciones) y `test_list_devices_uses_current_thread_manager` (regresión RPC_E_WRONG_THREAD con fake DM) |
| 2 | «Volcado selectivo…» está en `src_scan_row` (tras «Escanear cámaras») y NO en `op_row`; `_open_selective_dump` intacto | ✓ VERIFIED | `main_window.py:442-445` `btn_selective_dump` definido y añadido a `src_scan_row` entre `btn_scan_cameras` (:440) y `addStretch` (:447); `op_row` :623-636 contiene solo `btn_reorganize` + `btn_clear_completed`; `_open_selective_dump` :3790 intacto e implementado (guarda proyecto + abre `SelectiveDumpAssistant`). Test `test_selective_dump_button_in_scan_row_not_operations` pasa |
| 3 | Col0 de `source_list` es `QHeaderView.Interactive` con ancho 320; `setMinimumSectionSize(40)`; columnas de borrado Fixed 40 px | ✓ VERIFIED | `main_window.py:410` `setSectionResizeMode(0, QHeaderView.Interactive)`; :415 `resizeSection(0, 320)`; :414 `setMinimumSectionSize(40)`; :413/:418 col3 Fixed + `resizeSection(3, 40)`; :654/:659 col5 Fixed + `resizeSection(5, 40)`; `stretchLastSection(False)` en ambos headers :409/:652. Test `test_source_path_column_interactive_with_default_width` pasa (incluye resize real 320→200) |
| 4 | `source_list` tiene 4 columnas con borrado por fila (🗑) que llama a `_delete_source_at_row` (confirmación default No); `btn_remove_source`/`_remove_selected_source`/`_update_remove_source_button` no existen | ✓ VERIFIED | `main_window.py:405` `setColumnCount(4)`; :2034 `setCellWidget(row, 3, self._build_remove_source_button(row))`; `_build_remove_source_button` :2103-2110 (🗑 24×24, connect a `_delete_source_at_row`); `_delete_source_at_row` :2304-2325 usa `QMessageBox.question(..., QMessageBox.No)` como default; grep de `btn_remove_source`/`_remove_selected_source`/`_update_remove_source_button` → 0 matches; `_show_source_context_menu` conservado :2293-2302. Tests `test_source_list_has_per_row_delete_column`, `test_source_delete_button_removes_source_with_confirmation`, `test_source_delete_button_no_keeps_session` pasan |
| 5 | `self.table` tiene 6 columnas con borrado por fila que solo hace `removeRow` vía `indexFromItem(row_item).row()` (nunca db/fs); funciona con tabla ordenable | ✓ VERIFIED | `main_window.py:645` `QTableWidget(0, 6)`; :1588 `setCellWidget(row, 5, self._build_remove_file_button(filename_item))`; `_build_remove_file_button` :2112-2119 captura el ITEM; `_remove_file_row` :2121-2125 = `indexFromItem(row_item).row()` + guard `row < 0` + `removeRow` — cero llamadas a db/fs; sorting activo :661. Comportamiento probado por test que pasa: `test_files_table_delete_follows_sorting` (tras `sortItems(0)`, el click quita SOLO la fila de BBB vía `indexFromItem`) y `test_files_table_delete_button_removes_row_only` (sesiones en BD sin cambios) |
| 6 | Tests: `TestThreadLocalManager` en tests/test_mtp.py (3 tests, skip no-Windows); tests de ubicación del volcado selectivo, col0 Interactive, columnas de borrado por fila en tests/test_source_content.py; los 2 tests existentes actualizados (columnCount 4 y 6 + range(6)) | ✓ VERIFIED | `tests/test_mtp.py:244-345` clase `TestThreadLocalManager` con `@unittest.skipUnless(sys.platform == "win32", ...)` y los 3 tests (`test_manager_is_thread_local`, `test_list_devices_uses_current_thread_manager`, `test_wpd_session_devicename_no_duplicate`); `tests/test_source_content.py` con 7 tests nuevos relevantes (:128-198); tests existentes actualizados: `columnCount(), 4` :72 y `columnCount(), 6` + `range(6)` :117-118. Ejecución real: `python -m unittest tests.test_mtp tests.test_source_content -v` → 30 tests OK (los 3 de TestThreadLocalManager se ejecutaron, plataforma win32); `python -m unittest discover -s tests -v` → 252 OK, 3 skipped (preexistentes MTP live) |

**Score:** 6/6 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `app/core/mtp.py` | Manager COM thread-local + devicename sin duplicado | ✓ VERIFIED | `_manager_local` :157, `_manager()` thread-local :426-440, `devicename` :214 |
| `app/ui/main_window.py` | Volcado selectivo en src_scan_row, col0 Interactive/320, borrado por fila en ambas tablas, papelera retirada | ✓ VERIFIED | :405-418, :442-445, :645-659, :1588, :2034, :2103-2125, :2304-2325 |
| `tests/test_mtp.py` | `TestThreadLocalManager` (3 tests, skip no-Windows) | ✓ VERIFIED | :244-345; pasan en ejecución real |
| `tests/test_source_content.py` | Tests ubicación volcado selectivo, col0 Interactive, borrado por fila; existentes a 4/6 columnas | ✓ VERIFIED | :72, :117-118, :128-198; 17 tests OK en ejecución real |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | -- | ------ | ------- |
| `_manager()` | `threading.local()` | `_manager_local.device_manager` get/set (:432-439) | WIRED | `list_devices` (hilo principal, :452) y `_friendly_name` (worker QThread, :238) usan cada uno su propio manager; sin `_DEVICE_MANAGER` global |
| `btn_selective_dump` (src_scan_row) | `_open_selective_dump` | `clicked.connect` (:444) | WIRED | Slot intacto :3790; no hay `op_row.addWidget(self.btn_selective_dump)` |
| `source_list` col 3 | `_delete_source_at_row` | `_build_remove_source_button` → `clicked.connect(lambda: self._delete_source_at_row(row))` (:2109) | WIRED | Confirmación default No (:2321) → `_remove_source_path` (:2327) |
| `table` col 5 | `_remove_file_row` | `_build_remove_file_button(filename_item)` → `_remove_file_row` (:2118) | WIRED | `indexFromItem(row_item).row()` + guard + `removeRow` (:2121-2125); 0 llamadas db/fs |
| Header source_list | col0 Interactive 320 | `setSectionResizeMode(0, Interactive)` + `resizeSection(0, 320)` (:410, :415) | WIRED | `setMinimumSectionSize(40)` (:414) permite columnas Fixed 40 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `btn_selective_dump` → `_open_selective_dump` | `source` / `project_config` | `self.source_input.currentText()`, `self._source_paths`, `db.get_sessions` (:3796+) | Yes — no static fallback | ✓ FLOWING |
| `_delete_source_at_row` | `path`, `sessions` | `db.get_sessions(self.current_project_id)` (:2311) | Yes — DB query | ✓ FLOWING |
| `_remove_file_row` | — | Ninguna (solo vista) | N/A — por diseño: nunca db/fs | ✓ (intencional) |
| `WpdBackend.list_devices` | `devices` | `_manager()` → `DM.GetDevices` real (mockeado en tests) | Yes | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Manager COM thread-local (mismo objeto mismo hilo, distinto en otro, 2 creaciones) | `python -m unittest tests.test_mtp.TestThreadLocalManager.test_manager_is_thread_local -v` | ok | ✓ PASS |
| list_devices usa el manager del hilo actual (regresión RPC_E_WRONG_THREAD) | `python -m unittest tests.test_mtp.TestThreadLocalManager.test_list_devices_uses_current_thread_manager -v` | ok | ✓ PASS |
| devicename `{name}_{serial}` sin duplicado | `python -m unittest tests.test_mtp.TestThreadLocalManager.test_wpd_session_devicename_no_duplicate -v` | ok | ✓ PASS |
| Borrado por fila en tabla ordenable resuelve fila correcta | `python -m unittest tests.test_source_content.TestSourceContent.test_files_table_delete_follows_sorting -v` | ok | ✓ PASS |
| Borrado fila tabla ingesta solo-vista (BD intacta) | `python -m unittest tests.test_source_content.TestSourceContent.test_files_table_delete_button_removes_row_only -v` | ok | ✓ PASS |
| Borrado origen con confirmación Yes/No | `python -m unittest tests.test_source_content.TestSourceContent.test_source_delete_button_removes_source_with_confirmation -v` | ok | ✓ PASS |
| Volcado selectivo en scan_row y NO en op_row | `python -m unittest tests.test_source_content.TestSourceContent.test_selective_dump_button_in_scan_row_not_operations -v` | ok | ✓ PASS |
| Col0 Interactive + resize real | `python -m unittest tests.test_source_content.TestSourceContent.test_source_path_column_interactive_with_default_width -v` | ok | ✓ PASS |

### Probe Execution

| Probe | Command | Result | Status |
| ----- | ------- | ------ | ------ |
| Suite completa sin regresiones (gate #5 del plan) | `python -m unittest discover -s tests -v` | 252 OK, 3 skipped (MTP live preexistentes) | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| UI-04 | PLAN requirements: [UI-04, UI-05] | (per REQUIREMENTS.md: mejoras UI de tablas/columnas) | ✓ SATISFIED | Col0 Interactive, borrado por fila en ambas tablas, volcado selectivo reubicado — verificado en main_window.py y tests |
| UI-05 | PLAN requirements: [UI-04, UI-05] | (per REQUIREMENTS.md: UI de orígenes) | ✓ SATISFIED | `source_list` 4 columnas con borrado por fila y confirmación default No |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | Sin markers TBD/FIXME/XXX en archivos modificados | — | None |
| `main_window.py` :407/:648 | — | Cabeceras vacías `""` en columnas de borrado | ℹ️ Info | Intencional (spec del plan: columna de borrado sin cabecera) |

### Human Verification Required

Ninguno. Los comportamientos dependientes de estado (thread-locality, sort-safe delete, confirmación default No) están ejercitados por tests que pasan. La revisión visual con dispositivo MTP real queda como opcional no bloqueante (plan, paso 6).

### Gaps Summary

Sin gaps. Las 6 truths del plan se cumplen con evidencia de código y tests en verde.

---

_Verified: 2026-08-16_
_Verifier: the agent (gsd-verifier)_
