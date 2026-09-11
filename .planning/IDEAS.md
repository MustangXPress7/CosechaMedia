# Ideas y Rutas Futuras

Documento vivo de ideas y rutas futuras para CosechaMedia. Las ideas que pasan a un plan concreto se mueven a su fase en ROADMAP.md y quedan referenciadas aquí.

**Convención de prioridades:**

- **[uso]** — Cambio crítico de usabilidad/flujo (bug-like): corrige una fricción que el operador encuentra en su trabajo diario. Se prioriza antes que funcionalidad nueva.
- **[nuevo feature]** — Funcionalidad nueva o ampliación de capacidades.

## Visión (cómo concibe el usuario la app)

CosechaMedia es la aplicación para **agilizar el proceso de volcar una SD o dispositivo en un PC para editar en él**:

- **Volcado selectivo** — para tarjetas "en sucio" con varias jornadas de trabajo: volcar solo un rango de fechas.
- **Proyectos** — cada proyecto tiene una **carpeta maestra** donde residen los volcados que se crean.
- **Sesiones** — dentro de un proyecto; permiten enviar **un único volcado a infinidad de destinos** (esto ya funciona hoy). A futuro: destinos de **"fallback"/"servidor"** — una copia local y otra en nube, por si el proyecto se reasigna a otra persona.
- **Features de apoyo** — detección de cámara, personalización de carpetas/contenedores, modo delicado, configuración de proyecto (estructura de carpetas consistente), proxies, acciones post-ingesta.

## Principio rector

**Primero base sólida: que nada explote y sea consistente y compacto.** Los features y la estética vienen después de estabilizar y consolidar el núcleo.

**Adaptar al uso de cada usuario, sin que se vaya de madre.** El programa se amolda a cómo trabaja cada uno (destinos, estructura, flujos), pero sin sobre-ingeniería.

## En Fase 1.5.0 (planeado — ROADMAP.md)

Fase: **1.5.0 — Consolidación y bugs del flujo** (fase ligera: solo bugs activos de
CONCERNS.md resueltos por quick tasks). Los features del volcado selectivo listados abajo
(antigua Fase 2) pasan a **Fase 1.6.0** (decisión 2026-08-29); depende de Fase 1

| ID | Idea | Prioridad | Justificación |
|----|------|-----------|---------------|
| ID-04 | La caché MTP sigue **"viva"/disponible** aunque el dispositivo esté desconectado (permite consultar/filtrar por fecha sin tenerlo conectado), con opción de preguntar al usuario si quiere **eliminar esa caché** cuando el dispositivo al que referencia no está conectado | uso | Hoy la caché es inaccesible sin el dispositivo y no hay control sobre cuándo se descarta: riesgo de basura y de datos obsoletos |
| ID-01 | El volcado selectivo **global** (el que se lanza fuera del menú del dispositivo) incluye **todos los orígenes** añadidos en Orígenes; el volcado selectivo **per-device** (columna Contenido / menú del dispositivo) mantiene la selección uno a uno | nuevo feature | El caso global "quiero solo un rango de fechas pero de todo lo que hay enchufado" no es posible hoy: solo toma un origen |
| ID-02 | MTP: **escaneo completo de archivos** vía caché (device_cache) para poder ordenar/filtrar por fecha sin volcar todo | nuevo feature | El rango por fecha hoy depende del escaneo; con la caché se puede listar sin volcar. Pendiente de validar el método (ffprobe remoto vs. mtime del dispositivo) |
| ID-03 | Opción **"todo"** dentro del volcado selectivo para revertir la selección y volver a "volcar todo" | uso | Sin salida del filtro, el operador queda encerrado en el rango; es una fricción diaria |

**Verificación (2026-08-28):** ID-03 quedó cubierta por el modo "Todo" de I-15 (quick 260821-f2k). ID-04 está cubierta a medias: el origen de las sesiones MTP apunta a la caché local `data/device_cache/`, por lo que es usable para filtrar/volcar sin el dispositivo conectado si ya se escenificó, pero no hay navegación por alias ni opción explícita de "eliminar caché". ID-01 (volcado selectivo global multi-origen) y ID-02 (escaneo completo vía caché) siguen sin implementar.

