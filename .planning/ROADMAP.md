# Roadmap: CosechaMedia — Auditoría UI y Plan de Reubicación

## Overview

Iniciativa de diagnóstico para CosechaMedia (aplicación de escritorio PySide6 para operadores de cámara). La interfaz actual concentra todos los flujos en un `MainWindow` de 3.870 líneas y una colección de diálogos con patrones propios, lo que genera zonas saturadas y opciones dispersas. Esta iniciativa entrega un mapa completo de la UI desde la perspectiva del operador de cámara: se auditan las cuatro zonas (ventana principal/dashboard, pickers de fuente, asistentes y paneles, acciones post-ingesta), se documenta un informe de hallazgos con evidencia en `.planning/` y se produce un plan de reubicación priorizado y acordado. **La iniciativa es exclusivamente diagnóstica: no se implementa ningún cambio de código** — la ejecución de las reubicaciones acordadas es una fase posterior (v2, UI-04/UI-05).

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Auditoría UI y Plan de Reubicación** - Auditoría de las cuatro zonas de la interfaz, informe de hallazgos con evidencia y plan de reubicación acordado (sin cambios de código)

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
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Auditoría UI y Plan de Reubicación | 0/TBD | Not started | - |
