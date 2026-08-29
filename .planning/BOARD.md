# BOARD — Estado consolidado CosechaMedia

Última actualización: 2026-08-28 — Verificación de ideas vs código (HEAD 0310aa0; suite 298 OK, skipped=4)
Fuente: .planning/STATE.md, IDEAS.md, ROADMAP.md, BACKLOG_UI_V2.md, codebase/CONCERNS.md, PROJECT.md

## Core Value
Que el operador de cámara pueda vaciar tarjetas SD/cámaras/móviles al archivo del proyecto de forma fiable y sin perder datos — cada archivo copiado con verificación de integridad y organizado correctamente.

## Milestone actual
**v1.5 — Consolidación y bugs (Fase 1.5.0)**
Fase: 00 Bugs conocidos + features v1.5 — STARTING
Última actividad: 2026-08-28 Verificación ideas vs código: I-03/I-15/I-18 y B-08/13/14/15/16/17/18/19/21/22 ya implementados

## Asignación por versión (reordenada 2026-08-29)

| Versión | Contenido |
|---------|-----------|
| **1.5.0** | Bugs y fricciones del flujo de volcado (CONCERNS.md activos + primera ola F-01..F-05 aplicada), volcado selectivo multi-origen + escaneo MTP vía caché (antigua Fase 2), I-07 WiFi resume a decidir |
| **1.6.0** | Verificación avanzada: XXH64 + ASC MHL (R-05) + Reorganizar footage REQ-06 (R-06) |
| **2.0** | Modo guiado I-01 + Pantalla de bienvenida I-13; candidatas REQ-07 notificadores y REQ-08 WiFi cámaras (spike) |

## Resumen ejecutivo
- Fase 1 Auditoría UI completada 4/4 planes. Sin cambios de código.
- Fase 1.5.0 Consolidación y bugs en curso; mejoras volcado selectivo (ID-01/ID-02) pendientes de planificar. ID-03 "todo" cubierta por I-15.
- Working tree con fixes de tests sin commitear (test_source_picker.py, test_main_window.py).

## Features v1.5

### Hechas / validadas
- ✅ I-03 Detección de cámara ligada a ID de tarjeta/dispositivo — persistencia sd_cards/device_settings
- ✅ I-06 Reporte CSV de contenido de tarjeta — generate_card_content_report + generate_integrity_report
- ✅ I-11 Crear proyecto en un solo paso — wizard ampliado
- ✅ I-12 Arreglar "establecer como predeterminado"
- ✅ I-14 Forzar nombre de cámara al registrar origen
- ✅ I-15 Interruptor de contenido en volcado selectivo — quick 260821-f2k
- ✅ I-18 Filtrado de volcado por sesión — quick 260821-f2k (WiFi/FTP bloqueados a "Todo")
- ✅ I-19 Revisar temas claro/oscuro

### Pendientes v1.5 (Fase 1.5.0)
- 🔍 I-07 WiFi inbox: reanudar subidas interrumpidas + MD5 en móvil — Por revisar (solo `.part` atómico; sin reanudación ni MD5 en el móvil)
- Volcado selectivo multi-origen (ID-01) y escaneo MTP vía caché (ID-02) — sin planificar

### Reservado v2.0 (Fase 2.0)
- I-01 Acciones rápidas / modo guiado
- I-13 Pantalla de bienvenida

### Asignado v1.6.0 (Fase 1.6.0)
- Verificación avanzada XXH64 + ASC MHL (R-05)
- Reorganizar footage REQ-06 (R-06)

## Ideas abiertas importantes
- I-02 Destinos fallback/servidor
- I-04 Contenedores por tipo archivo
- I-05 Thumbnails en tabla ingesta
- I-08 Reglas configurables organización
- I-15 Interruptor contenido — ✅ quick 260821-f2k
- I-16 Config por defecto orígenes en proyecto
- I-17 Config orígenes en proyecto nuevo
- I-18 Filtrado volcado por sesión — ✅ quick 260821-f2k

## Bugs conocidos — CONCERNS.md

### Activos
- FFprobe timeout → metadata Unknown + file_size=0 — metadata_engine.py
- Watcher re-ingesta tras pruning >10k — watcher.py
- DB path depende de CWD cuando no frozen — db.py _resolve_db_path
- Doble hash MD5 por copia — ingestor.py
- Device polling en UI thread — main_window.py _auto_sync_check

