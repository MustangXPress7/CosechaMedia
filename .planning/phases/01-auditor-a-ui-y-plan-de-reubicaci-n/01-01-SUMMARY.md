---
phase: 01-auditor-a-ui-y-plan-de-reubicaci-n
plan: 01
subsystem: ui
tags: [pyqt, pyside6, inventario-widgets, auditoria-ui, capturas-offscreen]

# Dependency graph
requires: []
provides:
  - "Inventario completo de widgets de las 4 zonas de la UI (A dashboard, B pickers, C asistentes/paneles, D post-ingesta) con citas archivo:línea reales"
  - "8 capturas offscreen de la UI (estado-inicial y configurado por zona) en captures/"
  - "Harness de captura reutilizable (capture_ui.py) con BD temporal y salida limpia"
  - "Baseline git de archivos modificados pre-existentes (A-BASELINE) para las fases de ejecución UI posteriores"
affects: [01-02, 01-03, 01-04, verificación de la auditoría UI]

# Actuals (#2632) — pairs with the plan's estimate (30000 tokens) on the same
# estimateTokens scale (chars/4 over the realized text diff, PNGs binarios excluidos).
actuals:
  tokens: 7750
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Harness offscreen QT_QPA_PLATFORM=offscreen con una sola QApplication y BD temporal (patrón de tests/test_e2e.py) para capturar escenas sin pantalla"
    - "Leyenda de capturas en el inventario mapeando cada PNG a zona, escena, estado y widgets fuente"

key-files:
  created:
    - ".planning/phases/01-auditor-a-ui-y-plan-de-reubicaci-n/01-INVENTARIO.md"
    - ".planning/phases/01-auditor-a-ui-y-plan-de-reubicaci-n/capture_ui.py"
    - ".planning/phases/01-auditor-a-ui-y-plan-de-reubicaci-n/captures/zona{A..D}_{estado-inicial,configurado}.png"
    - ".planning/phases/01-auditor-a-ui-y-plan-de-reubicaci-n/baseline_git.txt"
  modified: []

key-decisions:
  - "Inventario por zona con tablas de máx. 5 columnas (ID, attr, tipo Qt, texto/label, ubicación) para respetar la regla anti-desbordamiento de 01-UI-SPEC"
  - "El volcado selectivo solo alcanzable desde el botón 'Contenido' por fila (modo filter); _open_selective_dump (modo dump) no tiene wiring directo — documentado como D-07/D-08 en el inventario"
  - "Capturas offscreen como evidencia visual del estado inicial vs. configurado; cualquier escena no renderizable se registra como 'captura pendiente — motivo' en la leyenda sin abortar el harness"

patterns-established:
  - "Cada control del inventario cita su ubicación real con formato app/ui/<módulo>.py:<línea> y usa los atributos públicos con los que lo nombran los tests (btn_start, table, source_list)"
  - "Anclas de hallazgos confirmados (D-07..D-12 de 01-CONTEXT.md) mapeadas a filas concretas del inventario para trazabilidad"

requirements-completed: [UI-01]

