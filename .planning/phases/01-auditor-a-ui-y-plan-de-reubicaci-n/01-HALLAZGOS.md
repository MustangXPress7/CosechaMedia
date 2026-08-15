# Fase 1: Informe de Hallazgos de UI

**Elaborado:** 2026-08-15
**Estado:** draft

## Resumen ejecutivo

La auditoría cubre las **4 zonas** (A — ventana principal/dashboard, B — pickers de fuente, C — asistentes y paneles, D — acciones post-ingesta) y los **4 flujos del operador** (conectar → ingestar → formatear → reorganizar, D-01). Todos los hallazgos se anclan a código leído (`app/ui/*.py:<línea>`) y a las capturas del plan 01 (`captures/*.png`, 8/8 generadas, leyenda en `01-INVENTARIO.md:174-189`).

**Hallazgos priorizados (7):**

| ID | Hallazgo | Zona·Flujo | Severidad |
|----|----------|------------|-----------|
| H-01 | Zona post-ingesta desordenada y secundaria (D-07) | D·f/r | Alta |
| H-02 | Panel de sesiones crece a la derecha y come ancho (D-08) | A·i | Alta |
| H-03 | Botones de eliminar genéricos y mal ubicados (D-09) | A·c/i/g | Media |
| H-04 | Descripción del proyecto capturada pero nunca mostrada — dato muerto (D-10) | C·c | Media |
| H-05 | Columnas de `source_list` de ancho fijo (D-11) | A·c | Baja |
| H-06 | Duplicado "guardar dispositivos": dos flujos de origen separados (D-12) | A·c + B·c | Alta |
| H-07 | Volcado selectivo (modo dump) sin entrada visible; menú contextual con una sola acción | D·r | Media |

Los hallazgos **H-01, H-02 y H-06** son los de mayor impacto: tocan el cierre del ciclo del operador (post-ingesta), el ancho de ventana (sesiones) y un flujo duplicado percibido como el mismo (orígenes, decisión `costly` D-12). **H-04** convierte un dato capturado en información visible (regla no esconder nada, D-03). **H-07** es un hallazgo nuevo de esta revisión: `_open_selective_dump` (`app/ui/main_window.py:3671-3687`) está definido pero **nunca se conecta a ningún control**; el menú contextual de `table` solo expone "Eliminar completados" (`app/ui/main_window.py:1882-1886`).

**Cobertura:** las 4 zonas tienen hallazgos, por lo que la copy de estado vacío (UI-02 empty-informe, `01-UI-SPEC.md:102-103`: "Zona sin hallazgos" / "Ningún control de esta zona requiere reubicación. Se mantiene la ubicación actual.") **no aplica**; si alguna zona hubiera quedado sin hallazgos, se habría declarado explícitamente con esa copy junto al método y la evidencia que la respaldan, nunca como documento vacío. El cierre de cobertura es la sección §6 Conservación: **121 filas de inventario** (43 A + 32 B + 38 C + 8 D), cada una en §4 (hallazgo que la implica) o en §6 ("conservado").

Evidencia consolidada: inventario `01-INVENTARIO.md` (filas con `archivo:línea` verificadas) + capturas `captures/zona{A,B,C,D}_{estado-inicial,configurado}.png` (enlazadas en cada hallazgo). El próximo paso es el plan 03, que puntuará estos hallazgos con la fórmula D-06 y producirá `01-PLAN-REUBICACION.md`.

## Método

- **Heurísticas (D-05, definición operativa `01-UI-SPEC.md:236-244`):** cada hallazgo se justifica con heurísticas explícitas — **frecuencia de uso** (5 = cada ciclo; 3 = una vez por jornada; 1 = rara vez), **consistencia** entre diálogos, **contexto de acción** (¿el control está donde está la atención del operador en ese momento del flujo? Sí/Parcial/No), **descubribilidad** (0 = visible directo … 3 = oculto/colapsado) y **distancia de ratón** desde el punto focal primario (`btn_start`/barra de progreso, normalizada 1-5). Nada se marca como problema sin criterio.
- **Matriz de priorización (D-06, `01-UI-SPEC.md:246-252`):** `Score = Impacto − (Esfuerzo + Riesgo)/2`, bandas P1 ≥ 2.5 / P2 1.0–2.4 / P3 < 1.0. **Este informe solo identifica los factores por hallazgo** (impacto, esfuerzo, riesgo: tests/i18n/estética); la puntuación y el orden son del plan 03.
- **Evidencia (D-04):** lectura de widgets (grep por atributo público `self\.<attr> = Q…` + verificación del rango citado) combinada con inspección visual (capturas offscreen del plan 01). Las citas usan `app/ui/<módulo>.py:<inicio>-<fin>` en backticks, con el atributo público entre paréntesis cuando aplica.
- **Regla de evidencia:** cada hallazgo exige cita de código o captura. Si una afirmación no es verificable en esta fase, se usa la copy literal `01-UI-SPEC.md:104`: "Evidencia no verificable — registrar el motivo en la columna Evidencia y volver a capturar en la fase de ejecución." (usada en H-07 para la evidencia visual del menú contextual, que no se capturó en el plan 01).
- **Regla transversal (D-03):** no esconder nada — ninguna propuesta oculta, elimina ni colapsa un control; todo control del inventario queda accesible y descubrible en el estado objetivo. La conservación se verifica en §6.
- **Backstop de texto largo (UI-02 long-text):** opción usada — **resumen en celda + detalle en párrafo tras la tabla** (las tablas usan ≤5 columnas con celdas abreviadas y leyenda; el contexto largo de cada hallazgo se narra completo en su bloque, sin truncar).