**Reasignación (2026-08-29):** ID-01 e ID-02 (junto a ID-04) se planifican en la **Fase 1.6.0**; la Fase 1.5.0 queda acotada a los bugs activos de CONCERNS.md (fase ligera por quicks) y el I-07 queda como decisión de dashboard.

**Reasignación (2026-09-10):** ID-01 e ID-02 se mueven a la **Fase 1.7.0** (1.6.0 se cerró sin incluirlas; hoy planes 01.7.0-04 y 01.7.0-05). ID-04 (caché MTP viva) sigue pendiente de ubicar.

## Ideas abiertas

| ID | Idea | Área | Prioridad | Estado |
|----|------|------|-----------|--------|
| I-01 | **Acciones rápidas / modo guiado**: el usuario configura el proyecto una vez y las acciones rápidas automatizan todo el proceso — solo hay que conectar el dispositivo y aprobar el plan que propone la app | Ingesta | nuevo feature | **v2.0** — reserva bandera. Renombrado a **plantillas de proyecto** (Fase 1.8.0, plan 01.8.0-06); modo guiado se queda en 2.0 |
| I-02 | **Destinos de envío del volcado**: un único volcado puede enviarse a infinidad de destinos (ya funciona hoy). A futuro: destinos de **"fallback"/servidor** — copia local + copia en nube, por si el proyecto se reasigna a otra persona | Sesiones/Archivo | nuevo feature | **Fase 2.0** — base ya resuelta |
| I-03 | **Detección de cámara ligada a la ID de la tarjeta/dispositivo** — persistir el mapeo para no tener que introducir el nombre ni re-escanear cada vez | Detección | uso | ✅ Implementado — persistencia en `sd_cards` (serial) y `device_settings` (device_id) vía `_persist_camera_mapping` |
| I-04 | **Contenedores/carpetas por tipo de archivo extraído** — dar cabida a datos giroscópicos, RAW, etc. | Archivo | nuevo feature | **Fase 2.0** |
| I-05 | **Thumbnails / vista previa** en la tabla de ingesta | UI | nuevo feature | Abierta — alimenta I-23 (Fase 1.7.0) |
| I-06 | **Reporte de contenido de tarjeta (CSV)** — qué hay, fechas, tamaño, antes de volcar | Ingesta | nuevo feature | ✅ Implementado — `generate_card_content_report()` pre-dump + `generate_integrity_report()` post-dump cableado al UI |
| I-07 | **WiFi inbox: reanudar subidas interrumpidas + verificación MD5 en el móvil** | WiFi | uso | ⚠️ Parcial — solo escritura atómica `.part` sin reanudación (Range) ni MD5 en el móvil; por revisar (ver I-22 → Fase 1.7.0) |
| I-08 | **Reglas configurables de organización del archivo** más allá de `Footage/<Cámara>/<Fecha>` | Archivo | nuevo feature | Abierta — conecta con plantillas de proyecto (01.8.0-06) |
| I-09 | **Estética / pulido visual** de la app | UI | nuevo feature | ⚠️ Parcial — B-11 hecho (io6 C9); B-09/B-10 pendientes → **Fase 1.7.0** (01.7.0-01 pulido visual) |
| I-10 | **Base sólida del core**: resolver bugs conocidos y consolidar | Core | uso | **v1.5** — PRIMERO |
| I-11 | **Crear proyecto en un solo paso**: nombre + descripción + configuración a la vez, en una ventana suficientemente grande (sin wizard) | Proyectos | nuevo feature | ✅ Implementado — wizard ampliado con detección cámara, proxies, modo delicado |
| I-12 | **Arreglar "establecer como predeterminado"**: hoy no se aplica a todos los proyectos por crear | Proyectos | uso | ✅ Hecho |
| I-13 | **Pantalla de bienvenida** al primer arranque: proyectos recientes, crear nuevo (con selector de plantilla) y opción "no volver a mostrar" | Ingesta/UI | nuevo feature | **v1.8.0** — reubicada desde 1.7.0 (plan 01.8.0-07); integrada con plantillas |
| I-14 | **Forzar nombre de cámara al registrar origen** | Detección/UX | uso | ✅ Implementado — `force_prompt=True` en `_assign_folder_source`; skipped si cámara conocida (I-03) |
| I-15 | **Interruptor de contenido en volcado selectivo**: switch para controlar si volcar todo el contenido, un intervalo de días, o X días desde el último volcado (ventana nueva). Reemplaza el calendario de selección por modo de filtro predefinido | Ingesta | nuevo feature | ✅ Implementado — quick 260821-f2k: switch cíclico por sesión (Todo → Intervalo → Últimos N días) |
| I-16 | **Configuración por defecto de orígenes en el proyecto**: apartado en la configuración del proyecto para tocar modo rápido/delicado y tipo de volcado por defecto | Proyectos | nuevo feature | **Fase 1.8.0** — con plan 01.8.0-08 (configuración de orígenes en proyecto) |
| I-17 | **Configuración de orígenes en proyecto nuevo**: al crear un nuevo proyecto, aparecer también la configuración de orígenes entrantes predefinidos | Proyectos | nuevo feature | **Fase 1.8.0** — plan 01.8.0-08 (ProjectWizard pre-adición de orígenes) |
| I-18 | **Filtrado de volcado por sesión**: decidir si el parámetro de volcado (modo todo/intervalo/ventana) lo controla la sesión o el origen, una vez que la sesión decide ese parámetro. Mover a sesiones y no ponerlo en orígenes. **Nota**: Para los modos WiFi y FTP, el modo de volcado queda bloqueado por la compatibilidad de su sistema y sería "todo" por defecto, ya que no admiten selección parcial de contenido. | Sesiones | nuevo feature | ✅ Implementado — quick 260821-f2k: control solo en Sesiones, WiFi/FTP bloqueados a "Todo", columna Contenido → Opciones |
| I-19 | **Revisar aplicación de temas claro/oscuro en ventanas**: verificar que la transición y aplicación de temas oscuros y claros funcione correctamente en todas las ventanas y diálogos, especialmente después de cambios de configuración y en modo congelado (PyInstaller). Detectar posibles desajustes visuales, QSS no aplicados o fallback a valores por defecto. | UI | uso | ✅ Revisado — QSS template completo (600+ líneas), 64 inline styles usan theme.color(), refresh correcto en theme switch |
| I-20 | **Motor de copia más rápido**: el argumento estrella de OffShoot es la velocidad. Hoy la ingesta va con `shutil` + MD5 streaming. Explorar buffers grandes, copia nativa del SO (buffered async / `CopyFileEx` en Windows, `sendfile`/`fclone` en POSIX), y paralelismo multi-destino real. Benchmark público tarjeta→lector para poder comparar y vender el dato | Core | nuevo feature | **Fase 1.7.0** — plan 01.7.0-07 |
| I-21 | **Menú contextual "Copiar a CosechaMedia…"** (Explorer/Finder): clic derecho sobre una carpeta/tarjeta → motor de copia verificado sin abrir la app. Integración de registro/entorno tipo la de OffShoot | Ingesta/UX | nuevo feature | **Fase 2.0** — ver sección OffShoot |
| I-22 | **Stop & Resume + detección de duplicados robusta**: mejora del resume actual (`.sdimport_session_<id>.json`) para que reanude en cualquier punto aunque haya nombres idénticos, con duplicado por tamaño/hash, no solo por ruta | Core | uso | **Fase 1.7.0** — plan 01.7.0-08; complementa I-07 |
| I-23 | **Reportes presentables con marca**: evolución de los CSV actuales a informe HTML/PDF con logo, título, notas y miniatura por clip (I-05), listo para entregar al DIT/cliente al cierre de jornada | Ingesta | nuevo feature | **Fase 1.7.0** — plan 01.7.0-06 |
| I-24 | **Scripts/webhooks post-ingesta**: disparar un script o webhook (Slack/Discord/Telegram local) al terminar cada ingesta, además del notificador SMTP/Telegram de 1.8.0. Es el "Connect" de OffShoot pero sin nube | Ingesta | nuevo feature | **Fase 2.0** |
| I-25 | **Health check del soporte**: al detectar una SD (y antes de formatear), validar salud/estado (lectura, SMART de tarjetas si aplica, aviso de tarjeta degradada). OffShoot valida OWC/ProGrade; `SDReader` ya lee marca/serial — dar el paso a verificación de integridad del propio soporte | Detección | uso | **Fase 2.0** — ver sección OffShoot |

