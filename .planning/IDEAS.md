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

## En Fase 2 (planeado — ROADMAP.md)

Fase: **02 — Mejoras al volcado selectivo: multi-origen, escaneo MTP completo y opción todo** (depende de Fase 1)

| ID | Idea | Prioridad | Justificación |
|----|------|-----------|---------------|
| ID-04 | La caché MTP sigue **"viva"/disponible** aunque el dispositivo esté desconectado (permite consultar/filtrar por fecha sin tenerlo conectado), con opción de preguntar al usuario si quiere **eliminar esa caché** cuando el dispositivo al que referencia no está conectado | uso | Hoy la caché es inaccesible sin el dispositivo y no hay control sobre cuándo se descarta: riesgo de basura y de datos obsoletos |
| ID-01 | El volcado selectivo **global** (el que se lanza fuera del menú del dispositivo) incluye **todos los orígenes** añadidos en Orígenes; el volcado selectivo **per-device** (columna Contenido / menú del dispositivo) mantiene la selección uno a uno | nuevo feature | El caso global "quiero solo un rango de fechas pero de todo lo que hay enchufado" no es posible hoy: solo toma un origen |
| ID-02 | MTP: **escaneo completo de archivos** vía caché (device_cache) para poder ordenar/filtrar por fecha sin volcar todo | nuevo feature | El rango por fecha hoy depende del escaneo; con la caché se puede listar sin volcar. Pendiente de validar el método (ffprobe remoto vs. mtime del dispositivo) |
| ID-03 | Opción **"todo"** dentro del volcado selectivo para revertir la selección y volver a "volcar todo" | uso | Sin salida del filtro, el operador queda encerrado en el rango; es una fricción diaria |

## Ideas abiertas

| ID | Idea | Área | Prioridad | Estado |
|----|------|------|-----------|--------|
| I-01 | **Acciones rápidas / modo guiado**: el usuario configura el proyecto una vez y las acciones rápidas automatizan todo el proceso — solo hay que conectar el dispositivo y aprobar el plan que propone la app | Ingesta | nuevo feature | **v2.0** — reserva bandera |
| I-02 | **Destinos de envío del volcado**: un único volcado puede enviarse a infinidad de destinos (ya funciona hoy). A futuro: destinos de **"fallback"/servidor** — copia local + copia en nube, por si el proyecto se reasigna a otra persona | Sesiones/Archivo | nuevo feature | Abierta — base ya resuelta |
| I-03 | **Detección de cámara ligada a la ID de la tarjeta/dispositivo** — persistir el mapeo para no tener que introducir el nombre ni re-escanear cada vez | Detección | uso | **v1.5** |
| I-04 | **Contenedores/carpetas por tipo de archivo extraído** — dar cabida a datos giroscópicos, RAW, etc. | Archivo | nuevo feature | Abierta |
| I-05 | **Thumbnails / vista previa** en la tabla de ingesta | UI | nuevo feature | Abierta |
| I-06 | **Reporte de contenido de tarjeta (CSV)** — qué hay, fechas, tamaño, antes de volcar | Ingesta | nuevo feature | **v1.5** |
| I-07 | **WiFi inbox: reanudar subidas interrumpidas + verificación MD5 en el móvil** | WiFi | uso | **v1.5** — refuerza integridad |
| I-08 | **Reglas configurables de organización del archivo** más allá de `Footage/<Cámara>/<Fecha>` | Archivo | nuevo feature | Abierta |
| I-09 | **Estética / pulido visual** de la app | UI | nuevo feature | **v1.5** (B-09/B-10/B-11) |
| I-10 | **Base sólida del core**: resolver bugs conocidos y consolidar | Core | uso | **v1.5** — PRIMERO |
| I-11 | **Crear proyecto en un solo paso**: nombre + descripción + configuración a la vez, en una ventana suficientemente grande (sin wizard) | Proyectos | nuevo feature | **v1.5** |
| I-12 | **Arreglar "establecer como predeterminado"**: hoy no se aplica a todos los proyectos por crear | Proyectos | uso | ✅ Hecho |
| I-13 | **Pantalla de "bienvenido" al primer arranque**: seleccionar acciones rápidas sin trastear | Ingesta/UI | nuevo feature | **v2.0** — ligada a I-01 |
| I-14 | **Forzar nombre de cámara al registrar origen** | Detección/UX | uso | ✅ Implementado — `force_prompt=True` en `_assign_folder_source`; skipped si cámara conocida (I-03) |
| I-15 | **Interruptor de contenido en volcado selectivo**: switch para controlar si volcar todo el contenido, un intervalo de días, o X días desde el último volcado (ventana nueva). Reemplaza el calendario de selección por modo de filtro predefinido | Ingesta | nuevo feature | Abierta |
| I-16 | **Configuración por defecto de orígenes en el proyecto**: apartado en la configuración del proyecto para tocar modo rápido/delicado y tipo de volcado por defecto | Proyectos | nuevo feature | Abierta |
| I-17 | **Configuración de orígenes en proyecto nuevo**: al crear un nuevo proyecto, aparecer también la configuración de orígenes entrantes predefinidos | Proyectos | nuevo feature | Abierta |
| I-18 | **Filtrado de volcado por sesión**: decidir si el parámetro de volcado (modo todo/intervalo/ventana) lo controla la sesión o el origen, una vez que la sesión decide ese parámetro. Mover a sesiones y no ponerlo en orígenes. **Nota**: Para los modos WiFi y FTP, el modo de volcado queda bloqueado por la compatibilidad de su sistema y sería "todo" por defecto, ya que no admiten selección parcial de contenido. | Sesiones | nuevo feature | Por definir |
| I-19 | **Revisar aplicación de temas claro/oscuro en ventanas**: verificar que la transición y aplicación de temas oscuros y claros funcione correctamente en todas las ventanas y diálogos, especialmente después de cambios de configuración y en modo congelado (PyInstaller). Detectar posibles desajustes visuales, QSS no aplicados o fallback a valores por defecto. | UI | uso | Por definir |

