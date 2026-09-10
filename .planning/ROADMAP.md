# Roadmap: CosechaMedia — por versión

## Overview

Evolución de CosechaMedia organizada por **versión publicable**: cada fase del roadmap
corresponde a una release (1.5.0, 1.6.0, 1.7.0, 2.0). La fase 1 (histórica) fue la iniciativa de
auditoría de la UI, ya completada. A partir de la fase 1.5.0 el plan se ordena por release:
**1.5.0** consolida bugs y fricciones del flujo de volcado (fase ligera por quick tasks),
**1.6.0** añade el diálogo unificado de orígenes, el reorganizador de footage, el DeviceRegistry y
bugs de COM/FTP/UI, **1.7.0** añade notificadores, pulido visual UI, configuración de proyecto
(plantillas, bienvenida, orígenes en el wizard) y reorganizador con filtros ffprobe, y **2.0**
incorpora el modo guiado que se apoya en las plantillas creadas en 1.7.0. **1.9.0** cierra la
brecha percibida con OffShoot: velocidad de copia, resume robusto y reportes presentables.

## Milestones

- ✅ **v1.5.0 Consolidación y bugs del flujo** — Phases 1, 1.5.0 (shipped 2026-08-29)
- 🚧 **v1.6.0 Verificación avanzada + Reorganizador de footage** — Phases 1.6.0 (in progress)
- 📋 **v1.7.0 Notificadores + Pulido visual + Configuración de proyecto + Reorganizador avanzado** — Phases 1.7.0 (planned)
- 📋 **v2.0 Modo guiado con plantillas** — Phases 2.0 (planned)
- 📋 **v1.9.0 Velocidad de copia + Resume robusto + Reportes presentables** — Phases 1.9.0 (planned)

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
<summary>📋 v1.7.0 Notificadores + Pulido visual + Configuración de proyecto + Reorganizador avanzado (Phase 1.7.0) — PLANNED</summary>

- [ ] **Phase 1.7.0** (0/6 plans) — planned

</details>

<details>
<summary>📋 v2.0 Modo guiado con plantillas (Phase 2.0) — PLANNED</summary>

- [ ] **Phase 2.0: Modo guiado con plantillas** (0/0 plans) — planned

</details>

<details>
<summary>📋 v1.9.0 Velocidad de copia + Resume robusto + Reportes presentables (Phase 1.9.0) — PLANNED</summary>

- [ ] **Phase 1.9.0: Velocidad de copia + Resume robusto + Reportes presentables** (0/3 plans) — planned

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

**Plans**: 4/5 plans executed
Plans:

- [ ] 01-PLAN-REUBICACION.md

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

**Plans:** 6/6 plans executed

Plans:

**Wave 1**

- [x] 01.6.0-01-PLAN.md — COM threading balanceado (D-23..D-25) + Unknown_Camera → SinClasificar (D-16, D-18)

**Wave 2**

- [x] 01.6.0-02-PLAN.md — AddSourceDialog tabla plana 3 secciones (D-01..D-15) + integración main_window

**Wave 3**

- [x] 01.6.0-03-PLAN.md — ReorganizeDialog SinClasificar + MD5 re-registro (D-16..D-22, REQ-06)

**Wave 4**

- [x] 01.6.0-04-PLAN.md — FTP Server Hang + Device Deletion Sync + Disconnected Device Status

**Wave 5**

- [x] 01.6.0-05-PLAN.md — Ingest Table Terminology (cámara→dispositivo) + Camera Rename Persistence

**Wave 6**

- [x] 01.6.0-06-PLAN.md — DB Lock Duplicate Master Path + Master Path Wizard + Session Date Interval + Update Projects Button + DeviceRegistry

**Wave 7**

- [x] 01.6.0-07-PLAN.md — DeviceRegistry Write Path: upsert on MTP/FTP detection + camera rename + legacy migration + remove Detect button

### Phase 1.7.0: Notificadores SMTP/Telegram + Volcado por orden + Pulido visual UI + Configuración de proyecto + Reorganizador avanzado