## Plantillas de proyecto (Fase 1.8.0 — plan 01.8.0-06)

Las plantillas pre-configuran un proyecto completo (organización, proxies, sesión por defecto, acciones post-ingesta) para que el operador solo tenga que darle nombre y empezar. Sustituyen la terminología "acciones rápidas" (I-01) y se integran con la ventana de bienvenida (I-13) y el wizard de creación.

### Configuración que almacena cada plantilla

```json
{
  "name": "Plantilla",
  "organization_type": 0,
  "date_mode": 0,
  "proxy_enabled": true,
  "proxy_quality": "1080p",
  "session_dump_mode": "window",
  "session_window_days": 7,
  "session_window_unit": "days",
  "post_actions": {"csv_card": true, "csv_integrity": true, "proxies": false, "format": false, "shutdown": false},
  "allowed_sources": ["sd", "wifi", "ftp", "mtp"],
  "camera_detection": "auto"
}
```

`organization_type`: 0=Cámara/Fecha, 1=Fecha/Cámara, 2=Solo cámara, 3=Sin subcarpetas
`date_mode`: 0=Automática (ffprobe), 1=Manual
`session_dump_mode`: "all" (volcar todo), "interval" (intervalo de fechas), "window" (últimos N días/semanas/meses)

### Plantillas predefinidas

