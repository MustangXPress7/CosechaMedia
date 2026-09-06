---
phase: quick-260906-fgl
plan: 01
subsystem: ui
tags: [pyside6, mixin, refactor, main-window, god-object, camera-detection]

# Dependency graph
requires:
  - phase: quick-260906-ci2
    provides: Patrón canónico WifiMixin (movimiento VERBATIM de métodos a mixin propio, composición por MRO, singleton db a nivel de módulo patch-eable)
provides:
  - CameraMixin (app/ui/mixins/camera_mixin.py) con los 16 métodos de detección/nombrado de cámara y lectura SD, cuerpos VERBATIM
  - MainWindow compuesto como `class MainWindow(QMainWindow, WifiMixin, CameraMixin)` con los 16 métodos eliminados del cuerpo
  - Parche paralelo del singleton `db` en 5 ficheros de test (18 setUps) para el namespace nuevo del mixin
  - main_window.py reducido de 4141 a 3750 líneas (-391)
affects: bloques siguientes de reducción del god object MainWindow (roadmap 2026-09-06), auditoría UI

actuals:
  tokens: 14663    # chars/4 sobre el diff realizado (58655 chars) — escala del estimate (30000)
  tasks: 3
  commits: 1

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Mixin UI con herederos: CameraMixin sin __init__ ni super().__init__(), singletons importados a nivel de módulo (db, sd_reader, metadata_engine, get_mounted_drives) para patch por namespace de módulo"
    - "Hoisting de imports locales de método (import threading / import uuid) a nivel de módulo del mixin — única desviación del VERBATIM, ordenada por el plan"

key-files:
  created:
    - app/ui/mixins/camera_mixin.py
  modified:
    - app/ui/main_window.py
    - tests/test_main_window.py
    - tests/test_source_content.py
    - tests/test_e2e.py
    - tests/test_wifi_source.py
    - tests/test_session_content_modes.py

key-decisions:
  - "Composición por MRO: class MainWindow(QMainWindow, WifiMixin, CameraMixin) — CameraMixin antes de QMainWindow para que las llamadas cruzadas (wifi_mixin.py:345, self._drive_label, self._detect_camera_for_session, self._on_dialog_camera_name_changed) resuelvan por el mixin"
  - "Namespace del singleton: los 16 métodos resuelven db desde app.ui.mixins.camera_mixin — los tests que reasignan mw.db = self.db DEBEN reasignar también camera_mixin_module.db = self.db (18 setUps en 5 ficheros)"
  - "get_mounted_drives retirado del import de app.core.utils en main_window.py (quedó huérfano tras el movimiento); sd_reader y metadata_engine permanecen (siguen en uso)"

patterns-established:
  - "Extracción VERBATIM método-por-método con verificación programática de equivalencia contra `git show HEAD` (substring-check por par método+cierre) — mismo patrón de WifiMixin"
  - "Parche paralelo del singleton db: en cada setUp/tearDown que reasigna mw.db = self.db se añade camera_mixin_module.db = self.db / restauración con _orig_cam_db"

requirements-completed: [QUICK-260906-fgl]