### Bugs reportados por usuario 2026-08-20
- Bug 1: Proyecto en blanco + añadir QR → se añaden todos los QR ya creados. Posible sync_wifi_sessions crea sesiones para todos los senders.
- Bug 2: Wizard proyecto nuevo muestra opción modo delicado, irrelevante por proyecto, solo por dispositivo.
- Bug 3: Abrir intervalo de contenido de QR muestra opciones de volcar por días. Integración pobre I15/I18. — ✅ Resuelto (switcher por sesión; WiFi/FTP bloqueados a "Todo")
- Bug 4: Ruta maestra no visible en barra superior de la app — B-17. project_path_label con QSizePolicy.Ignored. — ✅ Resuelto (visible, max width 420)
- Bug 5: Al deseleccionar un origen, la sesión automática creada no desaparece. — ✅ Comportamiento intencional: borrar un origen conserva las sesiones (ui-layout-fixes #9)

### Técnicas resueltas recientemente
- rename_camera LIKE pattern
- _free_space retorna -1
- Camera detection race _cam_detection_token
- Duplicated device name MTP
- ThreadPoolExecutor shutdown
- chk_session_delicate eliminado

## Tech Debt crítica
- main_window.py god object ~4.131 líneas
- Migraciones DB inline sin versión
- Sin logging framework — 16 prints
- files.session_id TEXT vs sessions.id INTEGER
- QtString.arg reemplaza solo primera ocurrencia
- delicate_mode — ✅ activo por dispositivo (device_settings.delicate_mode)

## Backlog UI v2 — BACKLOG_UI_V2.md

### Prioridad Alta
- B-13 Menú conceptual dispositivo en "Ruta de origen" — ✅ Hecho (botones QR/FTP/MTP en columna Ruta)
- B-14 Modo delicado por dispositivo — ✅ Hecho (toggle zap/snail por fila)
- B-01 Volcado selectivo ubicación — ✅ Hecho
- B-02 Nombre origen en sesión — ✅ Hecho
- B-03 Visibilidad descripción proyecto — ✅ Hecho

### Prioridad Media
- B-08 Anillo focus visible — ✅ (QSS :focus)
- B-15 Generar proxies → configuración proyecto — ✅
- B-16 Etiqueta estado al pie — ✅
- B-17 Ruta maestra invisible header — ✅

### Prioridad Baja
- B-09 Tipografía jerarquía — ⏳
- B-10 Espaciado y superficies — ⏳
- B-11 Microinteracciones y botón primario — ✅ (io6 C9)
- B-12 Auditoría estética formal — ⏳
- B-18 Sesiones en contenedor — ✅ (QGroupBox)
- B-19 Botones edición origen derecha — ✅ (io6 C5)
- B-20 Eliminar dispositivos guardados — ⚠️ Parcial (borra sesiones/FTP; falta device_settings/sd_cards/caché)
- B-21 Limpiar panel configuración — ✅ (agrupado en QGroupBox)
- B-22 Reordenar botones Añadir origen — ✅ (Examinar/USB-MTP/WiFi QR/FTP)

## Seguridad
- FTP passwords e inbox tokens plaintext en DB
- ShootInboxServer 0.0.0.0, token en URL, sin TLS/rate limit
- Format via cmd con drive letter
- Updater descarga y ejecuta binarios con .sha256

## Performance
- Doble MD5 read
- UI-thread polling MTP/FTP
- ffprobe per-file batch
- FTP scan 64 workers
- Watcher os.walk completo
- MTP download sin chunking

## Quick tasks completados
- 260816-jlt SourcePickerDialog lanzador compacto
- 260816-k7i Corregir hallazgos UI-REVIEW
- 260816-mcj MTP manager COM por hilo + volcado selectivo
- 260816-x3b Glifos emoji → SVG vectoriales
- 260821-f2k Interruptor contenido por sesión (I-15/I-18)
- 260821-io6 Pulido layout (botones al borde, orden añadir origen, tema acento)
- 260821-nem Botón USB/MTP en columna ruta, deselección, reorden "Apagar al acabar"

## Archivos modificados sin commitear
tests/test_source_picker.py — fix mock SenderEditDialog (hang)
tests/test_main_window.py — fix índice combo del wizard (Manual=0)

## Próximos pasos sugeridos
1. Decidir I-07 WiFi resume + MD5 (solo `.part` atómico hoy)
2. Fase 1.5.0: planificar ID-01/ID-02 (multi-origen global + escaneo MTP vía caché); ID-04 borrado de caché
3. B-09/B-10/B-12 auditoría estética formal (resto de I-09)
4. B-20: ampliar "olvidar dispositivo" para limpiar device_settings/sd_cards/caché
5. Commit de fixes de tests

## Enlaces clave
.planning/STATE.md
.planning/IDEAS.md
.planning/ROADMAP.md
.planning/BACKLOG_UI_V2.md
.planning/codebase/CONCERNS.md
.planning/codebase/ARCHITECTURE.md
