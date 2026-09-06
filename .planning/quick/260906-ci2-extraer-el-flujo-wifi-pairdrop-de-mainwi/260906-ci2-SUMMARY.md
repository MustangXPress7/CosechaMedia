---
quick_id: 260906-ci2
slug: extraer-el-flujo-wifi-pairdrop-de-mainwi
title: Extraer el flujo WiFi/PairDrop de MainWindow a un WifiMixin
subsystem: ui
tags: [pyqt, pyside6, refactor, mixin, wifi, pairdrop, main_window]

# Dependency graph
requires: []
provides:
  - WifiMixin con los 24 métodos WiFi/PairDrop de MainWindow (app/ui/mixins/wifi_mixin.py)
  - Paquete app/ui/mixins/ con workers helpers (_StageWorker, _TaskWorker, DashboardBackground)
affects: [ui, main_window, wifi, mtp, ftp]

# Actuals (#2632) — pairs with the plan's `estimate` to calibrate future estimates.
# Same estimateTokens scale (chars/4 over the realized diff), never a harness token count.
# Este quick task no declara `estimate` en su frontmatter; los actuals quedan como referencia.
actuals:
  tokens: 13999
  tasks: 3
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Mixin composition: MainWindow(QMainWindow, WifiMixin) para dividir un god object por dominio"
    - "Paquete app/ui/mixins/ para helpers de nivel de módulo reutilizados por MainWindow"

key-files:
  created:
    - app/ui/mixins/wifi_mixin.py
    - app/ui/mixins/workers.py
    - app/ui/mixins/__init__.py
  modified:
    - app/ui/main_window.py
    - tests/test_wifi_source.py

key-decisions:
  - "Import lazy de ORG_TYPE_MAP dentro de _ingestor_for_wifi_session para evitar import circular (main_window ↔ mixin)"
  - "Se incluye translator en los imports de wifi_mixin.py siguiendo la lista literal del plan aunque ningún método movido lo referencia"
  - "Los tests de test_wifi_source.py se adaptan para parchear el singleton db en app.ui.mixins.wifi_mixin (convención del proyecto: singleton reemplazable a nivel de módulo)"

requirements-completed: []

# Metrics
duration: ~40min
completed: 2026-09-06
status: complete
---

# Quick Task 260906-ci2: Extraer el flujo WiFi/PairDrop de MainWindow a un WifiMixin

**Refactor puro: 24 métodos WiFi/PairDrop movidos verbatim a `app/ui/mixins/wifi_mixin.py` (clase `WifiMixin` compuesta en `MainWindow(QMainWindow, WifiMixin)`), helpers `_StageWorker`/`_TaskWorker`/`DashboardBackground` extraídos a `app/ui/mixins/workers.py`; main_window.py baja de 5139 → ~4590 líneas reales (4159 según Measure-Object -Line) sin cambio de comportamiento.**

## Performance

- **Duration:** ~40 min
- **Started:** 2026-09-06
- **Completed:** 2026-09-06
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- `WifiMixin` con los 24 métodos WiFi/PairDrop (2663-2676, 2699-2715, 4012-4196, 4206-4470, 4510-4516) copiados byte-verbatim, verificado con diff programático contra 271c357
- `MainWindow(QMainWindow, WifiMixin)` compone el mixin sin tocar la API pública; lógica y estado `self.*` intactos
- `workers.py` con `_StageWorker`, `DashboardBackground`, `_TaskWorker` — también byte-verbatim (verificado contra 271c357:92-148)
- main_window.py pasa de ~4670 → 4159 líneas según `Measure-Object -Line` (objetivo del plan: < 4250)
- Suite completa: 399 tests, `failures=1` — el fallo (`test_mtp.TestThreadLocalManager.test_wpd_session_devicename_no_duplicate`) es **pre-existente**, reproducido de forma idéntica en HEAD limpio (271c357) en corridas full-suite

## Task Commits

Cada tarea se commiteó atómicamente:

1. **Task 1: Extraer WifiMixin** - `f574a76` (refactor)
2. **Task 2: Extraer worker helpers** - `6e3fe5f` (refactor)

_Nota: la Task 3 (verificación global) no produjo cambios de código; sus verificaciones se documentan en este resumen._

## Files Created/Modified
- `app/ui/mixins/wifi_mixin.py` - Clase `WifiMixin` con los 24 métodos WiFi/PairDrop movidos verbatim desde main_window.py (508 líneas)
- `app/ui/mixins/workers.py` - `_StageWorker`, `DashboardBackground`, `_TaskWorker` (64 líneas)
- `app/ui/mixins/__init__.py` - Marcador de paquete vacío
- `app/ui/main_window.py` - Eliminados los 24 métodos WiFi + banner + 3 clases worker; añadidos imports de mixins; `class MainWindow(QMainWindow, WifiMixin)`; eliminados imports muertos `QPainter` y `paint_wheat_field`
- `tests/test_wifi_source.py` - Adaptado para parchear `wifi_mixin_module.db` en setUp/tearDown (4 líneas: import + 2 asignaciones + restauración)

