---
phase: quick-260906-epl
plan: 01
subsystem: ui
tags: [pyside6, qdialog, refactor, main-window, god-object]

# Dependency graph
requires:
  - phase: quick-260906-ci2
    provides: WifiMixin extraction pattern (movimiento VERBATIM de métodos a módulos propios)
provides:
  - 4 diálogos de configuración extraídos de MainWindow a clases QDialog propias en app/ui/
  - 6 métodos de MainWindow convertidos en wrappers finos (~10 líneas c/u)
  - main_window.py reducido de 4589 a 4141 líneas (~448 netas)
affects: fases de refactor posteriores de MainWindow (god object), auditoría UI

actuals:
  tokens: 10428    # chars/4 sobre el diff realizado de los 5 ficheros
  tasks: 3
  commits: 1

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Diálogo QDialog propio en app/ui/ siguiendo AboutDialog: clase XDialog(QDialog), wrapper tr() -> QtString, singleton db a nivel de módulo (patch-eable), referencia al parent como self.window"

key-files:
  created:
    - app/ui/project_settings_dialog.py
    - app/ui/camera_overrides_dialog.py
    - app/ui/names_manager_dialog.py
    - app/ui/dump_locations_dialog.py
  modified:
    - app/ui/main_window.py

key-decisions:
  - "Los 4 diálogos viven en ficheros propios app/ui/*_dialog.py con el patrón AboutDialog (wrapper tr() -> QtString, db importado a nivel de módulo para patch.object futuro)"
  - "El estado de proyecto sigue viviendo en MainWindow: las clases acceden vía self.window.<attr> (14 referencias de estado documentadas)"
  - "Se eliminan 4 imports huérfanos de QtWidgets en main_window.py (QDateEdit, QGridLayout, QLineEdit, QListWidget) — el análisis previo del plan afirmaba que no quedarían huérfanos y era incorrecto"
  - "Los widgets capturados por closures originales pasan a atributos de la clase (table -> self.table en CameraOverridesDialog; listw -> self.listw en NamesManagerDialog y DumpLocationsDialog), única forma de convertir closures en métodos sin cambiar la lógica"

patterns-established:
  - "Extracción de diálogo inline a clase QDialog: constructor recibe `window` (o parent + callbacks), el cuerpo de construcción va en __init__ sin exec(), los wrappers de MainWindow ejecutan exec() y conservan los guards/persistencias que dependen del estado de MainWindow"
  - "Closures -> métodos privados: las variables locales que las closures antigua capturaban se convierten en atributos de instancia con el mismo nombre"

requirements-completed: [QUICK-260906-epl]