**Goal:** Notificadores configurables por proyecto para avisar al acabar la ingesta, volcado de tarjetas por orden de dispositivo (reubicado desde 1.6.0) para rotar tarjetas con un solo lector, pulido visual de la UI con QSS moderno en `app/ui/` sin tocar core, integración mínima HTML para el fondo de trigo interactivo, configuración de proyecto de un vistazo (plantillas, bienvenida, orígenes en el wizard) y reorganización filtrable por metadatos.
**Mode:** standard
**Depends on:** Phase 1.6.0
**Requirements**: REQ-07 (notificadores); volcado por orden de dispositivo (todo 2026-09-02); mejora visual UI fase 1 — QSS, componentes Card/Chip, iconografía y animaciones Qt en `app/ui/`; fondo trigo interactivo con HTML/CSS hover en `app/ui/web/` mediante QWebEngineView mínimo; plantillas de proyecto (sustituye "acciones rápidas"); ventana de bienvenida I-13 (reubicada desde 2.0); pre-adición de orígenes en ProjectWizard; reorganizador con filtros por resolución y otros parámetros (ffprobe)
**Success Criteria** (what must be TRUE):

  1. Notificadores configurables por proyecto (SMTP + Telegram)
  2. Aviso al finalizar ingesta (éxito/error)
  3. Volcado por orden de dispositivo: con un solo lector, el operador rota tarjetas y la ingesta las procesa en orden
  4. Pulido visual UI Fase 1 aplicado en `app/ui/`: QSS modernizado con radios, spacing y sombras coherentes, componentes Card/Chip reutilizables, iconografía SVG consistente y micro-animaciones Qt, manteniendo tema oscuro/claro + acentos y sin cambios en `app/core/`
  5. Fondo de trigo interactivo mínimo: vista HTML/CSS incrustada con QWebEngineView que muestra patrón de espigas y animación hover `transform` sobre las vainas, color sincronizado con tema, sin modificar `app/core/`
  6. El reorganizador filtra y/o agrupa por resolución y otros metadatos extraídos por ffprobe (códec, fps, duración) antes de mover archivos
  7. La terminología "acciones rápidas" queda sustituida por "plantillas de proyectos"; existen plantillas reutilizables aplicables al crear un proyecto
  8. Ventana de bienvenida al primer arranque: proyectos recientes o crear proyecto nuevo, con opción "no volver a mostrar"
  9. El asistente de creación de proyecto permite añadir orígenes de antemano (USB/MTP, WiFi/QR, FTP)

**Plans:** 0 plans

Plans:

- [ ] 01.7.0-01-PLAN.md — Pulido visual UI Fase 1: QSS moderno, componentes Card/Chip, iconografía y animaciones en `app/ui/` (sin tocar core)
- [ ] 01.7.0-02-PLAN.md — Fondo trigo interactivo mínimo: QWebEngineView HTML/CSS con hover en vainas, integración en `app/ui/` y sincronización de color de tema
- [ ] 01.7.0-03-PLAN.md — Reorganizador avanzado: filtrado/agrupación por resolución, códec, fps y duración (ffprobe) en ReorganizeDialog
- [ ] 01.7.0-04-PLAN.md — Plantillas de proyectos: sustituye "acciones rápidas", plantillas reutilizables aplicables al crear proyecto
- [ ] 01.7.0-05-PLAN.md — Ventana de bienvenida (I-13, reubicada desde 2.0): proyectos recientes + crear nuevo + "no volver a mostrar"
- [ ] 01.7.0-06-PLAN.md — ProjectWizard: pre-adición de orígenes al crear el proyecto
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

### Phase 2.0: Modo guiado con plantillas

**Goal:** El operador configura el proyecto una vez y el **modo guiado** (I-01) automatiza el flujo completo — conectar el dispositivo y aprobar el plan que propone la app — apoyándose en las **plantillas de proyectos** (reubicadas desde 1.7.0). Candidatas a incluir: REQ-08 (WiFi por SSID+contraseña para cámaras; bloqueada por spike de viabilidad). La ventana de bienvenida (I-13) ya está implementada en 1.7.0.
**Mode:** standard
**Depends on:** Phase 1.7.0
**Requirements**: I-01 (modo guiado, reubicado aquí); REQ-08 como candidata
**Success Criteria** (what must be TRUE):

  1. Existe un modo guiado (I-01): el proyecto se configura una vez y al conectar un dispositivo la app propone un plan de volcado que el operador solo aprueba
  2. UI-04/UI-05 (implementación de reubicaciones acordadas en Phase 1) se incorporan a este alcance si el plan de reubicación lo exige
  3. REQ-08 (WiFi cámaras) se incorpora o queda fuera con decisión documentada; sin incorporar mientras no pase el spike de viabilidad