## Mapa zonas ↔ flujos

| Zona | Flujos que toca | Controles implicados | Hallazgos |
|------|-----------------|----------------------|-----------|
| A — Ventana principal / dashboard | c, i, r | A-06, A-15..A-19, A-23, A-25..A-32 | H-02, H-03, H-05, H-06 |
| B — Pickers de fuente | c | B-01..B-32 | H-06 |
| C — Asistentes y paneles | c, r | C-03 | H-04 |
| D — Acciones post-ingesta | f, r | D-01..D-08 | H-01, H-07 |

**Leyenda:** Z·f — zona (A/B/C/D) · flujo (c=conectar, i=ingestar, f=formatear, r=reorganizar). El detalle por control (estado en el informe) está en §4 y §6.
## Hallazgos por flujo

Los hallazgos se agrupan por flujo del operador (D-01: conectar → ingestar → formatear → reorganizar) y por zona (A-D). Cada fila de tabla = un control del inventario implicado por el hallazgo (una fila de datos por control, mismo H-NN cuando el hallazgo toca N controles). Los bloques tras cada tabla narran el detalle completo del hallazgo (backstop long-text: resumen en celda + detalle en párrafo, `01-UI-SPEC.md:269`).

**Flujo conectar (c) — Tabla de implicados:**

| ID | Control (attr) | Zona·Flujo | Ubicación actual | Hallazgo |
|----|----------------|------------|------------------|----------|
| H-04 | C-03 `desc_input` | C·c | `app/ui/project_wizard.py:41-46` | H-04 |
| H-05 | A-19 `source_list` | A·c | `app/ui/main_window.py:400-405` | H-05 |
| H-06 | A-16 `source_input` | A·c | `app/ui/main_window.py:378-382` | H-06 |
| H-06 | A-17 `btn_browse_source` | A·c | `app/ui/main_window.py:384-386` | H-06 |
| H-06 | A-18 `btn_receive_wifi` | A·c | `app/ui/main_window.py:388-392` | H-06 |
| H-06 | B-01 `SourcePickerDialog` | B·c | `app/ui/source_picker.py:18,33-35` | H-06 |
| H-06 | B-02 `hint` | B·c | `app/ui/source_picker.py:42-45` | H-06 |
| H-06 | B-03 `list_widget` | B·c | `app/ui/source_picker.py:47-54,70-78` | H-06 |
| H-06 | B-04 `browse_btn` | B·c | `app/ui/source_picker.py:57-59` | H-06 |
| H-06 | B-05 botonera | B·c | `app/ui/source_picker.py:61-67` | H-06 |
| H-06 | B-06 `DevicePickerDialog` | B·c | `app/ui/device_picker.py:16,34` | H-06 |
| H-06 | B-07 `device_combo` | B·c | `app/ui/device_picker.py:54-58` | H-06 |
| H-06 | B-08 `refresh_btn` | B·c | `app/ui/device_picker.py:59-61` | H-06 |
| H-06 | B-09 `tree` | B·c | `app/ui/device_picker.py:64,70` | H-06 |
| H-06 | B-10 `selection_label` | B·c | `app/ui/device_picker.py:72-76` | H-06 |
| H-06 | B-11 `ok_btn` | B·c | `app/ui/device_picker.py:79-82` | H-06 |
| H-06 | B-12 `FtpPickerDialog` | B·c | `app/ui/ftp_picker.py:53,71` | H-06 |
| H-06 | B-13 `profile_combo` | B·c | `app/ui/ftp_picker.py:93-97,189-192` | H-06 |
| H-06 | B-14 `name_edit` | B·c | `app/ui/ftp_picker.py:102` | H-06 |
| H-06 | B-15 `host_edit` | B·c | `app/ui/ftp_picker.py:105-107` | H-06 |
| H-06 | B-16 `detect_btn` | B·c | `app/ui/ftp_picker.py:108-111` | H-06 |
| H-06 | B-17 `port_spin` | B·c | `app/ui/ftp_picker.py:113` | H-06 |
| H-06 | B-18 `user_edit` | B·c | `app/ui/ftp_picker.py:117` | H-06 |
| H-06 | B-19 `pass_edit` | B·c | `app/ui/ftp_picker.py:119` | H-06 |
| H-06 | B-20 `base_edit` | B·c | `app/ui/ftp_picker.py:122` | H-06 |
| H-06 | B-21 `passive_check` | B·c | `app/ui/ftp_picker.py:125` | H-06 |
| H-06 | B-22 `connect_btn` | B·c | `app/ui/ftp_picker.py:131-134` | H-06 |
| H-06 | B-23 `conn_status` | B·c | `app/ui/ftp_picker.py:135-138` | H-06 |
| H-06 | B-24 `tree` | B·c | `app/ui/ftp_picker.py:141-147` | H-06 |
| H-06 | B-25 `guide_btn` | B·c | `app/ui/ftp_picker.py:149-153` | H-06 |
| H-06 | B-26 `guide_text` | B·c | `app/ui/ftp_picker.py:154-161` | H-06 |
| H-06 | B-27 `selection_label` | B·c | `app/ui/ftp_picker.py:163-166` | H-06 |
| H-06 | B-28 `ok_btn` | B·c | `app/ui/ftp_picker.py:169-172` | H-06 |
| H-06 | B-29 `WifiMethodDialog` | B·c | `app/ui/wifi_picker.py:13,22-24` | H-06 |
| H-06 | B-30 `hint` | B·c | `app/ui/wifi_picker.py:31-33` | H-06 |
| H-06 | B-31 `btn_pairdrop` | B·c | `app/ui/wifi_picker.py:35-42,59-66` | H-06 |
| H-06 | B-32 `btn_ftp` | B·c | `app/ui/wifi_picker.py:44-50,59-66` | H-06 |