coverage:
  - id: D1
    description: "app/ui/mixins/camera_mixin.py — 16 métodos de cámara/SD movidos VERBATIM desde MainWindow (detección de cámara por sesión/fuente, prompt de nombre, persistencia de mapping, rename post-ingesta, detección SD, auto-detección de unidades), con imports de módulo os/threading/uuid/QtCore/QtWidgets/db/sd_reader/metadata_engine/get_mounted_drives"
    requirement: QUICK-260906-fgl
    verification:
      - kind: other
        ref: "python -m compileall -q app/ui/mixins/camera_mixin.py (pass)"
        status: pass
      - kind: other
        ref: "import offscreen: from app.ui.mixins.camera_mixin import CameraMixin (pass)"
        status: pass
      - kind: other
        ref: "VERBATIM-CHECK: substring-check de los 16 pares método+EOF contra git show HEAD (pass)"
        status: pass
    human_judgment: false
  - id: D2
    description: "app/ui/main_window.py — class MainWindow(QMainWindow, WifiMixin, CameraMixin), 16 métodos eliminados, get_mounted_drives retirado del import de app.core.utils, cero definiciones duplicadas de eventFilter en el MRO"
    requirement: QUICK-260906-fgl
    verification:
      - kind: other
        ref: "verify script del plan: DEFS-REMAINING NONE / COMPOSITION PASS / GET_MOUNTED PASS / MRO-IMPORT PASS / CALLSITES-MRO PASS (pass)"
        status: pass
      - kind: other
        ref: "compileall + import offscreen de app.ui.main_window (pass)"
        status: pass
      - kind: other
        ref: "python -m unittest tests.test_wifi_source -q → Ran 55 tests, OK (pass)"
        status: pass
    human_judgment: false
  - id: D3
    description: "5 ficheros de test con parche paralelo del singleton: camera_mixin_module.db = self.db en cada setUp que construye MainWindow, restauración en tearDown — 18 setUps en 5 ficheros"
    requirement: QUICK-260906-fgl
    verification:
      - kind: other
        ref: "chequeo estructural: todo mw.db = self.db tiene su camera_mixin_module.db = self.db paralelo (18/18, PASS)"
        status: pass
      - kind: other
        ref: "5 ficheros en aislamiento (unittest -v): test_main_window 57 OK / test_source_content 16 OK / test_e2e 3 OK / test_wifi_source 55 OK / test_session_content_modes 13 OK (pass)"
        status: pass
      - kind: other
        ref: "python -m pytest tests/ -q → 393 passed, 5 skipped, 28 subtests; única falla tests/test_mtp.py::TestThreadLocalManager::test_wpd_session_devicename_no_duplicate, pre-existente order-dependent (pass)"
        status: pass
    human_judgment: false

# Metrics
duration: 20min
completed: 2026-09-06
status: complete
---

# Quick 260906-fgl: Bloque 3 — Extraer la detección/nombrado de cámara y lectura SD a CameraMixin

**Los 16 métodos de detección/nombrado de cámara y lectura de tarjeta SD de MainWindow se mueven VERBATIM a un nuevo `CameraMixin` (app/ui/mixins/camera_mixin.py) compuesto por MRO (`class MainWindow(QMainWindow, WifiMixin, CameraMixin)`), con el singleton db parcheado en paralelo (`camera_mixin_module.db = self.db`) en 18 setUps de 5 ficheros de test — main_window.py baja de 4141 a 3750 líneas (-391)**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-09-06T11:27:53Z
- **Completed:** 2026-09-06T11:47:52Z
- **Tasks:** 3
- **Files modified:** 7 (1 creado + 6 modificados)

## Accomplishments

- `CameraMixin` (app/ui/mixins/camera_mixin.py, 408 líneas) con los 16 métodos: `_on_camera_rename_needed`, `_post_ingest_rename_dialog`, `_prompt_rename_camera`, `_drive_label` (@staticmethod), `_find_smallest_media`, `_set_camera_cell_text`, `_camera_for_path`, `_detect_camera_for_session`, `_prompt_nombre_dispositivo`, `_detect_camera_for_source`, `_persist_camera_mapping`, `_on_camera_cell_edited`, `_on_dialog_camera_name_changed`, `_detect_sd_card`, `_on_auto_detect_toggled`, `_auto_detect_removable_drives`
- Cuerpos VERBATIM verificados programáticamente contra `git show HEAD` (substring-check por par método+cierre); única desviación: hoisting de `import threading`/`import uuid` a nivel de módulo (líneas 2284-2285 originales de `_detect_camera_for_session`), ordenado por el plan
- `class MainWindow(QMainWindow, WifiMixin, CameraMixin):` — resolución por MRO verificada: 16 métodos invocables sobre instancia, `eventFilter` definido una única vez (main_window.py:2497, ninguno de los movidos lo define)
- `get_mounted_drives` retirado del import de `app.core.utils` (huérfano tras el movimiento); 0 imports huérfanos nuevos introducidos
- 18 setUps en 5 ficheros de test con el parche paralelo `camera_mixin_module.db = self.db` + restauración `_orig_cam_db` (14 en test_main_window, 1 en cada uno de los otros 4)
- Suite completa: 393 passed / 5 skipped / 28 subtests — única falla pre-existente no relacionada (ver Issues)

## Task Commits

Commit único tras las 3 tareas, según la sección Output del plan:

1. **T1 + T2 + T3: extracción de CameraMixin + composición + parche de tests** - `bc650bf` (refactor)

**Plan metadata:** commits docs gestionados por el orquestador (no incluidos aquí).

