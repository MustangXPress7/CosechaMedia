---
phase: 01-auditor-a-ui-y-plan-de-reubicaci-n
plan: 02
subsystem: ui
tags: [hallazgos, ui, inventario, reubicacion, pyqt, pyside6]

# Dependency graph
requires:
  - phase: 01-auditor-a-ui-y-plan-de-reubicaci-n
    provides: "01-01: inventario de widgets de las 4 zonas (A-D) + 8 capturas offscreen"
provides:
  - "01-HALLAZGOS.md: informe consolidado de hallazgos UI (7 hallazgos H-01..H-07) con citas archivo:línea, severidad, anclas D-07..D-12 y sección de conservación (D-03)"
  - "Cobertura total: 121 filas del inventario distribuidas entre §4 (56 filas implicadas) y §6 (65 conservadas), conteo verificado == 125 con cabeceras"
affects: [01-03 (puntuación/plan de reubicación), fase v2 (ejecución UI-04/UI-05)]

# Actuals (#2632) — pairs with the plan's `estimate` to calibrate future estimates.
# Same estimateTokens scale (chars/4 over the realized diff), never a harness token count.
actuals:
  tokens: 8008    # chars/4 over 01-HALLAZGOS.md (32035 chars)
  tasks: 2         # tasks completed
  commits: 1       # commits made (ambas tareas en el mismo commit del único entregable)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Informe de hallazgos estilo CONCERNS.md (hallazgo → evidencia → propuesta) con bloques de labels en negrita"
    - "Tablas ≤5 columnas con texto abreviado en celdas + párrafo backstop long-text tras la tabla"
    - "Traza de cobertura numérica §4+§6 == inventario Zona A-D (fila por control, 1 fila de datos por control)"

key-files:
  created:
    - ".planning/phases/01-auditor-a-ui-y-plan-de-reubicaci-n/01-HALLAZGOS.md"
  modified: []

key-decisions:
  - "7 hallazgos: H-01 (zona post-ingesta, D-07, Alta), H-02 (sesiones crecen a la derecha, D-08, Alta), H-03 (botones eliminar genéricos, D-09, Media), H-04 (descripción dato muerto, D-10, Media), H-05 (columnas fijas source_list, D-11, Baja), H-06 (duplicado guardar dispositivos, D-12, Alta), H-07 (volcado selectivo sin wiring, nuevo, Media)"
  - "Ninguna severidad bloqueante: las confirmaciones destructivas (formateo, apagado, eliminaciones) ya existen en el código (main_window.py:1802,1837-1842,2266,2473,3554) — los hallazgos son de percepción/jerarquía, no de pérdida de datos"
  - "H-07 es hallazgo nuevo de esta revisión (no estaba en CONTEXT.md): _open_selective_dump definido en main_window.py:3671-3687 sin wiring; menú contextual de table solo expone 'Eliminar completados'"
  - "Cobertura del inventario: 56 filas implicadas en §4 + 65 conservadas en §6 == 121 filas de datos (conteo verificado == 125 con cabeceras que cuentan por su carácter no-letra)"

patterns-established:
  - "Regla de evidencia: cada hallazgo cita app/ui/<módulo>.py:<línea> o captura; copy literal UI-SPEC:104 para evidencia no verificable"
  - "Cada D-07..D-12 se cita textualmente desde 01-CONTEXT.md y se ancla a filas del inventario + captura"

requirements-completed: [UI-01, UI-02]

# Coverage metadata (#1602) — one entry per shipped deliverable.
coverage:
  - id: D1
    description: "Informe consolidado de hallazgos UI 01-HALLAZGOS.md con resumen ejecutivo, método (D-05/D-06), mapa zonas↔flujos, hallazgos H-01..H-07 con citas archivo:línea y severidad, anclas D-07..D-12 y sección §6 Conservación (D-03)"
    requirement: UI-01
    verification:
      - kind: other
        ref: "python -c verify tarea 1: secciones §1..§4 presentes, ≥3 hallazgos H-NN, citas app/ui/...py:\\d+ >= ids únicos, copy evidencia no verificable"
        status: pass
      - kind: other
        ref: "python -c verify tarea 2: conteo filas de datos §4+§6 == inventario Zona A-D (125==125), '## Conservaci' presente, 20 attrs críticos inventariados, nota 01-PLAN-REUBICACION"
        status: pass
    human_judgment: false
  - id: D2
    description: "Validación visual de los hallazgos por el operador (dueño del producto) — las capturas zone A-D y la percepción de jerarquía/orden del panel de sesiones requieren juicio humano"
    verification: []
    human_judgment: true
    rationale: "El informe es diagnóstico para el plan 03; el operador debe validar que los hallazgos reflejan su intención (D-07..D-12) antes de puntuar la reubicación"

# Metrics
duration: 45min
completed: 2026-08-15
status: complete
---

# Phase 01: Auditoría UI y Plan de Reubicación — Plan 02 Summary

