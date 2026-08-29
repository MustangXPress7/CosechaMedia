# Roadmap: CosechaMedia — por versión

## Overview

Evolución de CosechaMedia organizada por **versión publicable**: cada fase del roadmap
corresponde a una release (1.5.0, 1.6.0, 2.0). La fase 1 (histórica) fue la iniciativa de
auditoría de la UI, ya completada. A partir de la fase 1.5.0 el plan se ordena por release:
**1.5.0** consolida bugs y fricciones del flujo de volcado (fase ligera por quick tasks),
**1.6.0** añade custodia verificable (verificación avanzada XXH64 + ASC MHL), el
reordenamiento de footage volcado a mano y los features de volcado selectivo multi-origen
(ID-01/ID-02) migrados desde 1.5.0, y **2.0** incorpora el modo guiado y la pantalla de
bienvenida (reservados desde v1.5).

## Phases

**Phase Numbering:**

- Fases versionadas (1.5.0, 1.6.0, 2.0): entregables de una release publicable
- Fase 1 (integer legacy): iniciativa de auditoría original, ya completada
- Fases menores urgentes se pueden insertar como decimales (p. ej. 1.6.1) marcadas con INSERTED

Ejecución en orden numérico: 1 (completa) → 1.5.0 → 1.6.0 → 2.0.

- [x] **Phase 1: Auditoría UI y Plan de Reubicación** - Auditoría de las cuatro zonas de la interfaz, informe de hallazgos con evidencia y plan de reubicación acordado (sin cambios de código)
- [ ] **Phase 1.5.0: Consolidación y bugs del flujo** - Bugs conocidos y fricciones del volcado resueltos (FFprobe timeout, watcher re-ingesta, DB path CWD, doble MD5, polling en UI thread), fase ligera por quick tasks; ID-01/ID-02 migran a 1.6.0 e I-07 se decide por dashboard
- [ ] **Phase 1.6.0: Verificación avanzada + Reorganizador de footage** - Política de hash configurable (Rápida/Equilibrada/Máxima) con XXH64 + manifiestos ASC MHL encadenados por destino, y acción integrada "Reorganizar footage..." (REQ-06) para reconstrucción los volcados a mano
- [ ] **Phase 2.0: Modo guiado + Pantalla de bienvenida** - Acciones rápidas/modo guiado (I-01) que automatizan el flujo tras configurar el proyecto una vez + pantalla de bienvenida (I-13); candidatas REQ-07 (notificadores) / REQ-08 (WiFi cámaras)

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

### Phase 1.5.0: Consolidación y bugs del flujo

**Goal:** Los bugs conocidos del flujo de volcado y las fricciones de uso quedan resueltos y
el milestone v1.5 se cierra de forma fiable. Primera ola ya aplicada en auditoría de bugs
(F-01..F-05): borrado de origen, re-volcado, sesión restante, resume y ventana "últimos x días".
**Mode:** standard
**Depends on:** Phase 1
**Requirements**: CONCERNS.md (bugs activos del flujo de volcado) — fase ligera resuelta por
quick tasks. ID-01/ID-02 (volcado selectivo multi-origen, escaneo MTP vía caché) migrados a
la Fase 1.6.0; I-07 (WiFi resume) se decide por dashboard, fuera de esta fase
**Success Criteria** (what must be TRUE):

  1. Los bugs activos de CONCERNS.md quedan resueltos con regresión cubierta: FFprobe timeout →
     metadata "Unknown"/file_size=0, watcher re-ingesta tras pruning >10k, DB path dependiente de
     CWD en desarrollo, doble hash MD5 por copia, device polling en UI thread

  2. La suite completa de tests (`tests/`, Qt offscreen) pasa; cada fix lleva su test de regresión

**Plans:** 3/4 plans executed (bugs en waves de implementación; la investigación 2026-08-29 reveló que 3 de los 5 bloques no estaban aplicados)

Plans:
**Wave 1**

- [x] 01.5.0-01-PLAN.md — Metadata fiable (D-01/D-02): retry degradado de ffprobe + estado visible "no verificados" (R1)
- [x] 01.5.0-02-PLAN.md — Hash único MD5 stream-through en copy_verified (D-03) + reescritura de tests (R4)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01.5.0-03-PLAN.md — Inventario watcher persistente con veredicto + filter_key + poda por antigüedad (D-04, R2)

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 01.5.0-04-PLAN.md — Regresiones R3 (DB path CWD) y R5 (auto-sync off-thread) + gate de suite completa

### Phase 1.6.0: Verificación avanzada + Reorganizador de footage