**H-04 — Descripción del proyecto nunca mostrada (D-10):**
- Zona·Flujo: C·c. Control: `desc_input` (grupo "Descripción (Opcional)", placeholder "Breve descripción del proyecto...").
- Ubicación actual: `app/ui/project_wizard.py:41-46` — capturada en `ProjectWizard`; se guarda en BD al crear (INSERT en `app/ui/main_window.py:1191,3647`, SELECT en `:1313`, copia en duplicado `:1335-1339`).
- Problema: el wizard captura la descripción pero **ninguna vista posterior la muestra** (grep en `app/ui/` solo encuentra los puntos de guardado/lectura de BD, nunca un label del dashboard) — dato muerto.
- Heurísticas violadas: descubribilidad (el dato existe, 3 = oculto); contexto de acción (el operador busca el proyecto por su descripción en el dashboard).
- Propuesta de reubicación: línea de info del proyecto bajo la header bar (o tooltip del `project_combo`): "Descripción del proyecto: <texto>" truncada con ellipsis + tooltip completo (target `01-UI-SPEC.md:129`).
- Justificación de usabilidad: convertir un dato capturado en información visible; regla no esconder nada (D-03).
- Impacto: información del proyecto inaccesible; la descripción capturada no aporta valor.
- Evidencia: inventario fila C-03 + captura `captures/zonaC_configurado.png` (formulario con descripción llena) — ninguna captura posterior la muestra.
- Severidad: Media.

**H-05 — Columnas de `source_list` de ancho fijo (D-11):**
- Zona·Flujo: A·c. Control: `source_list` (columnas "Ruta de origen"/"Cámara"/"Contenido").
- Ubicación actual: `app/ui/main_window.py:400-405` — col0 `Stretch`, col1 `Fixed 140`, col2 `Fixed 180`; min 60 / max 120 filas.
- Problema: el operador no puede redimensionar las columnas de la tabla de orígenes para ver rutas largas o nombres de cámara.
- Heurísticas violadas: consistencia (la tabla de archivos `table` ya es `Interactive`, `app/ui/main_window.py:604`); contexto de acción.
- Propuesta de reubicación: no es reubicación — es **propiedad**: todas las columnas `Interactive` con ancho mínimo 100 y persistencia de anchos en `QSettings` (target `01-UI-SPEC.md:130`).
- Justificación de usabilidad: consistencia con `table`; el operador ajusta columnas según el contenido real de cada tarjeta.
- Impacto: fricción menor por jornada; no bloquea.
- Evidencia: inventario fila A-19 + captura `captures/zonaA_configurado.png` (tabla de orígenes poblada).
- Severidad: Baja.

