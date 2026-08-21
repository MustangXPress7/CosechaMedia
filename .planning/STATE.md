---
gsd_state_version: 1.0
milestone: v1.5
milestone_name: Consolidación y bugs
current_phase: 00
current_phase_name: Bugs conocidos + features v1.5
status: active
stopped_at: None
last_updated: "2026-08-21T10:33:06.173Z"
last_activity: 2026-08-21
last_activity_desc: "Quick 260821-f2k completado — volcado selectivo por sesión (I-15+I-18): switch cíclico de 3 modos por sesión, ventana N días real desde último volcado, tabla Opciones 3 columnas, botón global retirado."
progress:
  total_phases: 2
  completed_phases: 0
  total_plans: 5
  completed_plans: 4
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-15)

**Core value:** Que el operador de cámara pueda vaciar tarjetas SD/cámaras/móviles al archivo del proyecto de forma fiable y sin perder datos — cada archivo copiado con verificación de integridad y organizado correctamente.
**Current focus:** v1.5 — Consolidación de bugs + features pendientes (excepto modo guiado, reservado para v2.0)

## Objective: v1.5

**Alcance de v1.5 (todo excepto I-01 "acciones rápidas/modo guiado"):**

### Bugs conocidos (CONCERNS.md)

- FFprobe timeout → metadata "Unknown" + file_size=0
- Watcher re-ingesta tras pruning >10k archivos
- DB path depende de CWD cuando no está frozen
- Doble hash MD5 por copia (rendimiento)
- Device polling en UI thread (freezes)

### Features pendientes (IDEAS.md → v1.5)

- I-03: Cámara ↔ ID de tarjeta persistida
- I-06: Reporte CSV de contenido de tarjeta ✅
- I-07: WiFi reanudar subidas + MD5 en móvil — Por revisar
- I-11: Crear proyecto en un solo paso ✅
- I-12: Fix "establecer como predeterminado" ✅
- I-14: Forzar nombre de cámara al registrar origen ✅
- I-15: Interruptor de contenido en volcado selectivo ✅ — quick 260821-f2k
- I-18: Filtrado de volcado por sesión ✅ — quick 260821-f2k
- I-19: Revisar temas claro/oscuro ✅
- Fase 2: Volcado selectivo multi-origen, escaneo MTP vía caché, opción "todo"

### Estética (BACKLOG_UI_V2 → v1.5)

- B-09: Tipografía con jerarquía
- B-10: Espaciado y superficies
- B-11: Microinteracciones y botón primario
- B-12: Auditoría estética formal

### Reservado para v2.0

- I-01: Acciones rápidas / modo guiado
- I-13: Pantalla de bienvenida (ligada a I-01)

## Current Position

Phase: 00 (Bugs + features v1.5) — STARTING
Status: Investigando bugs conocidos de CONCERNS.md
Last activity: 2026-08-21 - Volcado por sesión (I-15+I-18): ventana por defecto 1 día + spinboxes estilizados en ambos temas (e97edc8)

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
- [Fase 2]: Volcado selectivo multi-origen (global = todos los orígenes; per-device = uno a uno), escaneo MTP completo vía caché para ordenar por fecha sin volcar, y opción "todo" para revertir la selección
- [Priorización]: Convención de prioridades de uso — cambios críticos de usabilidad = "uso"; funcionalidad nueva = "nuevo feature" (no feature-request genérico)

### Roadmap Evolution

- Phase 2 added: Mejoras al volcado selectivo: multi-origen, escaneo MTP completo y opción todo

### Pending Todos

- Investigar y fixear bugs conocidos de CONCERNS.md (FFprobe timeout, watcher re-ingesta, DB path CWD, doble MD5, device polling UI thread)
- Features v1.5: I-03, I-06, I-07, I-11, I-14, Fase 2
- Estética v1.5: B-09, B-10, B-11, B-12

### Blockers/Concerns

- [Core]: `main_window.py` (~4100 líneas) — god object, bugs conocidos documentados en CONCERNS.md
- [Core]: Sin framework de logging — solo `print()` en 16 sitios
- [Core]: Migraciones DB inline sin versión — riesgo en upgrades

