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

## Milestones

- ✅ **v1.5.0 Consolidación y bugs del flujo** — Phases 1, 1.5.0 (shipped 2026-08-29)
- 🚧 **v1.6.0 Verificación avanzada + Reorganizador de footage** — Phases 1.6.0 (in progress)
- 📋 **v2.0 Modo guiado + Pantalla de bienvenida** — Phases 2.0 (planned)

## Phases

<details>
<summary>✅ v1.5.0 Consolidación y bugs del flujo (Phases 1, 1.5.0) — SHIPPED 2026-08-29</summary>

- [x] **Phase 1: Auditoría UI y Plan de Reubicación** (4/4 plans) — completed 2026-08-29
- [x] **Phase 1.5.0: Consolidación y bugs del flujo** (4/4 plans) — completed 2026-08-29

</details>

<details>
<summary>🚧 v1.6.0 Verificación avanzada + Reorganizador de footage (Phase 1.6.0) — IN PROGRESS</summary>

- [ ] **Phase 1.6.0: Añadir origen + Reorganizador + Bugs** (0/3 plans) — planned

</details>

<details>
<summary>📋 v2.0 Modo guiado + Pantalla de bienvenida (Phase 2.0) — PLANNED</summary>

- [ ] **Phase 2.0: Modo guiado + Pantalla de bienvenida** (0/0 plans) — planned

</details>

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

**Plans:** 4/4 plans executed ✅ COMPLETED

Plans:
**Wave 1**

- [x] 01.5.0-01-PLAN.md — Metadata fiable (D-01/D-02): retry degradado de ffprobe + estado visible "no verificados" (R1)
- [x] 01.5.0-02-PLAN.md — Hash único MD5 stream-through en copy_verified (D-03) + reescritura de tests (R4)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01.5.0-03-PLAN.md — Inventario watcher persistente con veredicto + filter_key + poda por antigüedad (D-04, R2)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 01.5.0-04-PLAN.md — Regresiones R3 (DB path CWD) y R5 (auto-sync off-thread) + gate de suite completa

### Phase 1.6.0: Añadir origen + Reorganizador + Bugs + DeviceRegistry

**Goal:** Mejoras críticas en el flujo de añadir orígenes (menús, eliminación, detección cámara), el reorganizador footage, corrección de bugs de thread-local/timers, y registro persistente de dispositivos (DeviceRegistry) para pre-fill cross-proyecto.
**Mode:** standard
**Depends on:** Phase 1.5.0
**Requirements**: B-13, B-20 (mejoras añadir origen); REQ-06 (reorganizador); REQ-09 (registro devices); bugs de COM threading
**Success Criteria** (what must be TRUE):

  1. El menú dispositivo (QR/FTP) aparece en la columna "Ruta de origen", no en "Contenido"
  2. Eliminar origen inhabilita, no borra; botón borrar dispositivos guardados funciona
  3. "Reorganizar footage..." existe y funciona con _SinClasificar
  4. Thread-local COM se limpia correctamente en reset de proyecto
  5. FTP server no se cuelga al conectar; timeouts y keepalive activos
  6. Dispositivos desconectados muestran "Desconectado"; guardados persisten cross-proyecto
  7. Tabla de ingesta usa terminología "Dispositivo"; rename de cámara persiste en device_settings
  8. Proyectos con master_path duplicado dan error controlado (sin DB lock); Wizard guarda master_path
  9. Filtro de fecha de sesiones detecta unidad correctamente; "Actualizar proyectos" no bloquea dump_type
  10. Existe tabla `known_devices` con DeviceRegistry UI (pre-fill al añadir origen, persistencia cross-proyecto)

**Plans:** 6 plans

Plans:

**Wave 1**
- [x] 01.6.0-01-PLAN.md — COM threading balanceado (D-23..D-25) + Unknown_Camera → SinClasificar (D-16, D-18)

**Wave 2**
- [x] 01.6.0-02-PLAN.md — AddSourceDialog tabla plana 3 secciones (D-01..D-15) + integración main_window

**Wave 3**
- [x] 01.6.0-03-PLAN.md — ReorganizeDialog SinClasificar + MD5 re-registro (D-16..D-22, REQ-06)

**Wave 4**
- [ ] 01.6.0-04-PLAN.md — FTP Server Hang + Device Deletion Sync + Disconnected Device Status

**Wave 5**
- [ ] 01.6.0-05-PLAN.md — Ingest Table Terminology (cámara→dispositivo) + Camera Rename Persistence

**Wave 6**
- [ ] 01.6.0-06-PLAN.md — DB Lock Duplicate Master Path + Master Path Wizard + Session Date Interval + Update Projects Button + DeviceRegistry

### Phase 1.7.0: Notificadores SMTP/Telegram

**Goal:** Notificadores configurables por proyecto para avisar al acabar la ingesta.
**Mode:** standard
**Depends on:** Phase 1.6.0
**Requirements**: REQ-07 (notificadores)
**Success Criteria** (what must be TRUE):

  1. Notificadores configurables por proyecto (SMTP + Telegram)
  2. Aviso al finalizar ingesta (éxito/error)

**Plans:** 0 plans

Plans:

- [ ] TBD (run /gsd-plan-phase 1.7.0 to break down)

### Phase 1.8.0: WiFi SSID + verificación XXH64+ASC MHL

**Goal:** El operador conecta cámaras vía WiFi configurando SSID+contraseña, y el material volcado lleva custodia verificable estándar con política de hash configurable.
**Mode:** standard
**Depends on:** Phase 1.7.0
**Requirements**: REQ-08 (WiFi SSID), REQ-06/REQ-05 (verificación)
**Success Criteria** (what must be TRUE):

  1. Servidor FTP embebido funcional (multi-OS)
  2. Conexión WiFi automática con SSID/contraseña
  3. Política de hash selectable (Rápida/Equilibrada/Máxima)

**Plans:** 0 plans

Plans:

- [ ] TBD (run /gsd-plan-phase 1.8.0 to break down)

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
Phases execute in numeric order: 1 (completa), 1.5.0, 1.6.0, 1.7.0, 1.8.0, 2.0

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Auditoría UI y Plan de Reubicación | 4/4 | Complete | 2026-08-29 |
| 1.5.0. Consolidación y bugs del flujo | 4/4 | Complete | 2026-08-29 |
| 1.6.0. Añadir origen + Reorganizador + Bugs + DeviceRegistry | 3/6 | In Progress |  |
| 1.7.0. Notificadores SMTP/Telegram | 0/0 | Planned |  |
| 1.8.0. WiFi SSID + verificación | 0/0 | Planned |  |
| 2.0. Modo guiado + Pantalla de bienvenida | 0/0 | Planned |  |
