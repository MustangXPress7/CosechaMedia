---
gsd_state_version: 1.0
milestone: v1.6.0
milestone_name: Verificación avanzada + Reorganizador de footage
current_phase: beta3-menu
current_phase_name: Reestructuración barra de menú: Datos, Utilidades, absorción Ingesta
status: completed
stopped_at: Completed quick-01-PLAN.md (IngestMixin extraction)
last_updated: "2026-09-07T19:30:00.000Z"
last_activity: 2026-09-07
last_activity_desc: Completed 9 bloques reducción MainWindow (4589→961 líneas, 8 mixins, 394 tests pass)
state_head: f075c601442b9f5e29293d76c2a1abe224cda94f
progress:
  total_phases: 1
  completed_phases: 0
  total_plans: 7
  completed_plans: 7
---

Total Phases: 13

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-15)

**Core value:** Que el operador de cámara pueda vaciar tarjetas SD/cámaras/móviles al archivo del proyecto de forma fiable y sin perder datos — cada archivo copiado con verificación de integridad y organizado correctamente.
**Current focus:** Phase 01.6.0 — Añadir origen + Reorganizador + Bugs + DeviceRegistry

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
- Fase 1.6.0 (migrado desde 1.5.0): Volcado selectivo multi-origen (ID-01), escaneo MTP vía caché (ID-02), ID-04 borrado de caché

### Estética (BACKLOG_UI_V2 → v1.5)

- B-09: Tipografía con jerarquía
- B-10: Espaciado y superficies
- B-11: Microinteracciones y botón primario
- B-12: Auditoría estética formal

### Reservado para v2.0

- I-01: Acciones rápidas / modo guiado
- I-13: Pantalla de bienvenida (ligada a I-01)

## Current Position

Phase: 01.6.0 — COMPLETED
Plan: 6 of 6
Status: All plans verified
Last activity: 2026-09-08 — Completed quick 260908-f5o: rename de dispositivo en tabla de orígenes persiste en registro global (device_settings+known_devices) con popup Sí/No/No volver a preguntar (QSettings skip_rename_confirm), auto-fill USB de nombre conocido en Añadir origen (58 tests, 5 commits)

## Phase 1.6.0 — Verificación Avanzada (ingest-focused)

### Ola 1 — Verificación XXH64+ASC MHL

- [ ] Crear módulo `app/core/integrity.py`
- [ ] Añadir columna `hash_policy` a `projects`

### Ola 2 — Reorganizador Footage (REQ-06)

- [ ] Crear `app/ui/reorganize_dialog.py`
- [ ] Mover en sitio usando `metadata_engine`

**Nota:** Mantener 1.6.0 enfocado en ingesta. Otras features a fases intermedias.

## Next Steps