coverage:
  - id: D1
    description: "Inventario de widgets de la UI (01-INVENTARIO.md) cubriendo las zonas A (dashboard), B (pickers de fuente), C (asistentes y paneles) y D (acciones post-ingesta), cada control con attr, tipo Qt, texto/label y ubicación archivo:línea"
    requirement: "UI-01"
    verification:
      - kind: other
        ref: "python -c: verificación automatizada de secciones, 21 attrs obligatorios, anclas D-07..D-12 y 123 citas app/ui/[a-z_]+.py:\d+ (>=30 requeridas)"
        status: pass
    human_judgment: true
    rationale: "La calidad de un inventario de UI se juzga comparando las citas con el código real y la representatividad de los controles; la inspección humana del documento completo es necesaria"
  - id: D2
    description: "8 capturas offscreen de la UI (captures/zona{A..D}_{estado-inicial,configurado}.png) ≤1920px de ancho, generadas por capture_ui.py, con leyenda en el inventario"
    requirement: "UI-01"
    verification:
      - kind: other
        ref: "python -c: verificación automatizada de existencia de los 8 PNG, ancho <=1920px y citas en la leyenda (RESULT: PASS)"
        status: pass
    human_judgment: true
    rationale: "La evidencia visual (layouts, estados, placeholders) requiere revisión humana para confirmar que las capturas reflejan fielmente la UI real"
  - id: D3
    description: "Baseline git (baseline_git.txt) de archivos modificados pre-existentes en app/ tests/ tools/, incluyendo las 4 rutas A-BASELINE"
    requirement: "UI-01"
    verification:
      - kind: other
        ref: "git status --porcelain app/ tests/ tools/ → 4 rutas extraídas coinciden con app/ui/main_window.py, app/i18n/cosechamedia_en.ts, app/i18n/cosechamedia_en.qm, tools/translate_en.py"
        status: pass
    human_judgment: false

# Metrics
duration: 25min
completed: 2026-08-15
status: complete
---

# Phase 01 - Plan 01: Auditoría UI — Inventario de Widgets y Capturas Summary

**Inventario de widgets de las 4 zonas de la UI (A dashboard, B pickers, C asistentes/paneles, D post-ingesta) con 121 filas de controles citados archivo:línea, más 8 capturas offscreen de evidencia visual y el baseline git de los archivos pre-modificados**

## Performance

- **Duration:** 25 min
- **Started:** 2026-08-15T00:00:00Z
- **Completed:** 2026-08-15T00:25:00Z
- **Tasks:** 2
- **Files modified:** 14 (11 en Task 2 + 3 en Task 1)

## Accomplishments
- `01-INVENTARIO.md`: 121 filas de controles organizadas en Zona A (43), Zona B (32), Zona C (38) y Zona D (8), cada una con ID, attr público, tipo Qt, texto/label y ubicación `app/ui/<módulo>.py:<línea>`; 123 citas verificadas (≥30 requeridas)
- Anclas D-07..D-12 de 01-CONTEXT.md mapeadas a filas concretas del inventario (trazabilidad de hallazgos confirmados)
- 8 capturas offscreen generadas por `capture_ui.py` (1200x780 dashboard, 460x312 picker, 640x560 wizard, 677x120 zona D), todas ≤1920px de ancho, con `## Leyenda de capturas` en el inventario
- `baseline_git.txt`: las 4 rutas A-BASELINE pre-modificadas (`app/ui/main_window.py`, `app/i18n/cosechamedia_en.{ts,qm}`, `tools/translate_en.py`) capturadas para la comprobación de la fase 03
- Hallazgo clave documentado: el volcado selectivo solo se alcanza desde el botón "Contenido" por fila (modo filter); `_open_selective_dump` (modo dump) está sin wiring — evidencia directa para los planes de reubicación (01-02/01-03)

## Task Commits

Each task was committed atomically:

1. **Task 1: Inventario de widgets (`01-INVENTARIO.md`)** - `e59f38c` (docs)
2. **Task 2: Capturas offscreen + baseline + leyenda** - `dacf9bf` (test)

**Plan metadata:** `e59f38c` (docs(01-01): create widget inventory for the 4 UI zones) + `dacf9bf` (test(01-01): add offscreen capture harness and zone screenshots)

_Nota: los commits de tarea son los únicos commits de este plan; el commit de metadatos del plan lo gestiona el orquestador (commit_docs: true)._