## Files Created/Modified

- `app/ui/mixins/camera_mixin.py` - `CameraMixin` (408 líneas): 16 métodos VERBATIM + imports de módulo `os`, `threading`, `uuid`, `QTimer/QDate/QSettings`, `QInputDialog/QMessageBox`, `db`, `sd_reader`, `metadata_engine`, `get_mounted_drives`; sin `__init__` ni `super().__init__()` (precedente WifiMixin)
- `app/ui/main_window.py` - `class MainWindow(QMainWindow, WifiMixin, CameraMixin)`; 16 métodos eliminados; −`get_mounted_drives` del import de `app.core.utils`; +import `from app.ui.mixins.camera_mixin import CameraMixin`; 3750 líneas (verificado: ninguna definición de los 16 métodos queda en el cuerpo)
- `tests/test_main_window.py` - 14 pares setUp/tearDown con `import app.ui.mixins.camera_mixin as camera_mixin_module`, `self._orig_cam_db = camera_mixin_module.db`, `camera_mixin_module.db = self.db`, restauración en tearDown
- `tests/test_source_content.py`, `tests/test_e2e.py`, `tests/test_wifi_source.py`, `tests/test_session_content_modes.py` - 1 par setUp/tearDown cada uno (mismo patrón)

## Decisions Made

- Composición por MRO `(QMainWindow, WifiMixin, CameraMixin)`: CameraMixin se añade en el mismo orden que WifiMixin (después de QMainWindow) — las llamadas cruzadas desde métodos NO movidos (`wifi_mixin.py:345`, `self._drive_label`, `self._detect_camera_for_session`, `self._on_dialog_camera_name_changed`) resuelven por MRO sin tocar los call sites
- Namespace del singleton: los 16 métodos resuelven `db` desde `app.ui.mixins.camera_mixin` — el parche paralelo es obligatorio en todo setUp que reasigna `mw.db = self.db` y construye `MainWindow` (mismo mecanismo que `wifi_mixin_module.db` en quick 260906-ci2)
- `sd_reader` (3838) y `metadata_engine` (755/1441/3311) SIGUEN en uso en main_window → sus imports permanecen; solo `get_mounted_drives` queda huérfano

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Cobertura de parche] 18 setUps parcheados, no 15 como contaba el plan**
- **Found during:** Task 3 (grep de `mw.db = self.db` sobre los 5 ficheros)
- **Issue:** El plan estimaba 15 setUps a adaptar (12 en test_main_window + 1 en cada uno de los otros 4). El grep vivo encontró **14** en test_main_window (las clases en líneas 30, 105, 212, 273, 361, 462, 590, 741, 1037, 1142, 1197, 1242, 1338 y un setUp adicional que también reasigna `mw.db`) = 18 total; los bloques 673 (TestRenameCamera), 903 (TestFreeSpace), 915 (TestIntegrityReport), 975 (TestCardContentReport) no construyen MainWindow y siguen sin parche (correcto).
- **Fix:** Se parchearon los 18 setUps reales con el patrón completo (import + `_orig_cam_db` + `camera_mixin_module.db = self.db` + restauración). El criterio del plan («los tests reasignan camera_mixin_module.db = self.db en paralelo a mw.db = self.db») se cumplió mecánicamente sobre el fichero vivo, no sobre la estimación.
- **Files modified:** tests/test_main_window.py (14), tests/test_source_content.py, tests/test_e2e.py, tests/test_wifi_source.py, tests/test_session_content_modes.py (1 c/u)
- **Verification:** Chequeo estructural 18/18 (todo `mw.db = self.db` tiene su `camera_mixin_module.db = self.db` paralelo); 5 ficheros en aislamiento OK; suite completa sin fallas nuevas.
- **Committed in:** bc650bf (commit único del plan)

**2. [Rule 3 - Bloqueo de verificación] El run combinado de los 5 ficheros en un solo proceso unittest CRASHEA (0xC0000005) en Windows**
- **Found during:** Task 3 (verificación)
- **Issue:** `python -m unittest tests.test_main_window tests.test_source_content tests.test_e2e tests.test_wifi_source tests.test_session_content_modes -v` (un solo proceso) murió por access violation (EXIT=-1073741819) en mitad de TestWifiSource, sin FAIL/ERROR: crash nativo de Qt al convivir múltiples instancias QApplication/teardowns en un proceso.
- **Fix:** Se ejecutó la verificación como ordena el plan («en aislamiento», patrón 260906-epl): un proceso unittest por fichero. Los 5 pasan 100% (57/16/3/55/13 tests OK).
- **Files modified:** ninguno
- **Verification:** 5 runs aislados OK + suite pytest completa OK (el runner pytest no crasha y da el baseline exacto).
- **Committed in:** — (sin cambios; verificación, no código)