**Goal:** El material volcado lleva custodia verificable estándar: cada volcado completado sella
una generación ASC MHL nueva en `ascmhl/` de la raíz destino (cadena acumulativa por disco), con
política de hash configurable por proyecto — Rápida (XXH64), Equilibrada (XXH64 + pasada MD5,
default) o Máxima (MD5 + sidecars `.sha256` extra) — seleccionable tanto en el ProjectWizard como
en el menú de configuración. Además, el operador puede reconstruir volcados hechos a mano fuera de
la app con **"Reorganizar footage..."** (REQ-06): mueve en sitio a `Footage/<Cámara>/<Fecha>` sin
recopiar, con `_SinClasificar`, colisiones resueltas y reporte de movimientos.
**Mode:** standard
**Depends on:** Phase 1.5.0
**Requirements**: REQ-06 (reorganizador); diseño `.planning/notes/diseno-xxh64-asc-mhl.md`
(decisiones D1-D5) para verificación avanzada; ID-01 (volcado selectivo global multi-origen)
e ID-02 (escaneo MTP completo vía caché) — migrados desde la Fase 1.5.0
**Success Criteria** (what must be TRUE):

  1. La política de hash es seleccionable en opciones avanzadas del ProjectWizard y en el menú de configuración de proyecto; proyectos existentes/nuevos sin preferencia usan Equilibrada
  2. `copy_verified` usa el árbitro del nivel elegido y conserva la semántica actual de borrado de destino corrupto; los hashes quedan persistidos en la DB (migración inline de `files`)
  3. Cada volcado completado añade una generación verificable a la cadena `ascmhl/` del destino usando el paquete oficial `ascmhl` (MIT); volcados sucesivos encadenan generaciones
  4. Los manifiestos/sidecars reflejan el nivel: Rápida = xxh64; Equilibrada = md5+xxh64 con segunda pasada sobre destino; Máxima = md5 + sidecars `.sha256` propios fuera del MHL
  5. Los informes CSV incluyen columnas de hashes y la suite de tests valida roundtrip contra la CLI oficial `ascmhl verify`
  6. "Reorganizar footage..." (REQ-06) existe como acción integrada con su diálogo: mueve en sitio (sin MD5) a `Footage/<Cámara>/<Fecha>` via `metadata_engine`, no clasificables a `Footage/_SinClasificar/` con reporte, colisiones con capa "aplicar a todas", y nunca borra archivos
  7. El volcado selectivo **global** (ID-01) incluye todos los orígenes añadidos (per-device conserva selección uno a uno) y el escaneo MTP completo vía caché (ID-02) permite listar/filtrar por fecha sin volcar (migrados desde la 1.5.0)

**Plans:** 0 plans

Plans:

- [ ] TBD (run /gsd-plan-phase 1.6.0 to break down)

### Phase 2.0: Modo guiado + Pantalla de bienvenida

**Goal:** El operador configura el proyecto una vez y las **acciones rápidas / modo guiado**
(I-01) automatizan el flujo completo — conectar el dispositivo y aprobar el plan que propone la
app — apoyándose en la **pantalla de bienvenida** (I-13) al primer arranque para elegir acciones
rápidas sin trastear. Candidatas a incluir: REQ-07 (notificadores inteligentes al acabar la
ingesta) y REQ-08 (WiFi por SSID+contraseña para cámaras; bloqueada por spike de viabilidad).
**Mode:** standard
**Depends on:** Phase 1.6.0
**Requirements**: I-01, I-13 (reservadas desde v1.5); REQ-07/08 como candidatas
**Success Criteria** (what must be TRUE):

  1. Existe un modo guiado (I-01): el proyecto se configura una vez y al conectar un dispositivo la app propone un plan de volcado que el operador solo aprueba
  2. La pantalla de bienvenida (I-13) aparece en el primer arranque y guía la selección de acciones rápidas, sin pasos sueltos
  3. UI-04/UI-05 (implementación de reubicaciones acordadas en Phase 1) se incorporan a este alcance si el plan de reubicación lo exige
  4. REQ-07 (notificadores) y REQ-08 (WiFi cámaras) se incorporan o quedan fuera con decisión documentada; REQ-08 sin incorporar mientras no pase el spike de viabilidad

**Plans:** 0 plans

Plans:

- [ ] TBD (run /gsd-plan-phase 2.0 to break down)

## Progress

**Execution Order:**
Phases execute in numeric order: 1 (completa), 1.5.0, 1.6.0, 2.0

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Auditoría UI y Plan de Reubicación | 4/4 | In Progress|  |
| 1.5.0. Consolidación y bugs del flujo | 3/4 | In Progress|  |
| 1.6.0. Verificación avanzada + Reorganizador de footage | 0/0 | Planned |  |
| 2.0. Modo guiado + Pantalla de bienvenida | 0/0 | Planned |  |