Use `/gsd-plan-phase 1.6.0` to break down into concrete plans.

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
| 01.5.0-01 (D-01/D-02 ffprobe retry + marker) | 22m | 3 tasks | 4 files |
| 01.5.0-02 (copy_verified hash stream-through) | 12m | 3 tasks | 2 files |
| 01.5.0-03 (watcher inventory + should_skip) | 45m | 3 tasks | 5 files |
| 01.5.0-04 (R3/R5 regression + full suite gate) | 15m | 2 tasks | 2 files |
| 01.6.0-01 (COM threading + SinClasificar) | 36m | 2 tasks | 12 files |
| 01.6.0-02 (AddSourceDialog) | 45m | 3 tasks | 5 files (2 new, 1 mod, 2 del) |
| 01.6.0-03 (Reorganizador) | 25m | 3 tasks | 4 files (2 new, 1 mod) |
| Phase 01.6.0 P05 | 31 | 2 tasks | 7 files |
| Phase 01.6.0 P07 | 75 | 3 tasks | 8 files |
| Phase quick P01 | 45 | 3 tasks | 5 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Plan 01.5.0-01]: Retry de ffprobe ÚNICO en TimeoutExpired (Pitfall 6) — reintento con probe format-only (sin -show_streams) y timeout 30 s; rama genérica sin retry
- [Plan 01.5.0-01]: Dict de metadata de fallo idéntico en forma al de éxito con metadata_verified=False + metadata_error y file_size real vía getsize (nunca lanza)
- [Plan 01.5.0-01]: detect_camera_batch no cuenta como cámara real los fallos (metadata_verified is False) ni Unknown/Unknown_Camera
- [Plan 01.5.0-01]: Marker "Metadatos no verificados" SOLO en la celda de cámara (columna 1) + tooltip; la columna de estado mantiene el texto exacto "Completado" (Pitfall 3 — _clear_completed_rows intacto)
- [Plan 01.5.0-02]: copy_verified calcula el hash MD5 del origen una sola vez (pase stream-through) y lo devuelve; se elimina la relectura del destino con calculate_md5 (ingestor.py:61-68) — R4 / D-03
- [Plan 01.5.0-02]: Se conserva la semántica de borrado de destino corrupto/parcial (excepción de lectura/escritura → os.remove(dest_path) + None); calculate_md5 se mantiene para _handle_reference_file y tests
- [Iniciativa]: Auditoría primero, implementación después — el roadmap v1 es 100% diagnóstico (sin cambios de código)
- [Iniciativa]: Alcance = diagnóstico + plan por zona; la implementación (UI-04/UI-05) se difiere a v2 por decisión explícita del usuario
- [Iniciativa]: Todas las zonas de la UI con igual prioridad — el operador usa la app de extremo a extremo
- [Phase ?]: Quick k7i: ProjectWizard reactivado como única vía de creación de proyecto (600x520, callbacks on_finished/on_cancel)
- [Phase ?]: Quick k7i: gestión de dispositivos guardados migrada a Añadir origen — rol ('device', id) + menú contextual Eliminar guardado; menú Ingesta depurado sin código zombie
- [Fase 1.5.0 → 1.6.0 (2026-08-29)]: Volcado selectivo multi-origen (global = todos los orígenes; per-device = uno a uno), escaneo MTP completo vía caché para ordenar por fecha sin volcar, y opción "todo" para revertir la selección (reasignada: los features pasan a la Fase 1.6.0; la 1.5.0 queda acotada a bugs)
- [Priorización]: Convención de prioridades de uso — cambios críticos de usabilidad = "uso"; funcionalidad nueva = "nuevo feature" (no feature-request genérico)
- [Incidente 1.6.0 (2026-09-03)]: La primera ejecución de plan-phase 1.6.0 desmadró `main_window.py` (botón añadir origen hacía desaparecer la ventana) y se revirtió; `test_source_picker.py` quedó colgando. El contexto completo se recapturó (D-01..D-25) en `01.6.0-CONTEXT.md` y el plan de recuperación está en `.planning/todos/pending/plan-accion-post-incidente-1-6-0-recuperacion.md`.
- [Recuperación 1.6.0 (2026-09-03)]: Limpieza de árbol completada (pasos A): 27 archivos de debug eliminados, 9 dirs de fases fantasma + PROPOSED.md stale eliminados, `main_window.py` con el fix SC4 (thread-local COM + `_reset_ingestors`) commiteado como `fix(mtp)` 46b96a3, ROADMAP.md reestructurado (1.6.0/1.7.0/1.8.0), keep-alive del todo de limpieza.
- [Plan 01.6.0-03]: ReorganizeDialog usa QStackedWidget 3 páginas (selector → resumen → ejecución) con workers off-thread (_ScanWorker, _MoveWorker) para no bloquear UI
- [Plan 01.6.0-03]: MD5 recalc obligatorio al mover (D-19 override) — dest_path SIEMPRE actualizado tras move, md5_hash=NULL si calculate_md5 falla tras reintento
- [Plan 01.6.0-03]: Sin reporte CSV (D-21) — resumen en diálogo basta; archivos sin clasificar permanecen en SinClasificar/ y se reportan (D-18)
- [Plan 01.6.0-03]: "Reorganizar footage…" en botón post-ingesta Y menú &Ingesta (D-22) — disponible sin ingesta activa para volcados manuales
- [Phase 01.6.0]: Reutilizar save_dispositivo_config(device_id, nombre_dispositivo) en lugar de anadir update_device_camera_name: el esquema real de device_settings ya tiene device_key/nombre_dispositivo (el SQL del plan asumia una columna camera_name inexistente)
- [Phase 01.6.0]: Propagar el nombre editado por callback (on_camera_name_changed) desde AddSourceDialog sin acoplarlo a db
- [Phase 01.6.0]: Excluir nombres de marcador de posicion (Detectando/Sin nombre/Vacio) de la persistencia en el combo de dispositivos
- [Phase 01.6.0]: Sanitizar nombres de dispositivo en la capa de datos (DatabaseManager._sanitize_dispositivo_nombre) ademas del handler, para cualquier escritura futura (T-01.6.0-15)
- [Phase 01.6.0]: DeviceRegistry write path: auto-upsert known_devices on MTP/FTP detection via list_devices() and stage()
- [Phase 01.6.0]: Legacy device_settings migration to known_devices runs idempotently at startup via _migrate_legacy_devices()
- [Phase 01.6.0]: Cross-project device persistence: known_devices table + delete_all_known_cameras/delete_all_saved_devices kill-switches clear known_devices
- [Phase 01.6.0]: Removed btn_detect_drives from main_window (replaced by auto-detection D-09); upsert_known_device in save_dispositivo_config paths
- [Phase 01.6.0]: IngestMixin placed last in MRO (after WifiMixin, CameraMixin) to access their methods
- [Phase 01.6.0]: Worker functions (_format_sources_worker, _generate_proxies_worker, _reorganize_worker, _probe_device_connectivity) kept at module level in main_window.py
- [Phase 01.6.0]: ORG_TYPE_MAP duplicated in ingest_mixin.py for module independence
- [Phase 01.6.0]: Parallel db patching extended to ingest_mixin_module across 16 test classes (mirroring CameraMixin pattern)

