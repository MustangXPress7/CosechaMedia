---
schema_version: 1
open_count: 5
waived_count: 1
fixed_count: 1
total_count: 7
last_updated: 2026-09-08T09:38:29.865Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 01 | unrun-verify | tests/test_wifi_source.py | 726 | Suite cuelga en test_pick_wifi_source_ftp_opens_ftp_picker: mock de app.ui.wifi_picker.WifiMethodDialog no intercepta binding import-time main_window.py:39 (REVISA OPERADOR, fix en v2) | fixed | Fix aplicado en v2 (mismo milestone): en app/ui/main_window.py el binding de WifiMethodDialog se movió a import local dentro de `_pick_wifi_source()`, de modo que `mock.patch("app.ui.wifi_picker.WifiMethodDialog")` intercepta al call-site. Suite `python -m unittest discover -s tests` → 215 tests OK (skipped=3); el test que antes colgaba ahora pasa. | 2026-08-15T16:56:42.834Z | 2026-08-15T18:00:00.000Z |
| 2 | 01 | deviation | .planning/phases/01-auditor-a-ui-y-plan-de-reubicaci-n/baseline_git.txt |  | BOM UTF-8 eliminado para que el gate de conjuntos compare exacto (Rule 3 fix) | waived | Desviación aceptada: la eliminación del BOM fue necesaria para que el gate de conjuntos git del plan 03 comparara exacto (la codificación del archivo en disco tenía BOM, la lectura en memoria no). Sin impacto en los entregables; documentado en VERIFICATION.md §Anti-Patterns (Línea 161, WINDOWS.md id 2). | 2026-08-15T16:56:43.326Z | 2026-08-15T18:00:00.000Z |
| 3 | 01.6.0 | deviation | tests/test_mtp.py |  | Flake por orden de suite (pre-existente): test_wpd_session_devicename_no_duplicate falla solo en suite completa; verificado en worktree limpio en HEAD 551e180 | open |  | 2026-09-05T09:50:31.420Z |  |
| 4 | 01.6.0 | deviation | tests/test_e2e.py |  | Flake de timing bajo carga (pre-existente): e2e rotativo 'segunda ingesta no termino a tiempo' en suite completa; pasa aislado; disco C: con ~4,4 GB libres | open |  | 2026-09-05T09:50:31.784Z |  |
| 5 | quick-260906-ci2 | unrun-verify | tests/test_mtp.py | 374 | test_wpd_session_devicename_no_duplicate falla solo en full-suite (pre-existente en HEAD, pasa aislado) | open |  | 2026-09-06T07:45:55.854Z |  |
| 6 | quick-260906-epl | deviation | tests/test_mtp.py | 374 | Falla pre-existente dependiente del orden: tests/test_mtp.py::TestThreadLocalManager::test_wpd_session_devicename_no_duplicate falla solo en suite completa (pasa en aislamiento); idéntica en HEAD 9cf857f. Descubierta durante quick 260906-epl (refactor UI, no relacionada). | open |  | 2026-09-06T09:02:24.671Z |  |
| 7 | quick-260908-f5o | unrun-verify | tests/test_main_window.py | 977 | test_rename_in_dialog_ftp_prefix falla (QLineEdit sin setEditText) por cambios sin commitear de 260907-fb2 en add_source_dialog.py — pre-existente, fuera de scope | open |  | 2026-09-08T09:38:29.865Z |  |

````json
[
  {
    "id": 1,
    "kind": "unrun-verify",
    "phase": "01",
    "file": "tests/test_wifi_source.py",
    "line": 726,
    "description": "Suite cuelga en test_pick_wifi_source_ftp_opens_ftp_picker: mock de app.ui.wifi_picker.WifiMethodDialog no intercepta binding import-time main_window.py:39 (REVISA OPERADOR, fix en v2)",
    "status": "fixed",
    "reason": "Fix aplicado en v2 (mismo milestone): en app/ui/main_window.py el binding de WifiMethodDialog se movió a import local dentro de `_pick_wifi_source()`, de modo que `mock.patch(\"app.ui.wifi_picker.WifiMethodDialog\")` intercepta al call-site. Suite `python -m unittest discover -s tests` → 215 tests OK (skipped=3); el test que antes colgaba ahora pasa.",
    "recorded_at": "2026-08-15T16:56:42.834Z",
    "resolved_at": "2026-08-15T18:00:00.000Z"
  },
  {
    "id": 2,
    "kind": "deviation",
    "phase": "01",
    "file": ".planning/phases/01-auditor-a-ui-y-plan-de-reubicaci-n/baseline_git.txt",
    "line": null,
    "description": "BOM UTF-8 eliminado para que el gate de conjuntos compare exacto (Rule 3 fix)",
    "status": "waived",
    "reason": "Desviación aceptada: la eliminación del BOM fue necesaria para que el gate de conjuntos git del plan 03 comparara exacto (la codificación del archivo en disco tenía BOM, la lectura en memoria no). Sin impacto en los entregables; documentado en VERIFICATION.md §Anti-Patterns (Línea 161, WINDOWS.md id 2).",
    "recorded_at": "2026-08-15T16:56:43.326Z",
    "resolved_at": "2026-08-15T18:00:00.000Z"
  },
  {
    "id": 3,
    "kind": "deviation",
    "phase": "01.6.0",
    "file": "tests/test_mtp.py",
    "line": null,
    "description": "Flake por orden de suite (pre-existente): test_wpd_session_devicename_no_duplicate falla solo en suite completa; verificado en worktree limpio en HEAD 551e180",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-09-05T09:50:31.420Z",
    "resolved_at": null
  },
  {
    "id": 4,
    "kind": "deviation",
    "phase": "01.6.0",
    "file": "tests/test_e2e.py",
    "line": null,
    "description": "Flake de timing bajo carga (pre-existente): e2e rotativo 'segunda ingesta no termino a tiempo' en suite completa; pasa aislado; disco C: con ~4,4 GB libres",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-09-05T09:50:31.784Z",
    "resolved_at": null
  },
  {
    "id": 5,
    "kind": "unrun-verify",
    "phase": "quick-260906-ci2",
    "file": "tests/test_mtp.py",
    "line": 374,
    "description": "test_wpd_session_devicename_no_duplicate falla solo en full-suite (pre-existente en HEAD, pasa aislado)",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-09-06T07:45:55.854Z",
    "resolved_at": null
  },
  {
    "id": 6,
    "kind": "deviation",
    "phase": "quick-260906-epl",
    "file": "tests/test_mtp.py",
    "line": 374,
    "description": "Falla pre-existente dependiente del orden: tests/test_mtp.py::TestThreadLocalManager::test_wpd_session_devicename_no_duplicate falla solo en suite completa (pasa en aislamiento); idéntica en HEAD 9cf857f. Descubierta durante quick 260906-epl (refactor UI, no relacionada).",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-09-06T09:02:24.671Z",
    "resolved_at": null
  },
  {
    "id": 7,
    "kind": "unrun-verify",
    "phase": "quick-260908-f5o",
    "file": "tests/test_main_window.py",
    "line": 977,
    "description": "test_rename_in_dialog_ftp_prefix falla (QLineEdit sin setEditText) por cambios sin commitear de 260907-fb2 en add_source_dialog.py — pre-existente, fuera de scope",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-09-08T09:38:29.865Z",
    "resolved_at": null
  }
]
````