**3. [Nota] Exit code 0xC0000409 al terminar test_wifi_source en aislamiento (después de «Ran 55 tests OK»)**
- **Found during:** Task 3 (verificación)
- **Issue:** El proceso `python -m unittest tests.test_wifi_source` reporta 55 tests OK pero sale con EXIT=-1073740791 (crash de teardown Qt al cerrar el proceso).
- **Fix:** Ninguno — verificado en worktree temporal en HEAD sin cambios (0f4939e): mismo exit code idéntico. Pre-existente, ambiental (teardown Qt en Windows), no introducido por este refactor. Fuera de alcance (scope boundary).
- **Files modified:** ninguno
- **Verification:** Worktree base `fgl-base-check` en HEAD → `Ran 55 tests / OK` + EXIT=-1073740791 idéntico; eliminado después.
- **Committed in:** — (pre-existente)

---

**Total deviations:** 3 documentadas (1 cobertura de parche mayor que la estimada, 1 bloqueo de verificación resuelto por aislamiento, 1 crash de teardown pre-existente verificado en HEAD)
**Impact on plan:** Sin scope creep. La cobertura 18/18 es el cumplimiento exacto del criterio del plan (paralelismo mecánico); los dos crashes son ambientales de Windows/Qt y quedan documentados como Issues, no como defectos del refactor.

## Issues Encountered

- **Falla de suite pre-existente no relacionada:** `tests/test_mtp.py::TestThreadLocalManager::test_wpd_session_devicename_no_duplicate` falla SOLO en la ejecución completa de `pytest tests/ -q` (pasa en aislamiento). Mismo resultado exacto que el baseline documentado en 260906-epl: 1 failed / 393 passed / 5 skipped / 28 subtests. Falla dependiente del orden, en `app/core/mtp.py`, ajena a este refactor de `app/ui/`. Fuera de alcance; se registra aquí y no se repara.
- **Crash combinado unittest (Windows):** ejecutar los 5 ficheros de test en un solo proceso `python -m unittest` provoca access violation nativo (0xC0000005) en TestWifiSource. El patrón del plan y de 260906-epl es ejecutarlos aislados; el runner pytest aguanta los 5 juntos sin crash. No reproducible en pytest → ambiental.
- **Exit 0xC0000409 al final de test_wifi_source aislado:** crash de teardown Qt al cerrar el proceso, DESPUÉS de «Ran 55 tests OK». Verificado pre-existente en HEAD (worktree temporal) — no relacionado con la extracción.

## User Setup Required

None - refactor local de UI sin configuración externa, sin nuevas dependencias, sin strings de traducción nuevos (app/i18n/ intacto).

## Next Phase Readiness

- Bloque 3 del roadmap de reducción de MainWindow completado: dominio cámara/SD extraído siguiendo el patrón canónico WifiMixin (VERBATIM + MRO + singleton patch-eable por namespace)
- Listo para el siguiente bloque de reducción del god object (quedan ~3750 líneas)
- La falla MTP dependiente del orden y el crash de teardown Windows quedan registrados como deuda ambiental pre-existente para futuros bloques

---

*Quick: 260906-fgl*
*Completed: 2026-09-06*

## Self-Check: PASSED

- FOUND: app/ui/mixins/camera_mixin.py
- FOUND: app/ui/main_window.py (3750 líneas, 16 métodos fuera, composición CameraMixin)
- FOUND: tests/test_main_window.py (14 parches)
- FOUND: tests/test_source_content.py, tests/test_e2e.py, tests/test_wifi_source.py, tests/test_session_content_modes.py (1 parche c/u)
- FOUND: bc650bf refactor(ui): extraer deteccion/nombrado de camara y lectura SD de MainWindow a CameraMixin
- FOUND: .planning/quick/260906-fgl-bloque-3-extraer-la-deteccion-nombrado-d/260906-fgl-SUMMARY.md