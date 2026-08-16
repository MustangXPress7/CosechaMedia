---
schema_version: 1
open_count: 1
waived_count: 1
fixed_count: 1
total_count: 2
last_updated: 2026-08-15T18:00:00.000Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 01 | unrun-verify | tests/test_wifi_source.py | 726 | Suite cuelga en test_pick_wifi_source_ftp_opens_ftp_picker: mock de app.ui.wifi_picker.WifiMethodDialog no intercepta binding import-time main_window.py:39 (REVISA OPERADOR, fix en v2) | fixed | Fix aplicado en v2 (mismo milestone): en app/ui/main_window.py el binding de WifiMethodDialog se movió a import local dentro de `_pick_wifi_source()`, de modo que `mock.patch("app.ui.wifi_picker.WifiMethodDialog")` intercepta al call-site. Suite `python -m unittest discover -s tests` → 215 tests OK (skipped=3); el test que antes colgaba ahora pasa. | 2026-08-15T16:56:42.834Z | 2026-08-15T18:00:00.000Z |
| 2 | 01 | deviation | .planning/phases/01-auditor-a-ui-y-plan-de-reubicaci-n/baseline_git.txt |  | BOM UTF-8 eliminado para que el gate de conjuntos compare exacto (Rule 3 fix) | waived | Desviación aceptada: la eliminación del BOM fue necesaria para que el gate de conjuntos git del plan 03 comparara exacto (la codificación del archivo en disco tenía BOM, la lectura en memoria no). Sin impacto en los entregables; documentado en VERIFICATION.md §Anti-Patterns (Línea 161, WINDOWS.md id 2). | 2026-08-15T16:56:43.326Z | 2026-08-15T18:00:00.000Z |

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
  }
]
````