## Decisions Made
- **Import lazy de ORG_TYPE_MAP:** `from app.ui.main_window import ORG_TYPE_MAP` como primera línea del cuerpo de `_ingestor_for_wifi_session` (después del docstring) — única desviación de "movimiento verbatim" permitida por el plan para evitar el import circular
- **`translator` en wifi_mixin.py:** se incluye según la lista literal de imports del plan, aunque ningún método movido lo referencia directamente (import muerto inofensivo, documentado)
- **Adaptación de tests:** la convención del proyecto exige singletons reemplazables a nivel de módulo; al mover los métodos a `wifi_mixin`, el parche `mw.db = self.db` de los tests dejó de alcanzarlos. Se añade `wifi_mixin_module.db = self.db` en setUp/tearDown, mismo patrón que ya usa `ingestor_module.db`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test patching de `db` no alcanzaba los métodos movidos**
- **Found during:** Task 1 (verificación post-extracción)
- **Issue:** `test_wifi_source.py` parchea `mw.db = self.db` (singleton a nivel de módulo de `app.ui.main_window`), pero los 24 métodos WiFi ahora resuelven `db` desde el namespace de `app.ui.mixins.wifi_mixin` → 23 errores + 5 fallos en `test_wifi_source`
- **Fix:** Añadir `wifi_mixin_module.db = self.db` en setUp y restauración en tearDown (patrón ya usado para `ingestor_module.db`)
- **Files modified:** `tests/test_wifi_source.py`
- **Verification:** `python -m unittest tests.test_wifi_source` → 55 tests OK tras el fix
- **Committed in:** `f574a76` (parte del commit de Task 1)

**2. [Rule 1 - Limpieza] Imports muertos tras extraer `DashboardBackground`**
- **Found during:** Task 2 (verificación post-extracción)
- **Issue:** `QPainter` (línea 13) y `paint_wheat_field` (línea 29) quedaron sin uso en main_window.py tras mover `DashboardBackground` a workers.py
- **Fix:** Eliminados ambos imports (se conserva `import app.ui.wheat_field as wheat_field`, que sigue en uso)
- **Files modified:** `app/ui/main_window.py`
- **Verification:** `rg` confirma 0 usos; compileall OK; test_main_window 57 OK
- **Committed in:** `6e3fe5f` (parte del commit de Task 2)

---

**Total deviations:** 2 auto-fixed (1 bug de tests directamente causado por la extracción, 1 limpieza de imports)
**Impact on plan:** Ambos fixes necesarios para que la suite pasara tras el refactor. Sin scope creep; cero cambios de comportamiento.

## Issues Encountered
- **Verificación byte-verbatim inicial engañosa:** la primera comparación contra `git show HEAD` comparaba contra el commit de Task 1 (líneas ya desplazadas +1), no contra 271c357. Se re-verificó contra 271c357 explícitamente → MATCH.
- **Line endings:** el Write tool escribe LF; el repo trabaja en CRLF (autocrlf=true, working tree w/crlf). Se convirtió workers.py a CRLF para consistencia.
- **`rg -c "    def "` del plan devuelve 25, no 24:** el patrón cuenta la closure anidada `def _wifi_sessions()` (8 espacios) dentro de `_bind_wifi_sender`. Con `^    def ` (solo nivel de clase) son exactamente 24. El plan asumía un patrón que coincidía con la closure; la intención (24 métodos top-level) se cumple.
- **Fallos pre-existentes de la suite** (ver abajo, no causados por este refactor).

## Fallos pre-existentes documentados (fuera de scope)

1. **`test_wpd_session_devicename_no_duplicate` (test_mtp) falla solo en full-suite:** reproducido de forma idéntica en worktree limpio en HEAD (271c357): `Ran 399 tests ... FAILED (failures=1, skipped=5)`. En aislamiento (`discover -s tests -p test_mtp.py`) pasa (13 OK) en ambos árboles. Es una interacción de tests a nivel de suite, no del refactor.
2. **Crash de intérprete al salir (`0xC0000409`) tras test_wifi_source/full-suite:** presente también en HEAD limpio (baseline: exit=-1073740791 tras "OK"). Es un teardown de Qt/offscreen pre-existente; los tests pasan antes del crash.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- main_window.py reducido de ~4670 → 4159 líneas (Measure-Object -Line), objetivo del plan cumplido (< 4250)
- El paquete `app/ui/mixins/` queda como ubicación canónica para futuros mixins (MTP/FTP da la misma pauta)
- Cualquier quick task futuro que siga extrayendo dominios de MainWindow puede reutilizar el patrón WifiMixin + composición

---

*Quick task: 260906-ci2*
*Completed: 2026-09-06*

## Self-Check: PASSED

- FOUND: `.planning/quick/260906-ci2-extraer-el-flujo-wifi-pairdrop-de-mainwi/260906-ci2-SUMMARY.md`
- FOUND: `app/ui/mixins/wifi_mixin.py`
- FOUND: `app/ui/mixins/workers.py`
- FOUND: `app/ui/mixins/__init__.py`
- FOUND: commit `f574a76` (refactor(ui): extract WiFi mixin from main_window)
- FOUND: commit `6e3fe5f` (refactor(ui): extract worker helpers to app/ui/mixins/workers.py)