coverage:
  - id: D1
    description: "ProjectSettingsDialog — configuración general del proyecto (carpeta footage, organización, fechas, detección de cámara, proxies) con save SQL y defaults QSettings, copy VERBATIM de _show_metadata_dialog"
    requirement: QUICK-260906-epl
    verification:
      - kind: other
        ref: "python -m compileall -q app/ui/project_settings_dialog.py (pass)"
        status: pass
      - kind: other
        ref: "import offscreen: from app.ui.project_settings_dialog import ProjectSettingsDialog (pass)"
        status: pass
      - kind: other
        ref: "chequeo de equivalencia: conjunto de tr()/SQL/db.*/QSettings idéntico entre HEAD 726-880 y el módulo nuevo (pass)"
        status: pass
    human_judgment: false
  - id: D2
    description: "CameraOverridesDialog — fechas por cámara con merge de overrides existentes, copy VERBATIM de _show_camera_overrides_dialog (bloque 882-979); el persist SQL queda en el wrapper de MainWindow"
    requirement: QUICK-260906-epl
    verification:
      - kind: other
        ref: "python -m compileall -q app/ui/camera_overrides_dialog.py (pass)"
        status: pass
      - kind: other
        ref: "import offscreen: from app.ui.camera_overrides_dialog import CameraOverridesDialog (pass)"
        status: pass
      - kind: other
        ref: "chequeo de equivalencia: tr()/SQL/merge idénticos; solo cambia table -> self.table y self.project_* -> self.window.project_* (pass)"
        status: pass
    human_judgment: false
  - id: D3
    description: "NamesManagerDialog — gestión de nombres (footage/contenedores) con callbacks de db inyectados, copy VERBATIM de _show_names_manager (990-1096)"
    requirement: QUICK-260906-epl
    verification:
      - kind: other
        ref: "python -m compileall -q app/ui/names_manager_dialog.py (pass)"
        status: pass
      - kind: other
        ref: "import offscreen: from app.ui.names_manager_dialog import NamesManagerDialog (pass)"
        status: pass
      - kind: other
        ref: "chequeo de equivalencia: tr()/callbacks idénticos; QInputDialog/QMessageBox dialog -> self (pass)"
        status: pass
    human_judgment: false
  - id: D4
    description: "DumpLocationsDialog — destinos de volcado con add/del/reorder persistente, copy VERBATIM de _manage_dump_locations (1123-1209); el guard 'Sin proyecto' queda en el wrapper de MainWindow"
    requirement: QUICK-260906-epl
    verification:
      - kind: other
        ref: "python -m compileall -q app/ui/dump_locations_dialog.py (pass)"
        status: pass
      - kind: other
        ref: "import offscreen: from app.ui.dump_locations_dialog import DumpLocationsDialog (pass)"
        status: pass
      - kind: other
        ref: "chequeo de equivalencia: tr()/db.*/reorder idénticos; listw -> self.listw, self.current_project_id -> self.window.current_project_id (pass)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Wrappers finos de MainWindow — 5 métodos conservan nombre exacto y comportamiento (persist de overrides, guard de dump locations, refresh_file_types tras contenedores); _show_names_manager desaparece sin referencias"
    requirement: QUICK-260906-epl
    verification:
      - kind: other
        ref: "import offscreen: import app.ui.main_window (pass)"
        status: pass
      - kind: other
        ref: "python -m pytest tests/ -q — 393 passed, 5 skipped, 28 subtests; única falla tests/test_mtp.py::TestThreadLocalManager::test_wpd_session_devicename_no_duplicate, pre-existente e idéntica en HEAD (9cf857f) sin mis cambios (pass)"
        status: pass
      - kind: other
        ref: "git diff: solo movimiento + sustituciones documentadas; 0 huérfanos nuevos (pass)"
        status: pass
    human_judgment: false

# Metrics
duration: 45min
completed: 2026-09-06
status: complete
---

# Quick 260906-epl: Bloque 1 — Extraer los 4 diálogos de configuración de MainWindow