| # | Plantilla | Org | Proxies | Sesión por defecto | Post-ingesta | Orígenes típicos | Uso |
|---|-----------|-----|---------|--------------------|--------------|------------------|-----|
| 1 | **Documentary / Reportaje** | Fecha/Cámara (1) | 1080p | ventana 7 días | CSV card + integridad | SD + WiFi (entrevistas móvil) | Rodajes largos, varias jornadas, material de archivo |
| 2 | **Fiction / Ficción** | Cámara/Fecha (0) | 720p | ventana 1 día | integridad | SD (ARRI, Sony, RED) | Cine, serie, telefilm — múltiples cámaras por jornada |
| 3 | **Commercial / Publicidad** | Cámara/Fecha (0) | 1080p | todo | CSV card | SD | Spot, contenido corto, rápido turnaround |
| 4 | **Wedding / Evento** | Fecha/Cámara (1) | 1080p | todo | CSV card + integridad | SD + WiFi (invitados) | Boda, gala, evento de un día |
| 5 | **Corporate / Conferencia** | Fecha/Cámara (1) | 1080p | todo | CSV card | SD + WiFi | Presentación, conferencia, formación |
| 6 | **Fast / Urgente** | Sin subcarpetas (3) | desactivado | todo | nada | SD | Noticias, breaking news, volcado rápido sin organización |
| 7 | **Custom / Personalizado** | libre | libre | libre | libre | libre | El usuario configura todo desde el wizard (estado actual) |

### Notas de diseño

