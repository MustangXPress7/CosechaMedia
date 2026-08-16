# Ideas y Rutas Futuras

Documento vivo de ideas y rutas futuras para CosechaMedia. Las ideas que pasan a un plan concreto se mueven a su fase en ROADMAP.md y quedan referenciadas aquí.

**Convención de prioridades:**

- **[uso]** — Cambio crítico de usabilidad/flujo (bug-like): corrige una fricción que el operador encuentra en su trabajo diario. Se prioriza antes que funcionalidad nueva.
- **[nuevo feature]** — Funcionalidad nueva o ampliación de capacidades.

## Visión (cómo concibe el usuario la app)

CosechaMedia es la aplicación para **agilizar el proceso de volcar una SD o dispositivo en un PC para editar en él**:

- **Volcado selectivo** — para tarjetas "en sucio" con varias jornadas de trabajo: volcar solo un rango de fechas.
- **Proyectos** — cada proyecto tiene una **carpeta maestra** donde residen los volcados que se crean.
- **Sesiones** — dentro de un proyecto; cada sesión se convierte en un **backup/copia automática del footage** para ser enviado a otro disco duro o servidor que lo necesite.
- **Features de apoyo** — detección de cámara, personalización de carpetas/contenedores, modo delicado, configuración de proyecto (estructura de carpetas consistente), proxies, acciones post-ingesta.

## Principio rector

**Primero base sólida: que nada explote y sea consistente y compacto.** Los features y la estética vienen después de estabilizar y consolidar el núcleo.

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
| I-01 | **Acciones rápidas / modo guiado**: el usuario configura el proyecto una vez y las acciones rápidas automatizan todo el proceso — solo hay que conectar el dispositivo y aprobar el plan que propone la app | Ingesta | nuevo feature | Abierta — ruta bandera |
| I-02 | **Sesiones como réplica automática**: cada sesión puede enviarse automáticamente a otro disco duro o servidor como backup del footage | Sesiones/Archivo | nuevo feature | Abierta |
| I-03 | **Detección de cámara ligada a la ID de la tarjeta/dispositivo** — persistir el mapeo para no tener que introducir el nombre ni re-escanear cada vez | Detección | uso | Abierta |
| I-04 | **Contenedores/carpetas por tipo de archivo extraído** — dar cabida a datos giroscópicos, RAW, etc. | Archivo | nuevo feature | Abierta |
| I-05 | **Thumbnails / vista previa** en la tabla de ingesta | UI | nuevo feature | Abierta |
| I-06 | **Reporte de contenido de tarjeta (CSV)** — qué hay, fechas, tamaño, antes de volcar | Ingesta | nuevo feature | Abierta |
| I-07 | **WiFi inbox: reanudar subidas interrumpidas + verificación MD5 en el móvil** | WiFi | uso | Abierta — refuerza integridad |
| I-08 | **Reglas configurables de organización del archivo** más allá de `Footage/<Cámara>/<Fecha>` | Archivo | nuevo feature | Abierta |
| I-09 | **Estética / pulido visual** de la app | UI | nuevo feature | Abierta — baja prioridad (tras base sólida) |
| I-10 | **Base sólida del core**: resolver bugs conocidos y consolidar — carrera `_cam_done`, rename con `/`, validar el fix MTP en vivo | Core | uso | Abierta — PRIMERO |

## Rutas futuras (candidatas a fase)

| Ruta | Prioridad | Origen | Notas |
|------|-----------|--------|-------|
| R-01 | **Estabilización del core** (bugs conocidos + consistencia) | uso | I-10 — prerrequisito del resto |
| R-02 | **Acciones rápidas / modo guiado** | nuevo feature | I-01 — la ruta bandera que integra configuración de proyecto + volcado + acciones |
| R-03 | **Sesiones como réplica a otro disco/servidor** | nuevo feature | I-02 — conecta con la visión de sesión=backup |
| R-04 | Mejoras al volcado selectivo (MTP/caché, multi-origen) | — | Ya planeado en Fase 2 |