**Los 4 diálogos de configuración inline de MainWindow (configuración de proyecto, fechas por cámara, gestor de nombres footage/contenedores, destinos de volcado) pasan a clases QDialog propias en app/ui/*_dialog.py con lógica save/SQL/defaults/reorder byte-equivalente, y los 6 métodos de MainWindow quedan como wrappers finos — main_window.py baja de 4589 a 4141 líneas**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-09-06T10:45:02Z
- **Completed:** 2026-09-06T11:28:00Z
- **Tasks:** 3
- **Files modified:** 5 (4 creados + 1 modificado)

## Accomplishments

- `ProjectSettingsDialog` (app/ui/project_settings_dialog.py) — configuración general con save SQL `UPDATE projects` byte-equivalente, `db.add_footage_folder`, `QSettings` defaults y `_open_overrides_cb` conectado al wrapper de MainWindow
- `CameraOverridesDialog` (app/ui/camera_overrides_dialog.py) — tabla de cámaras activas con merge de overrides JSON; el persist SQL tras `exec()` se queda en el wrapper
- `NamesManagerDialog` (app/ui/names_manager_dialog.py) — getter + 4 callbacks de `db` inyectados; search filter, add/dup/ren/del con `QInputDialog`/`QMessageBox` sobre `self`
- `DumpLocationsDialog` (app/ui/dump_locations_dialog.py) — add/del/reorder de destinos persistente con las 4 llamadas `db.dump_locations/add/delete/reorder` byte-equivalentes
- 6 métodos de `MainWindow` → wrappers finos (5 conservan nombre exacto; `_show_names_manager` desaparece sin referencias); toolbar (`"_show_metadata_dialog"`) y menús intactos
- Suite completa: 393 passed / 5 skipped / 28 subtests — única falla pre-existente no relacionada (ver Issues)
- Verificación cruzada programática: conjuntos de strings `tr()`, SQL, llamadas `db.*` y claves `QSettings` idénticos entre el cuerpo original de HEAD y los módulos nuevos (cero strings nuevos/perdidos, cero SQL alterados)

## Task Commits

Commit único tras las 3 tareas, según la sección Output del plan:

1. **T1 + T2 + T3: extracción de los 4 diálogos + wrappers** - `8ffb70c` (refactor)

**Plan metadata:** commits docs gestionados por el orquestador (no incluidos aquí).

## Files Created/Modified

- `app/ui/project_settings_dialog.py` - `ProjectSettingsDialog(QDialog)`: grupos Configuración general / Detección de cámara / Proxies, `_save` (SQL + `db.add_footage_folder` + `self.window._refresh_source_list`), `_set_defaults` (QSettings + `self.window.ingest_status_label`), `_open_overrides`
- `app/ui/camera_overrides_dialog.py` - `CameraOverridesDialog(QDialog)`: tabla de cámaras activas (SELECT sesiones activas), filas con modo/fecha, `_save` con merge de overrides no visibles + `self.accept()`
- `app/ui/names_manager_dialog.py` - `NamesManagerDialog(QDialog)`: constructor `(parent, title, getter, add_cb, rename_cb, delete_cb, duplicate_cb)`, `_names_manager` como atributo, métodos `_refresh/_on_search/_selected/_add/_dup/_ren/_del`
- `app/ui/dump_locations_dialog.py` - `DumpLocationsDialog(QDialog)`: `_refresh/_add/_del/_move(delta)` con reorder persistente, `__init__` termina con `self._refresh()`
- `app/ui/main_window.py` - los 6 métodos pasan a wrappers finos; `_show_names_manager` eliminado; +4 imports de diálogos, −4 imports huérfanos (QDateEdit, QGridLayout, QLineEdit, QListWidget)

## Decisions Made

- Método de extracción VERBATIM con sustituciones mecánicas (`self.` → `self.window.` solo para las 14 referencias de estado de proyecto; closures → métodos privados; `dialog.reject/accept` → `self.reject/accept`), siguiendo el patrón documentado de `AboutDialog`/`WifiMixin`
- Los widgets capturados por closures originales se convierten en atributos de la instancia (`table` → `self.table`, `listw` → `self.listw`) — única forma de convertir las closures en métodos sin alterar la lógica
- Eliminación de los 4 imports huérfanos recién creados por la extracción (el análisis previo del plan los daba por usados; la comprobación viva demostró lo contrario)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug en el análisis previo del plan] 4 imports huérfanos en main_window.py**
- **Found during:** Task 3 (verificación de imports tras la extracción)
- **Issue:** El plan afirmaba «verificado: ningún símbolo queda huérfano tras la extracción» (línea 58) y su criterio de aceptación exige «Ningún import roto ni huérfano». Tras eliminar los 6 cuerpos, `QDateEdit`, `QGridLayout`, `QLineEdit` y `QListWidget` tenían 0 usos restantes fuera del bloque de imports (comprobación con regex sobre el fichero vivo).
- **Fix:** Se eliminaron exactamente esos 4 símbolos del bloque `from PySide6.QtWidgets import (...)` de main_window.py (líneas 6-12), dejando intactos los 12 huérfanos pre-existentes (QFont, QFrame, QListWidgetItem, QMenuBar, QObject, QPixmap, QPropertyAnimation, QSize, QSplashScreen, QStackedWidget, QSystemTrayIcon, QTextEdit — ya huérfanos en HEAD, fuera de alcance).
- **Files modified:** app/ui/main_window.py
- **Verification:** Script de comparación HEAD vs. actual: 0 huérfanos nuevos introducidos; import offscreen OK; suite completa sin fallas nuevas.
- **Committed in:** 8ffb70c (commit único del plan)

**2. [Nota de sustitución mecánica — attributes de widgets] `table` y `listw` pasan a atributos**
- **Found during:** Tasks 1-2 (conversión closure → método)
- **Issue:** Al convertir las closures `save()`/`refresh()`/`_del()`/`_move()` en métodos privados, las variables locales `table` (CameraOverridesDialog) y `listw` (NamesManagerDialog, DumpLocationsDialog) dejan de ser alcanzables por closure.
- **Fix:** Mismo mecanismo que el plan documenta para `self._names_manager` (atributo de instancia con el mismo nombre): `table` → `self.table`, `listw` → `self.listw`. Sin cambio de lógica.
- **Files modified:** app/ui/camera_overrides_dialog.py, app/ui/names_manager_dialog.py, app/ui/dump_locations_dialog.py
- **Verification:** compileall + import offscreen + chequeo de equivalencia programático (tr()/SQL/db.*/QSettings) idénticos.
- **Committed in:** 8ffb70c (commit único del plan)