**H-06 — Duplicado "guardar dispositivos" / dos flujos de origen separados (D-12):**
- Zona·Flujo: A·c + B·c. Controles: entrada manual del dashboard (`source_input`, `btn_browse_source`, `btn_receive_wifi`) + los 4 diálogos de picker (`SourcePickerDialog`, `DevicePickerDialog`, `FtpPickerDialog`, `WifiMethodDialog`, B-01..B-32).
- Ubicación actual: trío de la fila "Orígenes" (`app/ui/main_window.py:377-393`) + 4 diálogos independientes (`app/ui/source_picker.py`, `device_picker.py`, `ftp_picker.py`, `wifi_picker.py`).
- Problema: "elegir un origen personalizado en una sesión" y "buscar dispositivos guardados" son **dos flujos que parecen lo mismo pero están separados** (decisión confirmada D-12); el operador debe saber de antemano en qué diálogo buscar.
- Heurísticas violadas: frecuencia de uso (el origen se elige cada ciclo); descubribilidad (2 = varios diálogos con tooltips); consistencia (4 shells de diálogo distintos).
- Propuesta de reubicación: **un único flujo** "añadir origen" donde los guardados son una sección/pestaña del mismo diálogo, con zona de **dispositivos desconectados** visible en la misma ventana de orígenes (target `01-UI-SPEC.md:174-177`; decisión `costly` D-12: afecta a `source_picker.py`, `device_picker.py`, `main_window.py` y la tabla de sesiones).
- Justificación de usabilidad: un solo punto de entrada; los guardados pasan a ser pestañas; el estado de lo conocido se muestra (D-03 no esconder nada).
- Impacto: confusión en el flujo principal de conectar; es la decisión más cara de deshacer (costly).
- Evidencia: inventario filas A-16..A-18 + B-01..B-32 + capturas `captures/zonaB_estado-inicial.png` y `captures/zonaB_configurado.png` (SourcePickerDialog con secciones).
- Severidad: Alta.

**Flujo ingestar (i) — Tabla de implicados:**

| ID | Control (attr) | Zona·Flujo | Ubicación actual | Hallazgo |
|----|----------------|------------|------------------|----------|
| H-02 | A-23 `sessions_combo` | A·i | `app/ui/main_window.py:439-444` | H-02 |
| H-02 | A-26 `session_src_label` | A·i | `app/ui/main_window.py:461-466` | H-02 |
| H-02 | A-27 `_btn_browse_sess_src` | A·i | `app/ui/main_window.py:468-473` | H-02 |
| H-02 | A-29 `session_dest_combo` | A·i | `app/ui/main_window.py:477-481` | H-02 |
| H-02 | A-30 `session_dest_path` | A·i | `app/ui/main_window.py:483-488` | H-02 |
| H-02 | A-31 `_btn_browse_sess_dest` | A·i | `app/ui/main_window.py:490-496` | H-02 |
| H-02 | A-32 `chk_session_delicate` | A·i | `app/ui/main_window.py:498-500` | H-02 |
| H-03 | A-06 `btn_delete_project` | A·g | `app/ui/main_window.py:289,308` | H-03 |
| H-03 | A-15 `btn_remove_source` | A·c | `app/ui/main_window.py:368-374` | H-03 |
| H-03 | A-25 `btn_delete_session` | A·i | `app/ui/main_window.py:453-459` | H-03 |

**H-02 — Panel de sesiones crece a la derecha y come ancho de ventana (D-08):**
- Zona·Flujo: A·i. Controles: fila de sesión única (`sessions_combo` max 360, `session_src_label` max 240, `session_dest_combo` 110 fixed, `session_dest_path` 200 fixed, `_btn_browse_sess_src`, `_btn_browse_sess_dest`, `chk_session_delicate`).
- Ubicación actual: fila horizontal única bajo "Sesiones:" (`app/ui/main_window.py:434-503`).
- Problema: al configurar/ahondar, el panel crece hacia la derecha y come ancho de ventana; el espacio vertical disponible no se aprovecha (decisión confirmada D-08).
- Heurísticas violadas: contexto de acción (la config de sesión pertenece bajo su selector, no al costado); distancia de ratón (los campos quedan lejos del foco).
- Propuesta de reubicación: **apilado vertical** bajo el selector "Sesiones": combo arriba, configuración en filas propias debajo (origen, destino, modo delicado) (target `01-UI-SPEC.md:128`).
- Justificación de usabilidad: aprovecha el espacio vertical libre de la columna izquierda; reduce distancia de ratón y el scroll horizontal.
- Impacto: ancho de ventana consumido por configuración secundaria; la tabla de archivos pierde espacio.
- Evidencia: inventario filas A-23..A-32 + captura `captures/zonaA_configurado.png` (fila de sesión con todos los controles).
- Severidad: Alta.