### Quick Tasks Completed

| # | Description | Date | Commit | Status | Directory |
|---|-------------|------|--------|--------|-----------|
| 260816-jlt | Convertir SourcePickerDialog en lanzador compacto (inversión parcial D-12) | 2026-08-16 | 572cd26 | Needs Review | [260816-jlt-convertir-sourcepickerdialog-en-lanzador](./quick/260816-jlt-convertir-sourcepickerdialog-en-lanzador/) |
| 260816-k7i | Corregir hallazgos pendientes del UI-REVIEW (ProjectWizard, confirmaciones destructivas, zombie buttons, menú redundante) | 2026-08-16 | 7aa7f98 | Verified (gap fix 5d970b3) | [260816-k7i-corregir-hallazgos-pendientes-del-ui-rev](./quick/260816-k7i-corregir-hallazgos-pendientes-del-ui-rev/) |
| 260816-mcj | Arreglar MTP (manager COM por hilo), volcado selectivo a orígenes, columnas de borrado por fila y columna de ruta redimensionable | 2026-08-16 | 7b27666 | Verified | [260816-mcj-arreglar-mtp-manager-com-por-hilo-y-reub](./quick/260816-mcj-arreglar-mtp-manager-com-por-hilo-y-reub/) |
| 260816-x3b | Reemplazar glifos emoji por iconos SVG vectoriales tintables (app/ui/icons.py + 13 SVGs, hook refresh_all en tema/acento, .ts sincronizado) | 2026-08-16 | b28b808 | Needs Review | [260816-x3b-reemplazar-los-glifos-emoji-unicode-que-](./quick/260816-x3b-reemplazar-los-glifos-emoji-unicode-que-/) |
| 260821-f2k | Volcado selectivo por sesión (I-15+I-18): control por sesión en área Sesiones, ventana N días real desde último volcado, tabla Opciones 3 columnas, botón global retirado | 2026-08-21 | 8ff5121 | Verified | [260821-f2k-volcado-selectivo-por-sesion-i-15-i-18-s](./quick/260821-f2k-volcado-selectivo-por-sesion-i-15-i-18-s/) |
| 260821-f2k-rev | Revisión UX tras feedback: rotativo solo-icono del modo (cuadrado/calendario/cronómetro, cicla sin diálogos) + botón de configuración con texto legible que abre el menú del modo; 3 SVGs nuevos tintables | 2026-08-21 | 1e332ca | Verified | [260821-f2k-volcado-selectivo-por-sesion-i-15-i-18-s](./quick/260821-f2k-volcado-selectivo-por-sesion-i-15-i-18-s/) |
| 260821-f2k-rev2 | Ventana de volcado por defecto a 1 día (ingestor, UI y asistente) + QSS estandarizado para QSpinBox/QDoubleSpinBox/QTimeEdit con paleta del tema (antes nativo claro ilegible en oscuro) | 2026-08-21 | e97edc8 | Verified | [260821-f2k-volcado-selectivo-por-sesion-i-15-i-18-s](./quick/260821-f2k-volcado-selectivo-por-sesion-i-15-i-18-s/) |
| 260821-io6 | Lote de pulido UI: wizard con opciones avanzadas colapsables, WiFi directo al QR (sin diálogo intermedio), orden de botones del lanzador, progreso sin texto hasta finalizar, combo de sesiones elástico, icono llave inglesa, anchos de orígenes (Ruta stretch), flechas de combo triángulo, primarios dependientes del acento + todo el azul por defecto (bordes hover/focus, selecciones, barra de proyecto) sigue al acento | 2026-08-21 | 3b699d7 | Needs Review | [260821-io6-ui-polish-batch-wizard-advanced-toggle-d](./quick/260821-io6-ui-polish-batch-wizard-advanced-toggle-d/) |

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Implementación de reubicaciones | UI-04/UI-05 (v2) | Pending | 2026-08-15 |
| Refactor core | MainWindow god object, logging, migraciones | Out of scope | 2026-08-15 |

## Session Continuity

Last session: 2026-08-16T13:21:06.313Z
Stopped at: Completed 260816-k7i-PLAN.md (quick)
Resume file: None
