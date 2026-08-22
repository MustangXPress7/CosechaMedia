# Roadmap: CosechaMedia — Auditoría UI y Plan de Reubicación

## Overview

Iniciativa de diagnóstico para CosechaMedia (aplicación de escritorio PySide6 para operadores de cámara). La interfaz actual concentra todos los flujos en un `MainWindow` de 3.870 líneas y una colección de diálogos con patrones propios, lo que genera zonas saturadas y opciones dispersas. Esta iniciativa entrega un mapa completo de la UI desde la perspectiva del operador de cámara: se auditan las cuatro zonas (ventana principal/dashboard, pickers de fuente, asistentes y paneles, acciones post-ingesta), se documenta un informe de hallazgos con evidencia en `.planning/` y se produce un plan de reubicación priorizado y acordado. **La iniciativa es exclusivamente diagnóstica: no se implementa ningún cambio de código** — la ejecución de las reubicaciones acordadas es una fase posterior (v2, UI-04/UI-05).

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Auditoría UI y Plan de Reubicación** - Auditoría de las cuatro zonas de la interfaz, informe de hallazgos con evidencia y plan de reubicación acordado (sin cambios de código)
- [ ] **Phase 2: Mejoras al volcado selectivo: multi-origen, escaneo MTP completo y opción todo** - INSERTED
- [ ] **Phase 3: Verificación avanzada: XXH64 + ASC MHL** - Política de hash configurable por proyecto (Rápida/Equilibrada/Máxima) y manifiestos ASC MHL encadenados por destino para custodia verificable en postproducción

## Phase Details

### Phase 1: Auditoría UI y Plan de Reubicación

**Goal**: El operador de cámara dispone de un diagnóstico completo de la interfaz actual —qué controles existen, dónde están, qué está mal ubicado y hacia dónde deberían moverse— materializado en un informe de hallazgos con evidencia por zona y en un plan de reubicación priorizado y acordado. No se modifica ningún código.
**Mode**: mvp
**Depends on**: Nothing (first phase)
**Requirements**: UI-01, UI-02, UI-03
**Success Criteria** (what must be TRUE):

  1. Las cuatro zonas — ventana principal/dashboard, pickers de fuente (MTP/FTP/WiFi), asistentes y paneles (SelectiveDump, ShootInbox, About, ProjectWizard) y acciones post-ingesta (formateo, proxies, reorganizar, apagado) — quedan auditadas y cada control relevante está documentado con su ubicación actual y el problema detectado (UI-01)
  2. Existe un informe de hallazgos por zona en `.planning/` donde cada hallazgo incluye evidencia: ubicación actual, problema detectado, propuesta de reubicación y justificación de usabilidad para el operador de cámara (UI-02)
  3. Existe un plan de reubicación priorizado por zona —con impacto estimado y orden de implementación— revisado y aprobado por el usuario (UI-03)
  4. No hay cambios de código: el árbol `app/` no presenta diffs y la suite de tests (`tests/`, Qt offscreen) pasa sin modificaciones

**Plans**: 4/4 plans executed
Plans:

- [x] 01-01-PLAN.md — Inventario de widgets por zona y capturas offscreen (evidencia, UI-01)
- [x] 01-02-PLAN.md — Informe de hallazgos 01-HALLAZGOS.md con anclas D-07..D-12 (UI-01, UI-02)
- [x] 01-03-PLAN.md — Plan de reubicación priorizado 01-PLAN-REUBICACION.md + gate de cero código (UI-03)
- [x] 01-04-PLAN.md — Revisión y aprobación del plan de reubicación por el operador (UI-03)

**UI hint**: yes

### Phase 2: Mejoras al volcado selectivo: multi-origen, escaneo MTP completo y opción todo

**Goal:** [To be planned]
**Requirements**: TBD
**Depends on:** Phase 1
**Plans:** 0 plans

Plans:

- [ ] TBD (run /gsd-plan-phase 2 to break down)

### Phase 3: Verificación avanzada: XXH64 + ASC MHL

**Goal:** El material volcado lleva custodia verificable estándar: cada volcado completado sella una generación ASC MHL nueva en `ascmhl/` de la raíz destino (cadena acumulativa por disco), con política de hash configurable por proyecto — Rápida (XXH64), Equilibrada (XXH64 + pasada MD5, default) o Máxima (MD5 + sidecars `.sha256` extra) — seleccionable tanto en el ProjectWizard como en el menú de configuración. Postproducción puede verificar los manifiestos con herramientas oficiales (`ascmhl verify`, `md5sum -c`).
**Mode:** standard
**Depends on:** Phase 2
**Requirements**: TBD (diseño acordado en `.planning/notes/diseno-xxh64-asc-mhl.md` — decisiones D1-D5)
**Success Criteria** (what must be TRUE):

  1. La política de hash es seleccionable en opciones avanzadas del ProjectWizard y en el menú de configuración de proyecto; proyectos existentes/nuevos sin preferencia usan Equilibrada
  2. `copy_verified` usa el árbitro del nivel elegido y conserva la semántica actual de borrado de destino corrupto; los hashes quedan persistidos en la DB (migración inline de `files`)
  3. Cada volcado completado añade una generación verificable a la cadena `ascmhl/` del destino usando el paquete oficial `ascmhl` (MIT); volcados sucesivos encadenan generaciones
  4. Los manifiestos/sidecars reflejan el nivel: Rápida = xxh64; Equilibrada = md5+xxh64 con segunda pasada sobre destino; Máxima = md5 + sidecars `.sha256` propios fuera del MHL
  5. Los informes CSV incluyen columnas de hashes y la suite de tests valida roundtrip contra la CLI oficial `ascmhl verify`

**Plans:** 0 plans

Plans:

- [ ] TBD (run /gsd-plan-phase 3 to break down)

## Progress

**Execution Order:**
Phases execute in numeric order: 1, 2, 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Auditoría UI y Plan de Reubicación | 4/4 | In Progress|  |
| 2. Mejoras al volcado selectivo | 0/0 | Planned |  |
| 3. Verificación avanzada: XXH64 + ASC MHL | 0/0 | Planned |  |