**H-03 — Botones de eliminar genéricos y mal ubicados (D-09):**
- Zona·Flujo: A·g (proyecto) + A·c (origen) + A·i (sesión). Controles: `btn_delete_project` ("×"), `btn_remove_source` ("🗑"), `btn_delete_session` ("−").
- Ubicación actual: `app/ui/main_window.py:289,308` (header, deshabilitado sin proyecto), `:368-374` (fila "Orígenes:", deshabilitado sin selección), `:453-459` (junto al combo de sesiones).
- Problema: "mal ubicados Y mal presentados" (D-09): tres acciones destructivas distintas presentadas como iconos genéricos; el control debería comportarse distinto según el contexto (borrar sesión ≠ borrar origen ≠ borrar proyecto). **Confirmaciones existentes verificadas:** `_remove_selected_source` (pregunta en `app/ui/main_window.py:2266`), `_delete_current_session` (`:2473`), `delete_current_project` (`:3554`) — el problema es de presentación/ubicación, no de confirmación.
- Heurísticas violadas: consistencia (presentación destructiva no uniforme); contexto de acción (borrar el origen seleccionado pertenece a la fila, no al título).
- Propuesta de reubicación: `btn_remove_source` → menú contextual de fila "Eliminar origen…" con confirmación; `btn_delete_session` → "Eliminar sesión…" con consecuencia específica; `btn_delete_project` → mantener en header con confirmación explícita (target `01-UI-SPEC.md:132-134`, patrón D-09).
- Justificación de usabilidad: consistencia de presentación destructiva; contexto de acción por elemento.
- Impacto: riesgo de error operativo por iconos ambiguos; no hay pérdida de datos (confirmaciones ya presentes).
- Evidencia: inventario filas A-06, A-15, A-25 + captura `captures/zonaA_configurado.png`.
- Severidad: Media.

**Flujo formatear y reorganizar (f/r) — Tabla de implicados:**

| ID | Control (attr) | Zona·Flujo | Ubicación actual | Hallazgo |
|----|----------------|------------|------------------|----------|
| H-01 | A-42 `btn_clear_completed` | A·i | `app/ui/main_window.py:560-563` | H-01 |
| H-01 | D-01 `btn_reorganize` | D·r | `app/ui/main_window.py:570-573` | H-01 |
| H-01 | D-02 `chk_format_sources` | D·f | `app/ui/main_window.py:577-579,585` | H-01 |
| H-01 | D-03 `combo_format_mode` | D·f | `app/ui/main_window.py:580-585` | H-01 |
| H-01 | D-04 `chk_shutdown` | D·f | `app/ui/main_window.py:589-591` | H-01 |
| H-01 | D-05 `btn_clear_completed` | D·r | `app/ui/main_window.py:560-563` | H-01 |
| H-01 | D-06 botón "Contenido" | D·r | `app/ui/main_window.py:2052-2067,3689-3710` | H-01 |
| H-07 | D-07 `_open_selective_dump` | D·r | `app/ui/main_window.py:3671-3687` | H-07 |
| H-07 | D-08 menú contextual `table` | D·r | `app/ui/main_window.py:1882-1886` | H-07 |

**H-01 — Zona post-ingesta desordenada y visualmente secundaria (D-07):**
- Zona·Flujo: D·f/r (más A-42). Controles: `btn_reorganize`, `chk_format_sources`, `combo_format_mode`, `chk_shutdown`, `btn_clear_completed` (A-42/D-05), botón por fila "Contenido" (D-06).
- Ubicación actual: fila final bajo `stats_row` sin título (`app/ui/main_window.py:566-593`), mezclada con opciones de ingesta; `btn_clear_completed` dentro de `stats_row` (`:560-563`); "Contenido" por fila en `source_list` (`:2052-2067`, abre `_open_content_filter` `:3689-3710`).
- Problema: queda visualmente secundaria y desordenada — formateo/proxies/reorganizar viven ahí pero **no se perciben como acciones principales del flujo** (D-07). Además, hallazgo nuevo de esta revisión: `btn_reorganize` se **oculta** cuando el modo de detección no es `auto` (`self.btn_reorganize.setVisible(is_auto)` en `app/ui/main_window.py:1216`) — contradice D-03 (no esconder nada). Las confirmaciones de formateo (`:1802`) y apagado (`:1837-1842`) **existen** — no es un riesgo de pérdida de datos, es de percepción/jerarquía.
- Heurísticas violadas: contexto de acción (las acciones de cierre del ciclo están mezcladas con configuración previa); frecuencia (se usan al cierre de cada ciclo); descubribilidad (sin título de grupo).
- Propuesta de reubicación: `QGroupBox` "Acciones post-ingesta" con dos subgrupos: **"Al terminar"** (formatear orígenes + modo, apagar al acabar) y **"Operaciones"** (reorganizar por metadatos, limpiar completados, volcado selectivo…); `btn_clear_completed` sale de `stats_row`; `btn_reorganize` siempre visible (eliminar `setVisible(is_auto)`) (target `01-UI-SPEC.md:135-136`).
- Justificación de usabilidad: jerarquía visual; las acciones de cierre se perciben como principales; regla no esconder nada.
- Impacto: percepción del flujo completo; riesgo de que el operador olvide formatear/reorganizar al cerrar el ciclo.
- Evidencia: inventario filas A-42, D-01..D-06 + capturas `captures/zonaD_estado-inicial.png` y `captures/zonaD_configurado.png` (recorte de la zona bajo `progress_bar`).
- Severidad: Alta.