## Files Created/Modified
- `.planning/phases/01-auditor-a-ui-y-plan-de-reubicaci-n/01-INVENTARIO.md` - Inventario de widgets por zonas (Tarea 1) + `## Leyenda de capturas` (Tarea 2)
- `.planning/phases/01-auditor-a-ui-y-plan-de-reubicaci-n/capture_ui.py` - Harness offscreen: QApplication única, QT_QPA_PLATFORM=offscreen, BD temporal (patrón test_e2e), tema aplicado, salida limpia exit 0; escenas no renderizables se registran como "captura pendiente"
- `.planning/phases/01-auditor-a-ui-y-plan-de-reubicaci-n/captures/zonaA_estado-inicial.png`, `zonaA_configurado.png` - MainWindow completa, sin proyecto / con proyecto+sesión+progreso+tabla
- `.planning/phases/01-auditor-a-ui-y-plan-de-reubicaci-n/captures/zonaB_estado-inicial.png`, `zonaB_configurado.png` - SourcePickerDialog vacío / con carpetas, remitentes WiFi y perfil FTP
- `.planning/phases/01-auditor-a-ui-y-plan-de-reubicaci-n/captures/zonaC_estado-inicial.png`, `zonaC_configurado.png` - ProjectWizard vacío / formulario lleno
- `.planning/phases/01-auditor-a-ui-y-plan-de-reubicaci-n/captures/zonaD_estado-inicial.png`, `zonaD_configurado.png` - Zona post-ingesta (recorte columna izquierda) sin / con configuraciones activas
- `.planning/phases/01-auditor-a-ui-y-plan-de-reubicaci-n/baseline_git.txt` - Paths de `git status --porcelain app/ tests/ tools/` (segundo token por línea)

## Decisions Made
- Inventario con tablas de máx. 5 columnas (regla anti-desbordamiento de 01-UI-SPEC) en lugar de una estructura más ancha
- Volcado selectivo documentado como alcanzable únicamente por el botón "Contenido" por fila (modo filter); `_open_selective_dump` sin wiring registrado como D-07/D-08 (hallazgo, no defecto del plan)
- Capturas offscreen como evidencia visual; fallo de renderizado → registro "captura pendiente — motivo" en la leyenda (nunca abortar el harness)
- Todos los nombres de atributos usan los identificadores públicos con los que los nombran los tests (`btn_start`, `table`, `source_list`, etc.)

## Deviations from Plan

None - plan executed exactly as written.

**Total deviations:** 0
**Impact on plan:** N/A

## Issues Encountered
- `rg` no está disponible en el shell (PowerShell) — se usaron las herramientas Grep/Glob/Select-String para la verificación de citas; sin impacto en el resultado
- El modelo actual no soporta entrada de imágenes, por lo que las capturas se validaron programáticamente (dimensiones del header PNG y tamaño de archivo >2KB para descartar renders en blanco) en lugar de inspección visual directa; la revisión visual humana queda cubierta por la verificación de la fase
- `git status --porcelain` en PowerShell: el segundo token tras dividir por espacios era el código de estado; se corrigió con `.Trim()` antes de dividir para extraer el PATH correcto en `baseline_git.txt`

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- El inventario (01-02/01-03: propuesta de reubicación) tiene todos los controles de las 4 zonas citados y anclados a los hallazgos D-07..D-12
- Las capturas offscreen sirven de evidencia visual compartida para los planes de reubicación y para la verificación de la fase
- `baseline_git.txt` registra el estado pre-existente de los 4 archivos modificados en `app/`/`tools/`; la fase 03 puede comparar contra este baseline al finalizar su trabajo
- Sin bloqueadores ni pendientes conocidos para las fases siguientes

## Self-Check: PASSED

- `01-INVENTARIO.md`, `01-01-SUMMARY.md`, `capture_ui.py`, `baseline_git.txt` y las 8 capturas `zona{A..D}_{estado-inicial,configurado}.png` existen en disco
- Commits `e59f38c` (Tarea 1) y `dacf9bf` (Tarea 2) confirmados en `git log`

---
*Phase: 01-auditor-a-ui-y-plan-de-reubicaci-n*
*Completed: 2026-08-15*
