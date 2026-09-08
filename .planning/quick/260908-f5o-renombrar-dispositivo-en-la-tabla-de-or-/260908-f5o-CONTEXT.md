# Quick Task 260908-f5o: Renombrar dispositivo en la tabla de orígenes: persistir nombre en registro, popup de confirmación, combos universales en Añadir origen, detectar nombre ya conocido - Context

**Gathered:** 2026-09-08
**Status:** Ready for planning

<domain>
## Task Boundary

Renombrar un dispositivo en la tabla de orígenes actualmente solo actualiza la sesión (`db.update_session_config(nombre_dispositivo=...)` via `_prompt_rename_camera`). Debe persistir el nombre en el registro global (device_settings/known_devices/sd_cards). Además: popup de confirmación al renombrar, combos de nombres universales en Añadir origen, y detección de nombre ya conocido al añadir un origen.

</domain>

<decisions>
## Implementation Decisions

### Popup de confirmación al renombrar
- Al editar el nombre por doble clic (`_prompt_rename_camera`), mostrar popup que pregunte: "¿Guardar este nombre para futuras sesiones?" con opciones Sí / No / No volver a preguntar.
- "No volver a preguntar" debe persistirse (QSettings) para no repetir el diálogo.
- El rename debe persistir en el registro global (device_settings/known_devices/sd_cards) además de `update_session_config`.

### Semántica de combos universales en Añadir origen
- El combo ya lista todos los nombres conocidos via `db.list_known_camera_names()` (agrega sd_cards + device_settings + dispositivos) — mantener.
- Al añadir el origen, guardar el nombre elegido en el registro (device_settings) si no existe todavía ("Lista + guarda el elegido").

### Detección de nombre ya conocido
- Al añadir un origen, si el dispositivo/tarjeta ya tiene un nombre guardado distinto, mostrarlo como sugerencia en Añadir origen (etiqueta + opción de usar el conocido).
- Sin badge en la tabla (descartado).

### the agent's Discretion
- Mecánica exacta del diálogo de sugerencia (texto/botones) y del checkbox "no volver a preguntar".
- Qué helper de registro usar para persistir (procura reutilizar los existentes en db.py: `upsert_known_device`, `save_dispositivo`, `get_dispositivo_for_device`).

</decisions>

<specifics>
## Specific Ideas

- Bug precursor conocido: la ruta que sí persiste (`_on_camera_cell_edited` -> `_persist_camera_mapping`) solo se activa en modo manual de cámara; el doble clic (modo auto) no persiste.
- Existe fachada no-commiteada `app/core/device_registry.py`.

</specifics>

<canonical_refs>
## Canonical References

- Contexto previo: `.planning/quick/refactor-device-registry/` y `.planning/quick/revision-flujo-camara-addsource/`.

</canonical_refs>