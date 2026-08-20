# BOARD — Estado consolidado CosechaMedia

Última actualización: 2026-08-20 — Bugs 1-5 añadiados por usuario
Fuente: .planning/STATE.md, IDEAS.md, ROADMAP.md, BACKLOG_UI_V2.md, codebase/CONCERNS.md, PROJECT.md

## Core Value
Que el operador de cámara pueda vaciar tarjetas SD/cámaras/móviles al archivo del proyecto de forma fiable y sin perder datos — cada archivo copiado con verificación de integridad y organizado correctamente.

## Milestone actual
**v1.5 — Consolidación y bugs**
Fase: 00 Bugs conocidos + features v1.5 — STARTING
Última actividad: 2026-08-19 UI layout fixes + backlog auditado

## Resumen ejecutivo
- Fase 1 Auditoría UI completada 4/4 planes. Sin cambios de código.
- Fase 2 Mejoras volcado selectivo pendiente de planificar.
- 5 archivos modificados sin commitear: app/core/db.py, ingestor.py, shoot_inbox.py, app/ui/main_window.py, app/ui/selective_dump.py
- Múltiples scripts debug/fix sin versionar en root.

## Features v1.5

### Hechas / validadas
- ✅ I-06 Reporte CSV de contenido de tarjeta — generate_card_content_report + generate_integrity_report
- ✅ I-11 Crear proyecto en un solo paso — wizard ampliado
- ✅ I-12 Arreglar "establecer como predeterminado"
- ✅ I-14 Forzar nombre de cámara al registrar origen
- ✅ I-19 Revisar temas claro/oscuro

### Pendientes v1.5
- ⏳ I-03 Detección de cámara ligada a ID de tarjeta/dispositivo — uso
- 🔍 I-07 WiFi inbox: reanudar subidas interrumpidas + MD5 en móvil — Por revisar
- ❌ I-15 Interruptor de contenido en volcado selectivo — Pendiente, no completado
- ❌ I-18 Filtrado de volcado por sesión — Pendiente, no completado correctamente
- Fase 2: Volcado selectivo multi-origen, escaneo MTP vía caché, opción "todo"

### Reservado v2.0
- I-01 Acciones rápidas / modo guiado
- I-13 Pantalla de bienvenida

## Ideas abiertas importantes
- I-02 Destinos fallback/servidor
- I-04 Contenedores por tipo archivo
- I-05 Thumbnails en tabla ingesta
- I-08 Reglas configurables organización
- I-15 Interruptor contenido — pendiente
- I-16 Config por defecto orígenes en proyecto
- I-17 Config orígenes en proyecto nuevo
- I-18 Filtrado volcado por sesión — pendiente

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
- Bug 3: Abrir intervalo de contenido de QR muestra opciones de volcar por días. Integración pobre I15/I18.
- Bug 4: Ruta maestra no visible en barra superior de la app — B-17. project_path_label con QSizePolicy.Ignored.
- Bug 5: Al deseleccionar un origen, la sesión automática creada no desaparece.

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
- delicate_mode en sessions muerto

## Backlog UI v2 — BACKLOG_UI_V2.md

### Prioridad Alta
- B-13 Menú conceptual dispositivo en "Ruta de origen" — ⏳ Pendiente
- B-14 Modo delicado por dispositivo — ⏳ Pendiente
- B-01 Volcado selectivo ubicación — ✅ Hecho
- B-02 Nombre origen en sesión — ✅ Hecho
- B-03 Visibilidad descripción proyecto — ✅ Hecho

### Prioridad Media
- B-08 Anillo focus visible — ⏳
- B-15 Generar proxies → configuración proyecto — ⏳
- B-16 Etiqueta estado al pie — ⏳
- B-17 Ruta maestra invisible header — ⏳

### Prioridad Baja
- B-09 Tipografía jerarquía — ⏳
- B-10 Espaciado y superficies — ⏳
- B-11 Microinteracciones y botón primario — ⏳
- B-12 Auditoría estética formal — ⏳
- B-18 Sesiones en contenedor — ⏳
- B-19 Botones edición origen derecha — ⏳
- B-20 Eliminar dispositivos guardados — ⏳
- B-21 Limpiar panel configuración — ⏳
- B-22 Reordenar botones Añadir origen — ⏳

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

## Archivos modificados sin commitear
app/core/db.py
app/core/ingestor.py
app/core/shoot_inbox.py
app/ui/main_window.py
app/ui/selective_dump.py

## Próximos pasos sugeridos
1. Verificar I-07 WiFi resume + MD5
2. Implementar I-15 interruptor contenido
3. Re-diseñar I-18 filtrado por sesión
4. Cerrar B-13/B-14 UI alta prioridad
5. Commit de cambios actuales y limpiar scripts debug

## Enlaces clave
.planning/STATE.md
.planning/IDEAS.md
.planning/ROADMAP.md
.planning/BACKLOG_UI_V2.md
.planning/codebase/CONCERNS.md
.planning/codebase/ARCHITECTURE.md