## Rutas futuras (candidatas a fase)

| Ruta | Prioridad | Origen | Notas |
|------|-----------|--------|-------|
| R-01 | **Estabilización del core** (bugs conocidos + consistencia) | uso | I-10 — prerrequisito del resto. Alcance apuntado abajo |
| R-02 | **Acciones rápidas / modo guiado** | nuevo feature | I-01 + I-13 (pantalla de bienvenida = conclusión de la integración) |
| R-03 | **Destinos "fallback"/servidor para el volcado** (copia local + nube, p. ej. si el proyecto se reasigna) | nuevo feature | I-02 — la base (enviar un volcado a múltiples destinos) ya funciona hoy |
| R-04 | Mejoras al volcado selectivo (MTP/caché, multi-origen) | — | Ya planeado en Fase 2 |

### R-01 · Estabilización del core — alcance apuntado (solo notas, aún sin planificar)

Prerrequisito de I-01 (acciones rápidas). Piezas a considerar al definir la fase:

1. **Tests de regresión sobre la capa UI sin cubrir.** `MainWindow` es el god node nº 1 del gráfico graphify (`graphify-out/GRAPH_REPORT.md`): 144 aristas, betweenness 0.241, puente entre ~12 comunidades. Junto con los diálogos (SourcePickerDialog, SelectiveDumpAssistant, ProjectWizard, …), hoy no hay red de seguridad: cada quick task que toca la UI es un volado. Objetivo de fondo: poder tocar `main_window.py` sin miedo.
2. **Auditoría de concurrencia.** Evidencia directa: el bug MTP de hoy = COM cruzando hilos (`RPC_E_WRONG_THREAD`) con la excepción tragada. Superficie a inventariar: `ThreadPoolExecutor` de ingesta (4 hilos; 1 en modo delicado), `FileSystemWatcher` (daemon), QThread + `_StageWorker`/`_TaskWorker`, auto-sync (QTimer 5 s con throttle 60 s), COM inicializado por hilo (`_WpdSession`), locks (`_inflight_lock`, `_target_lock`). Riesgo alto: toca la integridad del volcado.
3. **Artefacto de integridad por sesión.** Ya existe verificación MD5 + estado de reanudación, pero no un reporte legible (hash, fechas, destino) que el operador pueda guardar o mandar. Germen de I-06 (CSV).
4. **Bugs conocidos a incluir:** carrera `_cam_done`, rename con `/` (documentados en `.planning/codebase/CONCERNS.md`). La validación del fix MTP en vivo queda fuera (requiere hardware del usuario).
5. **Recursos para definir la fase:** gráfico graphify (`graphify-out/` — 103 comunidades, hubs por zona) y docs `.planning/codebase/` (ARCHITECTURE.md, CONCERNS.md, TESTING.md, CONVENTIONS.md).

Quick tasks `uso` previas e independientes (no bloquean R-01): **I-12** (predeterminado), **I-03** (cámara ↔ ID de tarjeta/dispositivo).

(End of file - total 78 lines)