---

**Total deviations:** 2 auto-fixed (1 bug de análisis previo, 1 sustitución mecánica necesaria)
**Impact on plan:** Sin scope creep. La eliminación de imports era necesaria para cumplir el criterio de aceptación propio del plan («ni huérfano»); la atribución de widgets es la vía mínima para la conversión closure→método que el propio plan ordena.

## Issues Encountered

- **Falla de suite pre-existente no relacionada:** `tests/test_mtp.py::TestThreadLocalManager::test_wpd_session_devicename_no_duplicate` falla SOLO en la ejecución completa de `pytest tests/ -q` (pasa en aislamiento). Verificado con worktree temporal en HEAD sin cambios (9cf857f): mismo resultado exacto — 1 failed / 393 passed / 5 skipped / 28 subtests. Falla dependiente del orden, en `app/core/mtp.py`, ajena a este refactor de `app/ui/`. Fuera de alcance (scope boundary); se registra aquí y no se repara.
- Nota de equivalencia: los strings `tr()` de los wrappers de MainWindow («Personalizar carpeta de footage», «Personalizar contenedores de archivos», «Sin proyecto», «Selecciona un proyecto primero.») no están en los módulos nuevos porque el plan los deja en los wrappers — verificado que siguen presentes en main_window.py.

## User Setup Required

None - refactor local de UI sin configuración externa, sin nuevas dependencias, sin strings de traducción nuevos (app/i18n/ intacto).

## Next Phase Readiness

- Bloque 1 del roadmap de reducción de MainWindow completado: 4 dominios autónomos extraídos siguiendo el patrón canónico de diálogo (`XDialog(QDialog)` + `tr()` wrapper + `db` singleton a nivel de módulo, patch-eable como `test_add_source_dialog.py`)
- Listo para el siguiente bloque de reducción del god object (quedan ~4141 líneas); los 12 imports huérfanos pre-existentes son candidatos de limpieza en un bloque futuro
- La falla MTP dependiente del orden queda registrada como deuda pre-existente para un futuro fix de aislamiento de tests

---
*Quick: 260906-epl*
*Completed: 2026-09-06*

## Self-Check: PASSED

- FOUND: app/ui/project_settings_dialog.py
- FOUND: app/ui/camera_overrides_dialog.py
- FOUND: app/ui/names_manager_dialog.py
- FOUND: app/ui/dump_locations_dialog.py
- FOUND: .planning/quick/260906-epl-bloque-1-extraer-los-4-di-logos-de-confi/260906-epl-SUMMARY.md
- FOUND: 8ffb70c refactor(ui): extraer los 4 diálogos de configuración de MainWindow a app/ui/