### Roadmap Evolution

- Roadmap renumerado por versión (2026-08-29): fases 1.5.0 / 1.6.0 / 2.0. La antigua Fase 2 (volcado selectivo multi-origen) queda dentro de 1.5.0; la antigua Fase 3 (verificación avanzada XXH64+ASC MHL) pasa a 1.6.0 junto a REQ-06 (Reorganizar footage); modo guiado (I-01) y pantalla de bienvenida (I-13) quedan en 2.0
- Acotación posterior (2026-08-29): la 1.5.0 queda como fase ligera de bugs (CONCERNS.md) resueltos por quick tasks; ID-01/ID-02/ID-04 migran a la 1.6.0 y el I-07 pasa a decisión de dashboard, fuera del alcance de la 1.5.0
- Reasignación de roadmap (2026-09-10): notificadores SMTP/Telegram y volcado por orden de dispositivo → **Fase 1.8.0**; R-05 (XXH64+ASC MHL) → **Fase 1.7.0** (plan 01.7.0-06); reorganizador avanzado ffprobe (ex 01.7.0-03) → **Fase 1.8.0** (01.8.0-03); ID-01/ID-02 → **Fase 1.7.0** (01.7.0-07/08); I-24 → **Fase 2.0**; ideas abiertas sin conexión (I-02, I-04, I-21, I-25) → **Fase 2.0**. **Phase 1.9.0** creada (velocidad de copia + resume + reportes, del análisis OffShoot). Planes de 1.7.0 renumerados (8: 01..08). Mejora de interfaz/funciones del reorganizador de footage → **Fase 1.8.0** (01.8.0-05), total 5 planes

### Pending Todos