**Plans:** 0 plans

Plans:

- [ ] TBD (run /gsd-plan-phase 2.0 to break down)

### Phase 1.9.0: Velocidad de copia + Resume robusto + Reportes presentables

**Goal:** Cerrar la brecha percibida con OffShoot (análisis 2026-09-10 en IDEAS.md): motor de copia más rápido (copia nativa SO, buffers grandes), resume a prueba de duplicados por hash y reportes de ingesta presentables con marca. Candidata: scripts/webhooks post-ingesta sin nube.
**Mode:** standard
**Depends on:** Phase 1.8.0
**Requirements**: I-20 (velocidad de copia), I-22 (resume + duplicados), I-23 (reportes con marca, con I-05) — del análisis de competencia OffShoot; I-24 (scripts/webhooks) como candidata
**Success Criteria** (what must be TRUE):

  1. La copia verificada (MD5 stream-through) alcanza el máximo que permite el hardware sin degradar la verificación: buffers grandes / copia nativa (`CopyFileEx` en Windows, `sendfile` en POSIX) y un benchmark reproducible tarjeta→lector para comparar y publicar
  2. El resume reanuda en cualquier punto aunque existan nombres de archivo idénticos: duplicación por tamaño/hash, no solo por ruta; complementa I-07 (resume WiFi)
  3. Existe un informe de ingesta presentable (HTML/PDF) con logo, título, notas y miniatura por clip (I-05), complementario a los CSV que ya genera
  4. (Candidata) Al terminar una ingesta se puede ejecutar un script o webhook local (I-24), sumándose a los notificadores de 1.7.0

**Plans:** 0 plans

Plans:

- [ ] 01.9.0-01-PLAN.md — Motor de copia rápido (I-20): buffers grandes, copia nativa SO y benchmark público
- [ ] 01.9.0-02-PLAN.md — Resume robusto + detección de duplicados por hash (I-22)
- [ ] 01.9.0-03-PLAN.md — Reportes de ingesta con marca (I-23 + I-05): HTML/PDF con logo, notas y miniaturas
- [ ] TBD (run /gsd-plan-phase 1.9.0 to break down)

## Progress

**Execution Order:**
Phases execute in numeric order: 1 (completa), 1.5.0, 1.6.0, 1.7.0, 1.8.0, 1.9.0, 2.0

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Auditoría UI y Plan de Reubicación | 4/5 | In Progress|  |
| 1.5.0. Consolidación y bugs del flujo | 4/4 | Complete | 2026-08-29 |
| 1.6.0. Añadir origen + Reorganizador + Bugs + DeviceRegistry | 6/6 | Complete | 2026-09-05 |
| 1.7.0. Notificadores + Pulido visual + Configuración de proyecto + Reorganizador avanzado | 0/6 | Planned |  |
| 1.8.0. WiFi SSID + verificación | 0/0 | Planned |  |
| 1.9.0. Velocidad de copia + Resume robusto + Reportes presentables | 0/3 | Planned |  |
| 2.0. Modo guiado con plantillas | 0/0 | Planned |  |

### Phase 2: remove-camera-auto-detection Eliminar modo de detección automática de cámara (solo manual)

**Goal:** [To be planned]
**Requirements**: TBD
**Depends on:** Phase 1
**Plans:** 0 plans

Plans:

- [ ] TBD (run /gsd-plan-phase 2 to break down)

### Phase 3: beta3 Reestructuración barra de menú: Datos, Utilidades, absorción Ingesta

**Goal:** Reestructurar barra de menú agrupando acciones por intención: absorber Ingesta en Proyecto, crear menú Datos para mantenimiento destructivo, renombrar Herramientas a Utilidades y mover Idioma a Ayuda.
**Requirements**: UI-04
**Depends on:** Phase 1.6.0
**Plans:** 1 plan completed

Plans:

- [x] 01.6.1-01-PLAN.md — Reestructuración barra de menú: Proyecto/Datos/Utilidades, Idioma en Ayuda