**H-07 — Volcado selectivo (modo dump) sin entrada visible; menú contextual con una sola acción (nuevo):**
- Zona·Flujo: D·r. Controles: `_open_selective_dump` (D-07) y menú contextual de `table` (D-08).
- Ubicación actual: `_open_selective_dump` definido en `app/ui/main_window.py:3671-3687` pero **sin wiring**: el grep del plan 01 solo encuentra la definición, ningún `clicked.connect` ni llamada; el menú contextual de `table` (`:1882-1886`) solo tiene la acción "Eliminar completados". El modo filter es accesible por el botón por fila "Contenido" (`:2052-2067` → `_open_content_filter` `:3689-3710`), pero el modo dump (volcado selectivo completo) no tiene entrada visible.
- Problema: la funcionalidad de volcado selectivo existe (asistente `SelectiveDumpAssistant` con stack de 4 páginas, `app/ui/selective_dump.py:374-386`) pero su entrada principal es inaccesible desde la UI.
- Heurísticas violadas: descubribilidad (3 = oculto); frecuencia de uso real (el volcado selectivo se usa en rodajes con selección por fecha).
- Propuesta de reubicación: entrada visible **"Volcado selectivo…"** en el grupo "Acciones post-ingesta" → "Operaciones" **y** mantener el menú contextual (ambos accesibles; target `01-UI-SPEC.md:186,198`).
- Justificación de usabilidad: descubribilidad de una operación de cierre de ciclo; regla no esconder nada.
- Impacto: operación existente inaccesible; el operador no puede volcar selecciones por fecha desde la UI.
- Evidencia: inventario filas D-07, D-08 (grep de `_open_selective_dump` con 1 solo match = la definición) + captura `captures/zonaA_configurado.png`. **Evidencia no verificable — registrar el motivo en la columna Evidencia y volver a capturar en la fase de ejecución.** (el menú contextual es interacción en runtime y no se capturó offscreen en el plan 01; el grep confirma la definición sin wiring, la captura visual del menú queda pendiente).
- Severidad: Media.

## Anclas de decisiones (D-07..D-12)

Citas textuales de `01-CONTEXT.md:27-32` ancladas a las filas del inventario (`01-INVENTARIO.md:165-172`) y al hallazgo que las desarrolla. Ninguna decisión queda sin ancla verificable.

**D-07 — Zona post-ingesta:**
- Cita textual (01-CONTEXT.md:27): "**Zona post-ingesta** (lo que vive debajo de la barra de progreso): queda visualmente secundaria y está desordenada. Formateo/proxies/reorganizar viven ahí pero no se perciben como acciones principales del flujo."
- Ancla de inventario: D-01, D-02, D-03, D-04, D-05, D-06 (01-INVENTARIO.md:167)
- Evidencia: filas D-01..D-06 + capturas `captures/zonaD_estado-inicial.png` y `captures/zonaD_configurado.png`
- Hallazgo: H-01 (severidad Alta)

**D-08 — Sesiones:**
- Cita textual (01-CONTEXT.md:28): "**Sesiones**: al configurar/ahondar, el panel crece hacia la derecha y come ancho de ventana; el espacio vertical disponible no se aprovecha."
- Ancla de inventario: A-23 (max 360), A-26, A-27, A-29, A-30, A-31, A-32 (01-INVENTARIO.md:168)
- Evidencia: filas A-23, A-26, A-27, A-29, A-30, A-31, A-32 + captura `captures/zonaA_configurado.png`
- Hallazgo: H-02 (severidad Alta)

**D-09 — Botones de eliminar:**
- Cita textual (01-CONTEXT.md:29): "**Botones de eliminar**: mal ubicados Y mal presentados. Dependiendo del contexto (borrar sesión, borrar fuente, borrar origen) el control debería comportarse distinto — no un "eliminar" genérico en todas partes."
- Ancla de inventario: A-06 (`btn_delete_project`), A-15 (`btn_remove_source`), A-25 (`btn_delete_session`) (01-INVENTARIO.md:169)
- Evidencia: filas A-06, A-15, A-25 + confirmaciones verificadas (`app/ui/main_window.py:2266,2473,3554`) + captura `captures/zonaA_configurado.png`
- Hallazgo: H-03 (severidad Media)

**D-10 — Descripción del proyecto:**
- Cita textual (01-CONTEXT.md:30): "**Descripción del proyecto**: el wizard la captura pero no aparece en ninguna vista posterior — dato muerto. Debe mostrarse en algún sitio (informe del proyecto / cabecera)."
- Ancla de inventario: C-03 (`desc_input`) (01-INVENTARIO.md:170)
- Evidencia: fila C-03 + puntos de guardado/lectura (`app/ui/main_window.py:1191,1313,3647`) + captura `captures/zonaC_configurado.png` (descripción llena que ninguna vista posterior muestra)
- Hallazgo: H-04 (severidad Media)