- Investigar y fixear bugs conocidos de CONCERNS.md (FFprobe timeout, watcher re-ingesta, DB path CWD, doble MD5, device polling UI thread)
- Features v1.5: I-03/I-06/I-11/I-14 ✅ ya implementados; I-07 decisión por dashboard; Fase 2 (ID-01/ID-02/ID-04) → Fase 1.6.0
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
| 260821-io6 | Lote de pulido UI: wizard avanzadas colapsables con auto-reajuste, WiFi directo al QR, orden del lanzador, progreso sin texto hasta finalizar, combo de sesiones elástico con botones al borde, icono llave, anchos de orígenes, flechas svg reales (combo+spinbox), primarios y todo el azul por defecto según acento con retintado en caliente, fix json local en start_ingest | 2026-08-21 | c6815e1 | Needs Review | [260821-io6-ui-polish-batch-wizard-advanced-toggle-d](./quick/260821-io6-ui-polish-batch-wizard-advanced-toggle-d/) |
| 260822-gi3 | Actualizar README para versión 1.5: volcado selectivo por sesión, fechas flexibles, proyectos en un paso, informes CSV en post-ingesta, detección de dispositivos completada (sin WIP), iconos SVG tintables — mitades EN/ES simétricas 18/18 | 2026-08-22 | 768ceb0 | Verified | [260822-gi3-actualizar-readme-para-version-1-5-con-l](./quick/260822-gi3-actualizar-readme-para-version-1-5-con-l/) |
| 260822-ive | Licencia GPL-3.0-or-later (LICENSE canónica de gnu.org + README bilingüe + cabecera main.py) y preparación firma: codesign ad-hoc macOS en CI antes de zip/hash, docs/SIGNING.md con roadmap SignPath Foundation y workaround Gatekeeper | 2026-08-22 | aec250a | Needs Review | [260822-ive-cambiar-licencia-a-gpl-3-0-y-preparar-fi](./quick/260822-ive-cambiar-licencia-a-gpl-3-0-y-preparar-fi/) |
| 260822-ml7 | Cask de Homebrew para distribución macOS: cask propio (arm64 temporal + dependencia ffmpeg, sha256 :no_check documentado), docs/HOMEBREW.md (instalación --no-quarantine, publicación manual del tap homebrew-tap, checklist por release con fijado de SHA-256) y subsección Homebrew espejo EN/ES en README | 2026-08-22 | ffd2957, cd1feb2, a314038 | Needs Review | [260822-ml7-cask-de-homebrew-para-distribucion-macos](./quick/260822-ml7-cask-de-homebrew-para-distribucion-macos/) |
| 11 | Bump version 1.5.0.b3 para release beta3 (licencia GPL + firma ad-hoc macOS) | 2026-08-22 | ee2c0ca | — | — |
| 260904-bugs-add-source-dialog | Bugs (7) y mejoras (6) del diálogo «Añadir origen»: WiFi QR duplicado, borrar no actualiza tabla, Nuevo WiFi, falsos positivos MTP, cámara no persiste, menú Herramientas de limpieza, checkboxes centrados, secciones span, combo de cámara con escáner | 2026-09-04 | b853589 | Verified | [260904-bugs-add-source-dialog](./quick/260904-bugs-add-source-dialog/) |
| 260904-dwm | Fix _browse_session_src unpacking error (ValueError) al elegir origen en el selector de sesión: _pick_source_entry devuelve lista de dicts, no tupla; despacho con binding de sesión + manejos device/usb/ftp_new/wifi | 2026-09-04 | 86a608a | Verified | [260904-dwm-fix-browse-session-src-unpacking-error-v](./quick/260904-dwm-fix-browse-session-src-unpacking-error-v/) |
| 260904-eae | Fix on_file_finished UnboundLocalError (camera_item) al finalizar archivo con camera_model 'Unknown' + metadatos verificados (ingesta con dos sesiones mismo origen distinto destino): conserva el valor de la celda de cámara | 2026-09-04 | 1634091 | Verified | [260904-eae-fix-on-file-finished-unboundlocalerror-c](./quick/260904-eae-fix-on-file-finished-unboundlocalerror-c/) |
| 260906-ci2 | Extraer el flujo WiFi/PairDrop de MainWindow a WifiMixin: 24 métodos WiFi verbatim a app/ui/mixins/wifi_mixin.py (composición MainWindow(QMainWindow, WifiMixin)), workers (_StageWorker/_TaskWorker/DashboardBackground) a mixins/workers.py, main_window ~4670→4159 líneas, tests wifi adaptados al singleton del mixin | 2026-09-06 | f574a76, 6e3fe5f | Verified | [260906-ci2-extraer-el-flujo-wifi-pairdrop-de-mainwi](./quick/260906-ci2-extraer-el-flujo-wifi-pairdrop-de-mainwi/) |
| 260906-epl | Bloque 1 (reducción god object MainWindow): extraer los 4 diálogos de configuración inline a app/ui/ — ProjectSettingsDialog, CameraOverridesDialog, NamesManagerDialog, DumpLocationsDialog (patrón AboutDialog, QDialog + QtString wrapper, singleton db), 6 métodos de MainWindow convertidos en wrappers finos, main_window 4589→4141 líneas, suite 393 passed (único fail pre-existente order-dependent test_mtp) | 2026-09-06 | 8ffb70c | Verified | [260906-epl-bloque-1-extraer-los-4-di-logos-de-confi](./quick/260906-epl-bloque-1-extraer-los-4-di-logos-de-confi/) |
| 260906-fgl | Bloque 3 (reducción god object MainWindow): extraer detección/nombrado de cámara + lectura SD a CameraMixin (app/ui/mixins/camera_mixin.py) — 16 métodos verbatim (camera rename, prompt nombre dispositivo, mapping, _detect_sd_card, auto-detect drives, _drive_label/_find_smallest_media), composición MainWindow(QMainWindow, WifiMixin, CameraMixin), parche paralelo db en 18 setUps de 5 ficheros test, main_window 4141→3750 líneas, suite 393 passed | 2026-09-06 | bc650bf | Verified | [260906-fgl-bloque-3-extraer-la-deteccion-nombrado-d](./quick/260906-fgl-bloque-3-extraer-la-deteccion-nombrado-d/) |
| 260906-i6a | Bloque 2 (reducción god object MainWindow): extraer gestión de sesiones a SessionsMixin (app/ui/mixins/sessions_mixin.py) — 18 métodos verbatim (combo sesiones, modos vuelco, filtros, _populate_source_paths_from_sessions, _open_content_filter), composición + SessionsMixin, parche db en 18 setUps, main_window 3750→3337 líneas, suite 393 passed | 2026-09-07 | fa43085 | Verified | [260906-i6a-bloque-2-extraer-la-gestion-de-sesiones-](./quick/260906-i6a-bloque-2-extraer-la-gestion-de-sesiones-/) |
| 260906-01 | Bloque 4 (reducción god object MainWindow): extraer tabla de fuentes + menús a SourcesMixin (app/ui/mixins/sources_mixin.py) — 30 métodos verbatim (tabla, widgets, context menus, entry helpers), composición + SourcesMixin, parche db en 18 setUps, main_window 3337→2721 líneas, suite 393 passed | 2026-09-07 | 487db42 | Verified | [260906-sources-mixin/260906-01-PLAN.md](./quick/260906-sources-mixin/) |
| 260906-01 | Bloque 5 (reducción god object MainWindow): extraer ciclo de proyecto a ProjectMixin (app/ui/mixins/project_mixin.py) — 21 métodos verbatim (create/load/close/delete/duplicate/rename/root change), composición + ProjectMixin, parche db en 18 setUps, main_window 2721→2143 líneas, suite 393 passed | 2026-09-07 | 1c5770d | Verified | [260906-project-mixin/260906-01-PLAN.md](./quick/260906-project-mixin/) |
| 260906-01 | Bloque 6 (reducción god object MainWindow): extraer registro dispositivos + staging MTP/FTP a DevicesMixin (app/ui/mixins/devices_mixin.py) — 18 métodos verbatim (device pickers, folder assign, MTP/FTP staging, COM reset), composición + DevicesMixin, parche db, main_window 2143→~1973 líneas, suite 393 passed | 2026-09-07 | 6bddf94 | Verified | [260906-bloque6-devicesmixin/260906-01-PLAN.md](./quick/260906-bloque6-devicesmixin/) |
| 260906-01 | Bloque 7 (reducción god object MainWindow): extraer menú + language switch a MenuMixin (app/ui/mixins/menu_mixin.py) — 2 métodos verbatim (build_menu, _switch_language), composición + MenuMixin, parche db, main_window ~1973→~1800 líneas, suite 393 passed | 2026-09-07 | 4dcabaf | Verified | [260906-menu-mixin/260906-01-PLAN.md](./quick/260906-menu-mixin/) |
| 260906-01 | Bloque 8 (reducción god object MainWindow): extraer pipeline ingesta + post-actions a IngestMixin (app/ui/mixins/ingest_mixin.py) — 29 métodos verbatim (start/stop_ingest, on_file_*, _finalize_ingest, format/proxies/report/shutdown), composición + IngestMixin, parche db + ingest_mixin_module.db fixes, main_window ~1800→~1200 líneas, suite 393 passed | 2026-09-07 | f075c60/d66ad05 | Verified | [260906-ingest-mixin-extraction/260906-01-PLAN.md](./quick/260906-ingest-mixin-extraction/) |
| 260906-bloque9 | Bloque 9 (reducción god object MainWindow): descomponer setup_views en 8 helpers + limpieza (elimina _reorganize_worker dead code), main_window ~1200→961 líneas, suite 394 passed (1 pre-existente test_mtp) | 2026-09-07 | 7598f5d | Verified | [260906-bloque9-setup-views-decomposition/260906-bloque9-PLAN.md](./quick/260906-bloque9-setup-views-decomposition/) |
| 260907-p7b | Fix 7 bugs (fase 1.5.0): WiFi QR IP errónea (local_ip sin Internet + multi-NIC), FTP «timed out» con host:puerto, crash «Detectar» (COM manager reutilizado de apartamento cerrado), aviso «Proyecto requerido» al añadir origen sin proyecto, purga de `folder` en known_devices, «— Vacío —» predeterminado en selector de cámara (manual+auto), nombre fijo read-only en filas WiFi/FTP de Añadir origen | 2026-09-07 | 10fc7e3, dd07468, 84b0ebc, ac48027, c672e9b, 7eb5405, 3a8acbd | Needs Review | [260907-p7b-fix-7-bugs-wifi-qr-ip-erronea-ftp-timeou](./quick/260907-p7b-fix-7-bugs-wifi-qr-ip-erronea-ftp-timeou/) |
| 260907-fb2 | Fix 4 bugs: WiFi/FTP sin conexión (IP virtual/link-local, subred), origen USB fantasma «[MTP] F:\» (falso positivo + render), «+» Sesiones NameError QDate, churn COM (cache list_devices) | 2026-09-07 | pending | Planned | [260907-fb2-feedback-wifi-ftp-fantasma-sesiones](./quick/260907-fb2-feedback-wifi-ftp-fantasma-sesiones/) |
| 260908-f5o | Renombrar dispositivo en la tabla de orígenes: persistir nombre en registro (device_settings+known_devices) con popup Sí/No/No volver a preguntar (QSettings), auto-fill USB de nombre conocido en Añadir origen | 2026-09-08 | 865f373 | Verified | [260908-f5o-renombrar-dispositivo-en-la-tabla-de-or-](./quick/260908-f5o-renombrar-dispositivo-en-la-tabla-de-or-/) |