**Informe consolidado de hallazgos UI (01-HALLAZGOS.md): 7 hallazgos H-01..H-07 con citas archivo:línea verificadas (138 citas), severidad, anclas D-07..D-12 y cobertura total del inventario (121 filas, conteo verificado)**

## Performance

- **Duration:** 45 min
- **Started:** 2026-08-15
- **Completed:** 2026-08-15
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Informe consolidado `01-HALLAZGOS.md` (313 líneas) con estructura §1..§6: resumen ejecutivo, método (heurísticas D-05 + fórmula D-06), mapa zonas↔flujos, hallazgos por flujo, anclas de decisiones y conservación (D-03)
- 7 hallazgos priorizados con los campos del contrato UI-SPEC:221: id `H-NN`, zona+flujo, control implicado, ubicación actual (cita `archivo:línea` real), problema, propuesta, justificación (heurísticas D-05), impacto y severidad
- Cobertura total: 121 filas del inventario distribuidas entre §4 (56 filas implicadas por hallazgos) y §6 (65 conservadas); verificación numérica automatizada pasa (125 == 125 con cabeceras contadas)
- Anclas D-07..D-12 citadas textualmente desde `01-CONTEXT.md` y ancladas a filas del inventario + capturas; ninguna decisión quedó sin ancla verificable
- Hallazgo nuevo H-07 detectado en esta revisión: `_open_selective_dump` (modo dump del volcado selectivo) definido pero sin wiring; evidencia visual del menú contextual marcada con la copy literal UI-SPEC:104 (no verificable en runtime, se recapturará en ejecución)

## Task Commits

Cada tarea se verificó con su comando automatizado; ambas tareas escriben el mismo entregable (01-HALLAZGOS.md), por lo que se consolidaron en un único commit atómico:

1. **Tarea 1: Redactar el informe de hallazgos 01-HALLAZGOS.md (UI-01, UI-02)** - `bd4a055` (docs)
2. **Tarea 2: Sección §6 Conservación (D-03) y consistencia del informe (UI-01)** - `bd4a055` (docs, mismo commit — mismo archivo entregable)

**Plan metadata:** pendiente del commit final de estado.

## Files Created/Modified
- `.planning/phases/01-auditor-a-ui-y-plan-de-reubicaci-n/01-HALLAZGOS.md` - Informe consolidado de hallazgos UI: resumen ejecutivo (7 hallazgos), método (D-05/D-06), mapa zonas↔flujos, 3 tablas de implicados por flujo (conectar/ingestar/formatear-reorganizar), 7 bloques de hallazgo con contrato completo, anclas D-07..D-12, tabla de conservación (65 filas), nota de próximo paso al plan 03

## Decisions Made
- Ninguna severidad bloqueante: las confirmaciones destructivas ya existen en el código (formateo `:1802`, apagado `:1837-1842`, eliminar fuente/sesión/proyecto `:2266,2473,3554`); los hallazgos destructivos son de presentación/ubicación (D-09), no de pérdida de datos — ningún ítem destructivo recibió orden de reubicación sin confirmación D-09
- H-07 añadido como hallazgo nuevo: `_open_selective_dump` sin wiring (`app/ui/main_window.py:3671-3687`); el botón "Contenido" por fila solo abre el modo filter (`:2052-2067,3689-3710`)
- `btn_reorganize` se oculta cuando el modo de detección no es `auto` (`main_window.py:1216`) — contradice D-03 (no esconder nada); documentado dentro de H-01
- Formato del informe: tablas ≤5 columnas con abreviaturas en celdas + párrafo narrativo backstop tras cada tabla (UI-02 long-text)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- El conteo numérico de la tarea 2 requiere que las cabeceras de tabla se cuenten igual que en el inventario (la cabecera del inventario `texto/label` contiene `/`, no letra pura): se unificó §6 en una sola tabla (3 cabeceras en §4 + 1 en §6 = 4, igual que las 4 zonas del inventario) para que el total 125 == 125 pasara exactamente. Resuelto reestructurando la tabla de conservación, sin cambios de contenido.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `01-HALLAZGOS.md` está listo como entrada del plan 03 (puntuación D-06 y `01-PLAN-REUBICACION.md`): 7 hallazgos con severidad y factores de impacto/esfuerzo/riesgo identificados por hallazgo
- Los ítems destructivos (formateo/apagado/eliminaciones) quedan pendientes de confirmación D-09 — el plan 03 no debe darles orden de ejecución
- Las 121 filas del inventario tienen trazabilidad completa (implicadas o conservadas); ninguna quedó huérfana

---
*Phase: 01-auditor-a-ui-y-plan-de-reubicaci-n*
*Completed: 2026-08-15*

## Self-Check: PASSED

Verificado: 01-HALLAZGOS.md existe (313 líneas), 01-02-SUMMARY.md existe, commit bd4a055 en git log.