**D-11 — Columnas de la tabla de orígenes:**
- Cita textual (01-CONTEXT.md:31): "**Tabla de orígenes**: columnas de ancho fijo sin posibilidad de redimensionar. Propuesta: columnas redimensionables."
- Ancla de inventario: A-19 (`source_list`: col1/col2 Fixed, `app/ui/main_window.py:400-405`) (01-INVENTARIO.md:171)
- Evidencia: fila A-19 + captura `captures/zonaA_configurado.png` (tabla de orígenes con 3 filas)
- Hallazgo: H-05 (severidad Baja)

**D-12 — Duplicado de "guardar dispositivos":**
- Cita textual (01-CONTEXT.md:32): "**Duplicado de "guardar dispositivos"**: elegir un origen personalizado en una sesión vs. buscar dispositivos guardados son dos flujos que parecen lo mismo pero están separados. **Decisión: un único flujo** "añadir origen" donde los dispositivos guardados son una sección/pestaña del mismo diálogo, e incluyendo una **zona de dispositivos desconectados** (dispositivos conocidos pero no presentes ahora, con su estado visible) dentro de la **misma ventana de orígenes**."
- Ancla de inventario: A-16, A-17, A-18 + B-01..B-05 (`SourcePickerDialog`) + B-06..B-11 (`DevicePickerDialog`) + B-12..B-28 (`FtpPickerDialog`) + B-29..B-32 (`WifiMethodDialog`) (01-INVENTARIO.md:172)
- Evidencia: filas A-16..A-18 + B-01..B-32 + capturas `captures/zonaB_estado-inicial.png` y `captures/zonaB_configurado.png`
- Hallazgo: H-06 (severidad Alta; decisión `costly`)

## Conservación (D-03)

Controles del inventario que **no** requieren reubicación en esta fase: se mantiene la ubicación actual (regla D-03 — no esconder nada, no mover por mover). 65 de 121 filas quedan conservadas (28 de Zona A, 37 de Zona C); Zona B queda íntegramente implicada por H-06 y Zona D por H-01/H-07.

