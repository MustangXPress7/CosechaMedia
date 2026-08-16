---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: 01
current_phase_name: Auditoría UI y Plan de Reubicación
status: complete
stopped_at: Completed 260816-mcj-PLAN.md (quick)
last_updated: "2026-08-16T14:05:26.575Z"
last_activity: 2026-08-16
last_activity_desc: Quick task 260816-mcj completado y verificado — fix MTP (manager COM por hilo), volcado selectivo a la fila de orígenes, columnas de borrado por fila en ambas tablas y columna de ruta redimensionable.
progress:
  total_phases: 1
  completed_phases: 0
  total_plans: 5
  completed_plans: 4
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-15)

**Core value:** Que el operador de cámara pueda vaciar tarjetas SD/cámaras/móviles al archivo del proyecto de forma fiable y sin perder datos — cada archivo copiado con verificación de integridad y organizado correctamente.
**Current focus:** Phase 01 — Auditoría UI y Plan de Reubicación

## Current Position

Phase: 01 (Auditoría UI y Plan de Reubicación) — EXECUTING
Plan: 1 of 4
Status: Executing Phase 01
Last activity: 2026-08-16 - Completed quick task 260816-mcj: fix MTP (manager COM por hilo), volcado selectivo a la fila de orígenes, columnas de borrado por fila en ambas tablas, columna de ruta redimensionable

Progress: [████████░░] 80%

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: —
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Auditoría UI y Plan de Reubicación | TBD | 0 | — |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 260816-k7i-corregir-hallazgos-pendientes-del-ui-rev P1 | 0h | 3 tasks | 4 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Iniciativa]: Auditoría primero, implementación después — el roadmap v1 es 100% diagnóstico (sin cambios de código)
- [Iniciativa]: Alcance = diagnóstico + plan por zona; la implementación (UI-04/UI-05) se difiere a v2 por decisión explícita del usuario
- [Iniciativa]: Todas las zonas de la UI con igual prioridad — el operador usa la app de extremo a extremo
- [Phase ?]: Quick k7i: ProjectWizard reactivado como única vía de creación de proyecto (600x520, callbacks on_finished/on_cancel)
- [Phase ?]: Quick k7i: gestión de dispositivos guardados migrada a Añadir origen — rol ('device', id) + menú contextual Eliminar guardado; menú Ingesta depurado sin código zombie

### Pending Todos

None yet.

### Blockers/Concerns

- [Roadmap]: Implementación de reubicaciones fuera de alcance del milestone (decisión explícita) — la fase posterior deberá partir del plan UI-03
- [Contexto]: `main_window.py` (3.870 líneas) sin tests y con bugs conocidos (carrera `_cam_done`, rename con `/`) — documentados en CONCERNS.md, fuera del alcance de esta iniciativa

### Quick Tasks Completed

| # | Description | Date | Commit | Status | Directory |
|---|-------------|------|--------|--------|-----------|
| 260816-jlt | Convertir SourcePickerDialog en lanzador compacto (inversión parcial D-12) | 2026-08-16 | 572cd26 | Needs Review | [260816-jlt-convertir-sourcepickerdialog-en-lanzador](./quick/260816-jlt-convertir-sourcepickerdialog-en-lanzador/) |
| 260816-k7i | Corregir hallazgos pendientes del UI-REVIEW (ProjectWizard, confirmaciones destructivas, zombie buttons, menú redundante) | 2026-08-16 | 7aa7f98 | Verified (gap fix 5d970b3) | [260816-k7i-corregir-hallazgos-pendientes-del-ui-rev](./quick/260816-k7i-corregir-hallazgos-pendientes-del-ui-rev/) |
| 260816-mcj | Arreglar MTP (manager COM por hilo), volcado selectivo a orígenes, columnas de borrado por fila y columna de ruta redimensionable | 2026-08-16 | 7b27666 | Verified | [260816-mcj-arreglar-mtp-manager-com-por-hilo-y-reub](./quick/260816-mcj-arreglar-mtp-manager-com-por-hilo-y-reub/) |

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Implementación de reubicaciones | UI-04/UI-05 (v2) | Pending | 2026-08-15 |
| Refactor core | MainWindow god object, logging, migraciones | Out of scope | 2026-08-15 |

## Session Continuity

Last session: 2026-08-16T13:21:06.313Z
Stopped at: Completed 260816-k7i-PLAN.md (quick)
Resume file: None