- La plantilla **Custom** es el comportamiento actual del wizard: todo configurable, sin preselección.
- Las plantillas **no tocan `app/core/`** — solo pre-rellenan los campos del `ProjectWizard` existente.
- Si el operador modifica algo al crear el proyecto, se sobreescribe (la plantilla es un punto de partida, no una restricción).
- La plantilla se guarda como archivo `.json` en `data/templates/` (junto a la DB).
- Se pueden crear plantillas nuevas duplicando una predefinida y editándola (NamesManagerDialog reutilizable).
- La ventana de bienvenida (I-13, plan 01.8.0-07) muestra: proyecto reciente / crear nuevo (con selector de plantilla) / "no volver a mostrar".

### Alternativas consideradas

- **Plantillas por dispositivo (no por proyecto):** crear una plantilla para "Sony A7IV" que siempre usa las mismas opciones. Rechazado: la organización depende del tipo de rodaje, no del hardware.
- **Plantillas que restringen opciones:** impedir que el operador cambie la organización. Rechazado: la plantilla es un punto de partida; el operador siempre es libre.

## Análisis de competencia: OffShoot (Hedge)

Análisis 2026-09-10 de [OffShoot](https://hedge.co/products/offshoot) (ex-Hedge), DIT tool de referencia de Hedge: $169/$249, macOS/Windows, 10 días de prueba.

### Dónde CosechaMedia gana

| Ventaja | Detalle |
|---------|---------|
| **Ingesta desde móviles/cámaras** | OffShoot solo copia discos/tarjetas ya montados. CosechaMedia ingiere por USB (MTP), WiFi QR (PairDrop, sin instalar nada) y FTP — únicos en el nicho |
| **Modelo proyecto/sesión** | OffShoot es un motor de transferencia sin estado; CosechaMedia gestiona proyectos con sesiones, volcado selectivo por jornada, organización `Footage/<Cámara>/<Fecha>` y reorganizador de material descolocado |
| **Libre/open source + Linux** | GPL-3.0, multiplataforma (incluye Linux) frente a pago y solo macOS/Windows |
| **Proxies y detección integrados** | Generación de proxies 720/1080p y detección de cámara vía ffprobe dentro del mismo flujo; OffShoot deriva a EditReady y FoolCat (pago aparte) |
| **Sin nube, privacidad** | CosechaMedia es local-only; OffShoot empuja S3/iconik/Connect. En rodaje local es una ventaja |

### Carencias de CosechaMedia donde OffShoot gana (→ features propuestos)

| Carencia | OffShoot | Feature propuesto |
|----------|----------|-------------------|
| Velocidad de copia | Motor de copia "blazing speed", el argumento estrella | **I-20** — buffers grandes, copia nativa SO (`CopyFileEx`/`sendfile`), paralelismo multi-destino, benchmark público |
| Acceso sin abrir la app | Clic derecho → motor de copia (Finder/Explorer) | **I-21** — menú contextual "Copiar a CosechaMedia…" |
| Resume a prueba de duplicados | Stop & Resume + Duplicate Detection por tamaño/hash | **I-22** — resume robusto con duplicados por hash, no solo ruta |
| Reportes para entregar | Reports con logo, notas, miniaturas | **I-23** + I-05 — informe HTML/PDF con marca |
| Verificación diferida | Media Hash Lists + re-verificación posterior | **R-05 / Fase 1.7.0** — XXH64 + ASC MHL |
| Automatización | Connect (push, webhooks), presets, API y scripting | **I-24 (Fase 2.0)** + notificadores SMTP/Telegram (Fase 1.8.0) — scripts/webhooks post-ingesta sin nube |
| Salud del soporte | Health check OWC/ProGrade antes de volcar | **I-25** — validación de estado de la SD (SDReader ya lee marca/serial) |
| Presets compartibles y avisos varios | Presets online, presets Builder, Helper de menú | Plantillas de proyecto (1.8.0) + import/export JSON (ya en DeviceRegistry) |

### Posicionamiento recomendado

No competir en su terreno (velocidad + ecosistema DIT maduro), sino en el propio: **un operador que llega con una SD, un móvil o una cámara y necesita archivar un rodaje completo sin darse de alta en nada**. Ahí se gana por producto y por precio. De vuelta a casa, reportes presentables (I-23), velocidad de copia (I-20) y resume robusto (I-22) se planifican en **1.7.0** junto al pulido visual y la verificación avanzada: son los saltos que más cierran la brecha percibida.

## Rutas futuras (candidatas a fase)

| Ruta | Prioridad | Origen | Notas |
|------|-----------|--------|-------|
| R-01 | **Estabilización del core** (bugs conocidos + consistencia) | uso | I-10 — prerrequisito del resto. Alcance apuntado abajo. **Fase 1.5.0** |
| R-02 | **Modo guiado** | nuevo feature | I-01 (modo guiado) — las plantillas de proyecto (01.8.0-06) y la ventana de bienvenida (01.8.0-07) ya se implementan en **Fase 1.8.0**; el modo guiado se queda en **Fase 2.0** como integración final |
| R-03 | **Destinos "fallback"/servidor para el volcado** (copia local + nube, p. ej. si el proyecto se reasigna) | nuevo feature | I-02 — la base (enviar un volcado a múltiples destinos) ya funciona hoy. **Fase 2.0** |
| R-04 | Mejoras al volcado selectivo (MTP/caché, multi-origen) | — | **Fase 1.7.0** (ID-01/ID-02; ID-04 pendiente) |
| R-05 | **Verificación avanzada: XXH64 + ASC MHL** | nuevo feature | Diseño D1-D5 en `.planning/notes/diseno-xxh64-asc-mhl.md`. **Fase 1.7.0** — plan 01.7.0-03 |
| R-06 | **Reorganizar footage** (reconstrucción de volcados a mano) | uso | REQ-06 — definido en require. Integrado como acción de la app con diálogo propio. **Fase 1.6.0**; mejoras de interfaz/funciones en la **Fase 1.8.0** (01.8.0-05) |

### R-01 · Estabilización del core — alcance apuntado (solo notas, aún sin planificar)

Prerrequisito de I-01 (acciones rápidas). Piezas a considerar al definir la fase:

1. **Tests de regresión sobre la capa UI sin cubrir.** `MainWindow` es el god node nº 1 del gráfico graphify (`graphify-out/GRAPH_REPORT.md`): 144 aristas, betweenness 0.241, puente entre ~12 comunidades. Junto con los diálogos (SourcePickerDialog, SelectiveDumpAssistant, ProjectWizard, …), hoy no hay red de seguridad: cada quick task que toca la UI es un volado. Objetivo de fondo: poder tocar `main_window.py` sin miedo.
2. **Auditoría de concurrencia.** Evidencia directa: el bug MTP de hoy = COM cruzando hilos (`RPC_E_WRONG_THREAD`) con la excepción tragada. Superficie a inventariar: `ThreadPoolExecutor` de ingesta (4 hilos; 1 en modo delicado), `FileSystemWatcher` (daemon), QThread + `_StageWorker`/`_TaskWorker`, auto-sync (QTimer 5 s con throttle 60 s), COM inicializado por hilo (`_WpdSession`), locks (`_inflight_lock`, `_target_lock`). Riesgo alto: toca la integridad del volcado.
3. **Artefacto de integridad por sesión.** Ya existe verificación MD5 + estado de reanudación, pero no un reporte legible (hash, fechas, destino) que el operador pueda guardar o mandar. Germen de I-06 (CSV).
4. **Bugs conocidos a incluir:** carrera `_cam_done`, rename con `/` (documentados en `.planning/codebase/CONCERNS.md`). La validación del fix MTP en vivo queda fuera (requiere hardware del usuario).
5. **Recursos para definir la fase:** gráfico graphify (`graphify-out/` — 103 comunidades, hubs por zona) y docs `.planning/codebase/` (ARCHITECTURE.md, CONCERNS.md, TESTING.md, CONVENTIONS.md).

Quick tasks `uso` previas e independientes (no bloquean R-01): **I-12** (predeterminado), **I-03** (cámara ↔ ID de tarjeta/dispositivo).

(End of file - total 78 lines)