| ID | Control (attr) | Zona·Flujo | Ubicación actual | Estado en esta revisión |
|----|----------------|------------|------------------|-------------------------|
| A-01 | `app_label` | A·g | `app/ui/main_window.py:275-277` | Conservado — cabecera sin hallazgo |
| A-02 | (label estático) "Proyecto:" | A·g | `app/ui/main_window.py:280` | Conservado |
| A-03 | `project_combo` | A·g | `app/ui/main_window.py:281-284` | Conservado |
| A-04 | `btn_refresh_projects` | A·g | `app/ui/main_window.py:287,294-307` | Conservado |
| A-05 | `btn_new_project` | A·g | `app/ui/main_window.py:288,294-307` | Conservado |
| A-07 | `btn_rename_project` | A·g | `app/ui/main_window.py:290,309` | Conservado |
| A-08 | `btn_duplicate_project` | A·g | `app/ui/main_window.py:291,310` | Conservado |
| A-09 | `btn_browse_root` | A·g | `app/ui/main_window.py:292,294-307` | Conservado |
| A-10 | `project_path_label` | A·g | `app/ui/main_window.py:314-319` | Conservado |
| A-11 | `btn_show_metadata` | A·g | `app/ui/main_window.py:323-332` | Conservado |
| A-12 | `status_indicator` | A·g | `app/ui/main_window.py:336-339` | Conservado |
| A-13 | `status_text` | A·g | `app/ui/main_window.py:341-343` | Conservado |
| A-14 | (label estático) "Orígenes:" | A·c | `app/ui/main_window.py:364-367` | Conservado |
| A-20 | `btn_detect_drives` | A·c | `app/ui/main_window.py:421-424` | Conservado |
| A-21 | `btn_scan_cameras` | A·c | `app/ui/main_window.py:425-428` | Conservado |
| A-22 | (label estático) "Sesiones:" | A·i | `app/ui/main_window.py:434-436` | Conservado |
| A-24 | `btn_new_session` | A·i | `app/ui/main_window.py:446-451` | Conservado |
| A-28 | (label estático) "Destino:" | A·i | `app/ui/main_window.py:476` | Conservado |
| A-33 | `btn_start` | A·i | `app/ui/main_window.py:507-511` | Conservado — CTA principal sin hallazgo |
| A-34 | `btn_stop` | A·i | `app/ui/main_window.py:513-517` | Conservado |
| A-35 | `ingest_status_label` | A·i | `app/ui/main_window.py:523-525` | Conservado |
| A-36 | `progress_bar` | A·i | `app/ui/main_window.py:528-532` | Conservado |
| A-37 | `chk_generate_proxies` | A·i | `app/ui/main_window.py:536-538` | Conservado |
| A-38 | `proxy_resolution` | A·i | `app/ui/main_window.py:539-543,547` | Conservado |
| A-39 | `lbl_files_processed` | A·i | `app/ui/main_window.py:550-551` | Conservado |
| A-40 | `lbl_files_pending` | A·i | `app/ui/main_window.py:552-553` | Conservado |
| A-41 | `lbl_files_errors` | A·i | `app/ui/main_window.py:554-555` | Conservado |
| A-43 | `table` | A·i | `app/ui/main_window.py:598-614` | Conservado — tabla de archivos sin hallazgo |
| C-01 | (wizard) | C·c | `app/ui/project_wizard.py:10,18-20` | Conservado |
| C-02 | `name_input` | C·c | `app/ui/project_wizard.py:33-38` | Conservado |
| C-04 | `dest_input` | C·c | `app/ui/project_wizard.py:49-54` | Conservado |
| C-05 | `radio_one_day` | C·c | `app/ui/project_wizard.py:64-66` | Conservado |
| C-06 | `radio_multiple_days` | C·c | `app/ui/project_wizard.py:68-69` | Conservado |
| C-07 | `radio_no_date` | C·c | `app/ui/project_wizard.py:71-72` | Conservado |
| C-08 | `org_combo` | C·c | `app/ui/project_wizard.py:83-94` | Conservado |
| C-09 | `chk_use_metadata_date` | C·c | `app/ui/project_wizard.py:96-99` | Conservado |
| C-10 | `btn_finish` | C·c | `app/ui/project_wizard.py:113-117` | Conservado |
| C-11 | (asistente) | C·r | `app/ui/selective_dump.py:337,345-347` | Conservado — asistente completo (la entrada es el hallazgo, H-07) |
| C-12 | `_stack` | C·r | `app/ui/selective_dump.py:374-386` | Conservado |
| C-13 | `btn_scan` | C·r | `app/ui/selective_dump.py:413-416` | Conservado |
| C-14 | `scan_progress` | C·r | `app/ui/selective_dump.py:432-434` | Conservado |
| C-15 | `btn_scan_cancel` | C·r | `app/ui/selective_dump.py:445-447` | Conservado |
| C-16 | `calendar` | C·r | `app/ui/selective_dump.py:468-470,472-484,126` | Conservado |
| C-17 | `btn_select_all` | C·r | `app/ui/selective_dump.py:487-489` | Conservado |
| C-18 | `btn_clear` | C·r | `app/ui/selective_dump.py:490-492` | Conservado |
| C-19 | `preview_table` | C·r | `app/ui/selective_dump.py:507-517` | Conservado |
| C-20 | `chk_include_nodate` | C·r | `app/ui/selective_dump.py:523-524` | Conservado |
| C-21 | `btn_dump` | C·r | `app/ui/selective_dump.py:534-542` | Conservado |
| C-22 | `dump_progress` | C·r | `app/ui/selective_dump.py:557-559` | Conservado |
| C-23 | `btn_dump_cancel` | C·r | `app/ui/selective_dump.py:570-572` | Conservado |
| C-24 | (panel) | C·c | `app/ui/wifi_panel.py:66,81-87` | Conservado |
| C-25 | `qr_label` | C·c | `app/ui/wifi_panel.py:102-107` | Conservado |
| C-26 | `url_label` | C·c | `app/ui/wifi_panel.py:111-119` | Conservado |
| C-27 | `copy_btn` | C·c | `app/ui/wifi_panel.py:121-124` | Conservado |
| C-28 | `status_label` | C·c | `app/ui/wifi_panel.py:127-130` | Conservado |
| C-29 | `folder_mode_cb` | C·c | `app/ui/wifi_panel.py:141-144` | Conservado |
| C-30 | `stop_btn` | C·c | `app/ui/wifi_panel.py:150-153` | Conservado |
| C-31 | `close_btn` | C·c | `app/ui/wifi_panel.py:154-156` | Conservado |
| C-32 | (diálogo) | C·g | `app/ui/about_dialog.py:72,83` | Conservado |
| C-33 | `tabs` | C·g | `app/ui/about_dialog.py:86-92` | Conservado |
| C-34 | `lbl_current` | C·g | `app/ui/about_dialog.py:167-170` | Conservado |
| C-35 | `btn_check` | C·g | `app/ui/about_dialog.py:177-179` | Conservado |
| C-36 | `btn_download` | C·g | `app/ui/about_dialog.py:181-185` | Conservado |
| C-37 | `progress` | C·g | `app/ui/about_dialog.py:187-189` | Conservado |
| C-38 | `chk_auto` | C·g | `app/ui/about_dialog.py:192-195` | Conservado |

## Próximo paso

Los hallazgos H-01..H-07 pasan al plan 03, que los puntúa con la fórmula D-06 (`Score = Impacto − (Esfuerzo + Riesgo)/2`, bandas P1/P2/P3) y produce `01-PLAN-REUBICACION.md` con el orden de implementación por flujo del operador (conectar → ingestar → formatear → reorganizar). Los ítems destructivos quedan marcados "pendiente de confirmación D-09" y no reciben orden de ejecución hasta la confirmación explícita del operador.