## Deferred Items

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| debug_sessions | bug-qr-proyecto-blanco | investigating | 2026-08-29 | v1.5.0 |
| debug_sessions | revisemos-bugs-anotados-para-r | investigating | 2026-08-29 | v1.5.0 |
| quick_tasks | 260821-io6-ui-polish-batch-wizard-advanced-toggle-d | unknown | 2026-08-29 | v1.5.0 |
| quick_tasks | 260821-nem-ui-tabla-origenes-boton-dedicado-usb-mtp | unknown | 2026-08-29 | v1.5.0 |
| todos | revisar-awesome-python.md | (presence-only) | 2026-08-29 | v1.5.0 |
| todos | ui-sugerencias-dispositivos-conocidos.md | (presence-only) | 2026-08-29 | v1.5.0 |
| verification_gaps | 01/01-VERIFICATION.md | human_needed | 2026-08-29 | v1.5.0 |
| Implementación de reubicaciones | UI-04/UI-05 (v2) | Pending | 2026-08-15 | v1.0 |
| Refactor core | MainWindow god object, logging, migraciones | Out of scope | 2026-08-15 | v1.0 |

## Session Continuity

Last session: 2026-09-07T21:15:00.000Z
Stopped at: Plan escrito para quick 260907-fb2 (4 bugs: WiFi/FTP conexión, USB fantasma, sesiones +, churn COM); en espera de aprobación para ejecutar código
Resume file: None

## Operator Next Steps

- Start the next milestone with /gsd-new-milestone
