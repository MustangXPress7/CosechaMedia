# Ideas y Rutas Futuras

Documento vivo de ideas y rutas futuras para CosechaMedia. Las ideas que pasan a un plan concreto se mueven a su fase en ROADMAP.md y quedan referenciadas aquí.

**Convención de prioridades:**

- **[uso]** — Cambio crítico de usabilidad/flujo (bug-like): corrige una fricción que el operador encuentra en su trabajo diario. Se prioriza antes que funcionalidad nueva.
- **[nuevo feature]** — Funcionalidad nueva o ampliación de capacidades.

## En Fase 2 (planeado — ROADMAP.md)

Fase: **02 — Mejoras al volcado selectivo: multi-origen, escaneo MTP completo y opción todo** (depende de Fase 1)

| ID | Idea | Prioridad | Justificación |
|----|------|-----------|---------------|
| ID-01 | El volcado selectivo **global** (el que se lanza fuera del menú del dispositivo) incluye **todos los orígenes** añadidos en Orígenes; el volcado selectivo **per-device** (columna Contenido / menú del dispositivo) mantiene la selección uno a uno | nuevo feature | El caso global "quiero solo un rango de fechas pero de todo lo que hay enchufado" no es posible hoy: solo toma un origen |
| ID-02 | MTP: **escaneo completo de archivos** vía caché (device_cache) para poder ordenar/filtrar por fecha sin volcar todo | nuevo feature | El rango por fecha hoy depende del escaneo; con la caché se puede listar sin volcar. Pendiente de validar el método (ffprobe remoto vs. mtime del dispositivo) |
| ID-03 | Opción **"todo"** dentro del volcado selectivo para revertir la selección y volver a "volcar todo" | uso | Sin salida del filtro, el operador queda encerrado en el rango; es una fricción diaria |

## Ideas abiertas (sesión de hoy)

| ID | Idea | Área | Prioridad | Estado |
|----|------|------|-----------|--------|
| | *(en blanco — se va rellenando en sesión)* | | | |

## Rutas futuras (candidatas a fase)

*(en blanco — se va rellenando en sesión)*
