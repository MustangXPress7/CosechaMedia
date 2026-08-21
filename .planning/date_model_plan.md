# Plan de fechas simplificado

## Objetivo
Simplificar la lógica de fechas y eliminar la confusión de duración Un solo día / Múltiples días / Sin fecha.

## Modelo
- `date_mode` enum: `auto` | `manual`
  - `auto`: fecha por archivo desde metadatos ffprobe, fallback mtime.
  - `manual`: fecha única `manual_date` para toda la sesión/proyecto.
- Sin modo `none`. La ausencia de fecha se obtiene por organización `Solo cámara` o `Sin subcarpetas`.
- Overrides por cámara a nivel proyecto: `camera_date_overrides` JSON {camera_name: YYYY-MM-DD}
- Offset por cámara/sesión opcional: anclar un archivo a fecha correcta y aplicar delta constante a todos los archivos de esa cámara en la sesión.

## Prioridad de resolución de fecha
1. Si organización no incluye fecha → ruta sin fecha.
2. Override por cámara → fecha del override.
3. `date_mode == manual` → `manual_date` sesión o proyecto.
4. `date_mode == auto` → fecha de metadato, fallback mtime.

## Cambios DB
projects:
- date_mode TEXT DEFAULT 'auto'
- manual_date TEXT
- camera_date_overrides TEXT DEFAULT '{}'

sessions:
- date_mode TEXT
- manual_date TEXT

## UI
Configuración de proyecto:
- Modo de fechas: Automática / Manual
- Si Manual → selector Fecha
- Tabla Overrides por cámara: Cámara | Fecha | Eliminar
- Detección de cámara ya integrada.

## Ingestor
Refactorizar `_determine_date(metadata, camera_name)` para aplicar prioridad anterior.

## Próximos pasos
1. Migración DB
2. Actualizar _load_project / _save
3. Refactorizar UI configuración
4. Actualizar Ingestor
5. Tests
