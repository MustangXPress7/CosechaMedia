# Fase 1: Plan de Reubicación — Auditoría UI

**Elaborado:** 2026-08-15
**Estado:** draft — pendiente de aprobación del operador (checkpoint plan 04)

## Resumen por bandas

El informe de hallazgos (`01-HALLAZGOS.md`) identificó **7 hallazgos (H-01..H-07)** con sus factores impacto/esfuerzo/riesgo. Este plan puntúa cada hallazgo con la fórmula D-06 (`Score = Impacto − (Esfuerzo + Riesgo)/2`, bandas **P1 ≥ 2.5**, **P2 1.0–2.4**, **P3 < 1.0** — `01-UI-SPEC.md:246-252`) y lo descompone en **17 ítems de reubicación (R-01..R-17)** con orden de implementación por flujo del operador (conectar → ingestar → formatear → reorganizar, D-01). Ningún hallazgo queda sin ítem ni se descarta sin motivo (trazabilidad completa en la sección §5-bis).

| Banda | Ítems | Copy (zero-one-many) | Ítems |
|-------|-------|----------------------|-------|
| P1 (≥ 2.5) | 5 | **5 ítems P1** | R-01, R-02, R-03, R-06, R-10 |
| P2 (1.0–2.4) | 11 | **11 ítems P2** | R-04, R-05, R-07, R-08, R-09, R-11, R-12, R-13, R-14, R-15, R-17 |
| P3 (< 1.0) | 1 | **1 ítem P3** | R-16 |

**Cobertura de casos (UI-03 zero-one-many, `01-UI-SPEC.md:270`):**
- **many (P1, 3+ ítems):** "5 ítems P1" — R-01, R-02, R-03, R-06, R-10.
- **many (P2, 3+ ítems):** "11 ítems P2" — R-04, R-05, R-07, R-08, R-09, R-11, R-12, R-13, R-14, R-15, R-17.
- **one (P3, 1-2 ítems):** "1 ítem P3" — R-16.
- **zero (sin P1):** no aplica — las tres bandas tienen ítems; ninguna banda se oculta ni se vacía en silencio. Si una banda quedara vacía se declararía explícitamente "Zona sin ítems de reubicación" (copy literal `01-UI-SPEC.md:263` / `01-PATTERNS.md:166`) en §1 y §3.

**Ítems destructivos (5):** R-02 (formatear orígenes), R-03 (apagar al acabar), R-07 (eliminar origen), R-08 (eliminar sesión), R-09 (eliminar proyecto) — quedan **pendientes de confirmación D-09** y **no reciben orden de ejecución** hasta la confirmación explícita del operador en el checkpoint del plan 04 (las confirmaciones de runtime ya existen en el código: formateo `main_window.py:1802`, apagado `:1837-1842`, eliminar origen/sesión/proyecto `:2266,2473,3554`; el hallazgo es de presentación/ubicación, no de pérdida de datos).

## Matriz de puntuación

Matriz por hallazgo (una fila por H-NN, con el Score y la banda del ítem líder de cada hallazgo). Los sub-scores por ítem (Impacto/Esfuerzo/Riesgo, 1-5) se detallan en la matriz ampliada y en cada bloque de §3.

| H-NN · Hallazgo | Ítems (R-NN) | Impacto | Esfuerzo | Riesgo | Score · Banda |
|-----------------|--------------|---------|----------|--------|---------------|
| H-01 · Zona post-ingesta desordenada (D-07) | R-01, R-02, R-03, R-04, R-05 | 5 | 2 | 2 | **3.0 · P1** (R-01) |
| H-02 · Panel de sesiones crece a la derecha (D-08) | R-06 | 5 | 2 | 2 | **3.0 · P1** (R-06) |
| H-03 · Botones de eliminar genéricos (D-09) | R-07, R-08, R-09 | 4 | 2 | 3 | **1.5 · P2** (R-07) |
| H-04 · Descripción del proyecto, dato muerto (D-10) | R-10 | 4 | 1 | 2 | **2.5 · P1** (R-10) |
| H-05 · Columnas de `source_list` de ancho fijo (D-11) | R-11 | 3 | 2 | 2 | **1.0 · P2** (R-11) |
| H-06 · Duplicado "guardar dispositivos" (D-12, costly) | R-12, R-13, R-14, R-15, R-16 | 5 | 5 | 3 | **1.0 · P2** (R-12) |
| H-07 · Volcado selectivo sin entrada visible (nuevo) | R-17 | 3 | 2 | 2 | **1.0 · P2** (R-17) |

**Fórmula (D-06):** `Score = Impacto − (Esfuerzo + Riesgo)/2` — Impacto 5 = frecuencia alta y bloqueo/fricción del flujo, 1 = pulido cosmético; Esfuerzo 5 = toca múltiples diálogos + wiring (caso D-12), 1 = cambio local de layout; Riesgo 1-5 = tests acoplados + i18n (nuevos strings/renombres) + estética (QSS/tema). Bandas: **P1 ≥ 2.5**, **P2 1.0–2.4**, **P3 < 1.0** (`01-UI-SPEC.md:246-252`).

**Cálculos a modo de ejemplo (4 de 17):**

| Ítem | Cálculo | Resultado |
|------|---------|-----------|
| R-01 — Grupo "Acciones post-ingesta" | 5 − (2 + 2)/2 | 5 − 2 = **3.0 → P1** |
| R-06 — Apilado vertical de sesiones | 5 − (2 + 2)/2 | 5 − 2 = **3.0 → P1** |
| R-12 — Diálogo unificado "Añadir origen" | 5 − (5 + 3)/2 | 5 − 4 = **1.0 → P2** (Esfuerzo 5 es definicional para D-12, `01-UI-SPEC.md:249`; véase discrepancia en §4) |
| R-16 — `WifiMethodDialog` mantenido | 2 − (1 + 2)/2 | 2 − 1.5 = **0.5 → P3** |

**Matriz ampliada por ítem (17 filas, sub-scores y bandas):**

| Ítem (R-NN · H-NN) | Impacto | Esfuerzo | Riesgo | Score · Banda |
|--------------------|---------|----------|--------|---------------|
| R-01 · H-01 | 5 | 2 | 2 | 3.0 · **P1** |
| R-02 · H-01 | 4 | 1 | 2 | 2.5 · **P1** (destructivo, D-09) |
| R-03 · H-01 | 4 | 1 | 2 | 2.5 · **P1** (destructivo, D-09) |
| R-04 · H-01 | 4 | 1 | 3 | 2.0 · **P2** |
| R-05 · H-01 | 3 | 1 | 2 | 1.5 · **P2** |
| R-06 · H-02 | 5 | 2 | 2 | 3.0 · **P1** |
| R-07 · H-03 | 4 | 2 | 3 | 1.5 · **P2** (destructivo, D-09) |
| R-08 · H-03 | 4 | 2 | 3 | 1.5 · **P2** (destructivo, D-09) |
| R-09 · H-03 | 3 | 1 | 3 | 1.0 · **P2** (destructivo, D-09) |
| R-10 · H-04 | 4 | 1 | 2 | 2.5 · **P1** |
| R-11 · H-05 | 3 | 2 | 2 | 1.0 · **P2** |
| R-12 · H-06 | 5 | 5 | 3 | 1.0 · **P2** |
| R-13 · H-06 | 4 | 3 | 3 | 1.0 · **P2** |
| R-14 · H-06 | 4 | 3 | 3 | 1.0 · **P2** |
| R-15 · H-06 | 4 | 2 | 3 | 1.5 · **P2** |
| R-16 · H-06 | 2 | 1 | 2 | 0.5 · **P3** |
| R-17 · H-07 | 3 | 2 | 2 | 1.0 · **P2** |

**Cobertura:** los 7 hallazgos H-01..H-07 aparecen en la matriz con Score (D-06) y banda; ningún hallazgo queda sin puntuar.

## Plan por zona

Las 4 zonas tienen ítems de reubicación; ninguna se oculta ni se vacía en silencio (D-03, UI-03). Dentro de cada banda, los ítems se ordenan por flujo del operador (conectar → ingestar → formatear → reorganizar, D-01); los ítems destructivos quedan **pendientes de confirmación D-09** sin orden de ejecución.

### Zona A — Ventana principal / dashboard (5 ítems)

**R-06 — Apilado vertical del panel de sesiones (H-02 · D-08):**
- **Zona·Flujo:** A · i (ingestar)
- **Control:** `sessions_combo` (selector de sesión, A-23), `session_src_label` + `_btn_browse_sess_src` (origen de sesión, A-26/A-27), `session_dest_combo` + `session_dest_path` + `_btn_browse_sess_dest` (destino, A-29..A-31), `chk_session_delicate` ("Modo delicado", A-32)
- **Ubicación actual:** fila horizontal única bajo "Sesiones:" que crece a la derecha — `app/ui/main_window.py:434-503` (combo max 360, labels max 240, dest combo fixed 110, dest path fixed 200)
- **Destino propuesto:** apilado vertical bajo el selector "Sesiones": combo arriba; origen, destino y modo delicado en filas propias debajo (target `01-UI-SPEC.md:128`); aprovecha el espacio vertical de la columna izquierda y reduce distancia de ratón
- **Strings nuevos:** — (ninguno; labels existentes)
- **Riesgo:** tests: medio — `sessions_combo` y `_refresh_sessions_combo()` usados por `tests/test_source_content.py:142-145` y `tests/test_wifi_source.py:373,388-389`; se mantienen el attr, el método y los estados (prohibido renombrar). i18n: ninguno. Estética: medio — cambio de layout de la columna izquierda sin tocar QSS/tema.
- **Score:** 3.0 (5 − (2+2)/2) → **P1**
- **Orden:** P1-2 (flujo ingestar; tras R-10 de conectar)

**R-11 — Columnas de `source_list` redimensionables + persistencia (H-05 · D-11):**
- **Zona·Flujo:** A · c (conectar)
- **Control:** `source_list` (columnas "Ruta de origen"/"Cámara"/"Contenido", A-19)
- **Ubicación actual:** `app/ui/main_window.py:396-418` — col0 `Stretch`, col1 `Fixed 140`, col2 `Fixed 180` (`:400-405`), min 60 / max 120 filas
- **Destino propuesto:** todas las columnas `Interactive` (`QHeaderView.Interactive`), ancho mínimo 100, persistir anchos en `QSettings` (target `01-UI-SPEC.md:130`); consistencia con `table` (ya Interactive, `:604`)
- **Strings nuevos:** — (ninguno)
- **Riesgo:** tests: medio — `source_list` es widget público usado por `tests/test_e2e.py` (nombrado en `01-INVENTARIO.md:8`); el cambio de resize mode no altera la lectura de celdas. i18n: ninguno. Estética: bajo.
- **Score:** 1.0 (3 − (2+2)/2) → **P2**
- **Orden:** P2-1 (flujo conectar)

**R-07 — `btn_remove_source` → menú contextual "Eliminar origen…" (H-03 · D-09):**
- **Zona·Flujo:** A · c (conectar)
- **Control:** `btn_remove_source` ("🗑", tooltip "Eliminar origen seleccionado", A-15)
- **Ubicación actual:** icono en la fila del título "Orígenes" — `app/ui/main_window.py:368-374`, deshabilitado sin selección
- **Destino propuesto:** menú contextual de fila "Eliminar origen…" con confirmación explícita (target `01-UI-SPEC.md:132`); el icono del título se mantiene solo deshabilitado cuando no hay selección (D-03: no ocultar)
- **Strings nuevos:** `tr("Eliminar origen…")` + confirmación con plantilla D-09 `tr("Eliminar <elemento>: Esta acción no se puede deshacer. <Consecuencia específica>.")` (`01-UI-SPEC.md:105`)
- **Riesgo:** tests: bajo — `btn_remove_source` no acoplado a tests; la confirmación `_remove_selected_source` ya existe (`:2266`). i18n: 1 string nuevo + plantilla. Estética: bajo.
- **Score:** 1.5 (4 − (2+3)/2) → **P2**
- **Orden:** pendiente de confirmación D-09 — no recibe orden de ejecución

**R-08 — `btn_delete_session` → "Eliminar sesión…" (H-03 · D-09):**
- **Zona·Flujo:** A · i (ingestar)
- **Control:** `btn_delete_session` ("−", tooltip "Eliminar sesión", A-25)
- **Ubicación actual:** icono junto al combo de sesiones — `app/ui/main_window.py:453-459`, deshabilitado sin sesión
- **Destino propuesto:** "Eliminar sesión…" con confirmación específica de consecuencia (borra la sesión y sus referencias de archivos) (target `01-UI-SPEC.md:133`); confirmación `_delete_current_session` ya existe (`:2473`)
- **Strings nuevos:** `tr("Eliminar sesión…")` + plantilla D-09
- **Riesgo:** tests: bajo — `btn_delete_session` no acoplado a tests. i18n: 1 string nuevo + plantilla. Estética: bajo.
- **Score:** 1.5 (4 − (2+3)/2) → **P2**
- **Orden:** pendiente de confirmación D-09 — no recibe orden de ejecución

**R-09 — `btn_delete_project` → confirmación explícita en header (H-03 · D-09):**
- **Zona·Flujo:** A · g (gestión de proyecto; se activa en conectar)
- **Control:** `btn_delete_project` ("×", tooltip "Eliminar proyecto", A-06)
- **Ubicación actual:** icono de la header bar, deshabilitado sin proyecto — `app/ui/main_window.py:289,308`
- **Destino propuesto:** mantener en header; confirmación explícita con consecuencia (borra sesiones y referencias del proyecto) (target `01-UI-SPEC.md:134`); confirmación `delete_current_project` ya existe (`:3554`)
- **Strings nuevos:** `tr("Eliminar proyecto…")` + plantilla D-09
- **Riesgo:** tests: bajo — `btn_delete_project` no acoplado a tests. i18n: 1 string nuevo + plantilla. Estética: bajo.
- **Score:** 1.0 (3 − (1+3)/2) → **P2**
- **Orden:** pendiente de confirmación D-09 — no recibe orden de ejecución

### Zona B — Pickers de fuente (5 ítems)

**R-12 — Diálogo unificado "Añadir origen" (H-06 · D-12, costly):**
- **Zona·Flujo:** B · c (conectar)
- **Control:** `SourcePickerDialog` (B-01..B-05) + entrada del dashboard `source_input`/`btn_browse_source`/`btn_receive_wifi` (A-16..A-18)
- **Ubicación actual:** trío de la fila "Orígenes" (`app/ui/main_window.py:377-393`) + diálogo propio "Seleccionar origen" (`app/ui/source_picker.py:18,33-35`)
- **Destino propuesto:** un único botón "Añadir origen…" que abre el diálogo unificado con `QTabWidget` **[Guardados | Dispositivos | Desconectados]** + botón "Examinar…" + botonera estándar (targets `01-UI-SPEC.md:131,174`); "Examinar" vive dentro del diálogo; WiFi → `WifiMethodDialog` invocado desde el diálogo; estado de lo conocido siempre visible (D-03)
- **Strings nuevos:** `tr("Añadir origen…")`, `tr("Dispositivos guardados")`, `tr("Dispositivos desconectados")` + empty states `tr("Sin dispositivos guardados")`, `tr("No se detectaron dispositivos")`, `tr("Sin dispositivos conocidos")` (`01-UI-SPEC.md:109`)
- **Riesgo:** tests: alto — `SourcePickerDialog`/`list_widget` en `tests/test_source_picker.py:1,10,19,28-29,66-68`; mock `app.ui.wifi_picker.WifiMethodDialog` en `tests/test_wifi_source.py:721,731`; cambio del entry point de orígenes. i18n: 6 strings nuevos. Estética: medio — shell QTabWidget nuevo en zona B.
- **Score:** 1.0 (5 − (5+3)/2) → **P2** (véase discrepancia con target-state en §4)
- **Orden:** P2-2 (D-12 precede a sus pestañas R-13/R-14/R-15 — dependencia, `01-UI-SPEC.md:252`)

**R-13 — `DevicePickerDialog` → pestaña "Dispositivos" (MTP) (H-06 · D-12):**
- **Zona·Flujo:** B · c (conectar)
- **Control:** `DevicePickerDialog` — `device_combo`, `refresh_btn`, `tree`, `selection_label`, `ok_btn` (B-06..B-11)
- **Ubicación actual:** diálogo propio "Seleccionar carpeta del dispositivo" — `app/ui/device_picker.py:16,34`
- **Destino propuesto:** contenido de la pestaña "Dispositivos" (sección MTP) del diálogo unificado, reutilizando el patrón existente (target `01-UI-SPEC.md:175`)
- **Strings nuevos:** — (labels existentes; la pestaña reutiliza `tr("Dispositivos")` del shell)
- **Riesgo:** tests: medio — sin acople directo a tests en `tests/`; el flujo MTP depende de `app/core/mtp.py` (no tocado). i18n: ninguno. Estética: bajo.
- **Score:** 1.0 (4 − (3+3)/2) → **P2**
- **Orden:** P2-3 (depende de R-12)

**R-14 — `FtpPickerDialog` → pestaña "Dispositivos" (FTP) (H-06 · D-12):**
- **Zona·Flujo:** B · c (conectar)
- **Control:** `FtpPickerDialog` — `profile_combo`, `name_edit`, `host_edit`, `detect_btn`, `port_spin`, `user_edit`, `pass_edit`, `base_edit`, `passive_check`, `connect_btn`, `conn_status`, `tree`, `guide_btn`, `guide_text`, `selection_label`, `ok_btn` (B-12..B-28)
- **Ubicación actual:** diálogo propio "Importar por WiFi (FTP)" — `app/ui/ftp_picker.py:53,71`
- **Destino propuesto:** contenido de la pestaña "Dispositivos" (sección FTP) del diálogo unificado (target `01-UI-SPEC.md:176`)
- **Strings nuevos:** — (labels existentes)
- **Riesgo:** tests: medio — `tests/test_ftp.py` ejercita el backend, no el diálogo; sin acople directo del diálogo en `tests/`. i18n: ninguno. Estética: bajo.
- **Score:** 1.0 (4 − (3+3)/2) → **P2**
- **Orden:** P2-4 (depende de R-12)

**R-15 — Zona "Dispositivos desconectados" (H-06 · D-12):**
- **Zona·Flujo:** B · c (conectar)
- **Control:** (control nuevo — no existe hoy; estado objetivo)
- **Ubicación actual:** no existe — decisión D-12 (`01-CONTEXT.md:32`): incluir la zona en la misma ventana de orígenes, no en la principal
- **Destino propuesto:** pestaña/sección "Dispositivos desconectados" del diálogo unificado: dispositivos guardados no presentes ahora, con estado "desconectado" visible y acción de refrescar/recordar (target `01-UI-SPEC.md:177`; regla D-03: el estado de lo conocido se muestra)
- **Strings nuevos:** `tr("Dispositivos desconectados")` (compartido con R-12) + empty state `tr("Sin dispositivos conocidos")`
- **Riesgo:** tests: bajo — control nuevo sin acople previo. i18n: 1-2 strings nuevos. Estética: bajo.
- **Score:** 1.5 (4 − (2+3)/2) → **P2**
- **Orden:** P2-5 (depende de R-12)

**R-16 — `WifiMethodDialog` mantenido, invocable desde el diálogo unificado (H-06 · D-12):**
- **Zona·Flujo:** B · c (conectar)
- **Control:** `WifiMethodDialog` — `hint`, `btn_pairdrop`, `btn_ftp` (B-29..B-32)
- **Ubicación actual:** diálogo propio de 2 tarjetas "Recibir por WiFi" — `app/ui/wifi_picker.py:13,22-24`
- **Destino propuesto:** mantener como punto de entrada a recepción WiFi; invocable desde el diálogo unificado (flujo "Añadir origen…" → WiFi) (target `01-UI-SPEC.md:178`)
- **Strings nuevos:** — (ninguno)
- **Riesgo:** tests: medio — `app.ui.wifi_picker.WifiMethodDialog` mockeado en `tests/test_wifi_source.py:721,731`; mantener módulo/clase/constructor. i18n: ninguno. Estética: bajo.
- **Score:** 0.5 (2 − (1+2)/2) → **P3**
- **Orden:** P3-1 (invocación desde R-12)

### Zona C — Asistentes y paneles (1 ítem)

**R-10 — Línea de info del proyecto (H-04 · D-10):**
- **Zona·Flujo:** C · c (conectar) — origen del dato; destino en Zona A (dashboard)
- **Control:** `desc_input` ("Descripción (Opcional)", C-03) — capturada en `ProjectWizard`
- **Ubicación actual:** `app/ui/project_wizard.py:41-46`; guardado en BD al crear (`app/ui/main_window.py:1191,3647`), SELECT `:1313`, copia en duplicado `:1335-1339`; **ninguna vista posterior la muestra** — dato muerto
- **Destino propuesto:** línea de info del proyecto bajo la header bar: "Descripción del proyecto: <texto>" truncada con ellipsis + tooltip completo (o tooltip del `project_combo`) (target `01-UI-SPEC.md:129`)
- **Strings nuevos:** `tr("Descripción del proyecto")`
- **Riesgo:** tests: bajo — `desc_input` solo se usa en el wizard (sin acople en `tests/`); el label nuevo no rompe `ProjectWizard`. i18n: 1 string nuevo. Estética: bajo — label bajo header con QSS existente.
- **Score:** 2.5 (4 − (1+2)/2) → **P1**
- **Orden:** P1-1 (flujo conectar — la info del proyecto se lee al seleccionar proyecto)

El resto de la Zona C (**no reubicar — ya bien ubicado**): `ProjectWizard` mantiene su estructura (referencia de buena organización, `01-UI-SPEC.md:185`), `SelectiveDumpAssistant` mantiene su patrón de asistente (la entrada es el hallazgo H-07 → R-17), `ShootInboxPanel` y `AboutDialog` se mantienen con shell estándar (P3, `01-UI-SPEC.md:187-188`).

### Zona D — Acciones post-ingesta (6 ítems)

**R-01 — Grupo "Acciones post-ingesta" con subgrupos (H-01 · D-07):**
- **Zona·Flujo:** D · f/r (formatear/reorganizar)
- **Control:** contenedor para `btn_reorganize` (D-01), `chk_format_sources` + `combo_format_mode` (D-02/D-03), `chk_shutdown` (D-04), `btn_clear_completed` (A-42/D-05)
- **Ubicación actual:** fila final bajo `stats_row` sin título — `app/ui/main_window.py:566-593`; `btn_clear_completed` dentro de `stats_row` (`:560-563`)
- **Destino propuesto:** `QGroupBox` "Acciones post-ingesta" con dos subgrupos: **"Al terminar"** (formatear orígenes + modo, apagar al acabar) y **"Operaciones"** (reorganizar por metadatos, limpiar completados, volcado selectivo…); `btn_clear_completed` sale de `stats_row`; `btn_reorganize` **siempre visible** (eliminar `self.btn_reorganize.setVisible(is_auto)` en `:1216` — contradice D-03) (target `01-UI-SPEC.md:135-136`)
- **Strings nuevos:** `tr("Acciones post-ingesta")`, `tr("Al terminar")`, `tr("Operaciones")`
- **Riesgo:** tests: medio — `chk_format_sources`/`combo_format_mode` acoplados en `tests/test_wifi_source.py:353-354,364`; el agrupado no altera attrs ni estados. i18n: 3 strings nuevos. Estética: bajo — `QGroupBox` con QSS/tema existente.
- **Score:** 3.0 (5 − (2+2)/2) → **P1**
- **Orden:** P1-3 (contenedor de R-02..R-05, R-17 — precede a sus hijos)

**R-02 — `chk_format_sources` + `combo_format_mode` → subgrupo "Al terminar" (H-01 · D-07/D-09):**
- **Zona·Flujo:** D · f (formatear)
- **Control:** `chk_format_sources` ("Formatear orígenes al acabar:", D-02) + `combo_format_mode` ("Rápido"/"Completo", D-03)
- **Ubicación actual:** `app/ui/main_window.py:577-585`
- **Destino propuesto:** subgrupo "Al terminar" del grupo "Acciones post-ingesta"; confirmación de formateo (destructivo) si quedan errores pendientes (target `01-UI-SPEC.md:194`; confirmación existente `:1802`)
- **Strings nuevos:** — (labels existentes); confirmación con plantilla D-09 si procede
- **Riesgo:** tests: medio — `chk_format_sources` y `combo_format_mode` usados en `tests/test_wifi_source.py:353-354,364` (`isEnabled`); mantener attrs y estados. i18n: ninguno (labels existentes). Estética: bajo.
- **Score:** 2.5 (4 − (1+2)/2) → **P1**
- **Orden:** pendiente de confirmación D-09 (destructivo: formatea tarjetas) — no recibe orden de ejecución

**R-03 — `chk_shutdown` → subgrupo "Al terminar" (H-01 · D-07):**
- **Zona·Flujo:** D · f (formatear)
- **Control:** `chk_shutdown` ("Apagar al acabar", D-04)
- **Ubicación actual:** `app/ui/main_window.py:589-591`
- **Destino propuesto:** subgrupo "Al terminar" del grupo "Acciones post-ingesta"; confirmación explícita de apagado (acción irreversible del equipo) (target `01-UI-SPEC.md:195`; confirmación existente `:1837-1842`)
- **Strings nuevos:** — (label existente); confirmación con plantilla D-09
- **Riesgo:** tests: bajo — `chk_shutdown` no acoplado a tests. i18n: ninguno. Estética: bajo.
- **Score:** 2.5 (4 − (1+2)/2) → **P1**
- **Orden:** pendiente de confirmación D-09 (destructivo: apaga el equipo) — no recibe orden de ejecución

**R-04 — `btn_reorganize` → subgrupo "Operaciones" + siempre visible (H-01 · D-07):**
- **Zona·Flujo:** D · r (reorganizar)
- **Control:** `btn_reorganize` ("Reorganizar por metadatos", D-01)
- **Ubicación actual:** `app/ui/main_window.py:570-573`; **oculto salvo modo auto** (`setVisible(is_auto)` `:1216`)
- **Destino propuesto:** subgrupo "Operaciones"; siempre visible (eliminar `setVisible(is_auto)`); confirmación si hay archivos en `Unknown_Camera` (target `01-UI-SPEC.md:196`)
- **Strings nuevos:** — (ninguno)
- **Riesgo:** tests: bajo — `btn_reorganize` no acoplado a tests; eliminar el `setVisible` condicional requiere verificar el flujo de detección no-auto. i18n: ninguno. Estética: medio — el botón pasa a estar siempre presente en el layout.
- **Score:** 2.0 (4 − (1+3)/2) → **P2**
- **Orden:** P2-6 (flujo reorganizar)

**R-05 — `btn_clear_completed` → subgrupo "Operaciones" (H-01 · D-07):**
- **Zona·Flujo:** D · r (reorganizar)
- **Control:** `btn_clear_completed` ("Limpiar completados", A-42/D-05)
- **Ubicación actual:** dentro de `stats_row` junto a los contadores — `app/ui/main_window.py:560-563`
- **Destino propuesto:** subgrupo "Operaciones" del grupo "Acciones post-ingesta" (sale de `stats_row`) (target `01-UI-SPEC.md:136`)
- **Strings nuevos:** — (ninguno)
- **Riesgo:** tests: bajo — `btn_clear_completed` no acoplado a tests. i18n: ninguno. Estética: bajo.
- **Score:** 1.5 (3 − (1+2)/2) → **P2**
- **Orden:** P2-7 (flujo reorganizar)

**R-17 — Entrada visible "Volcado selectivo…" (H-07, hallazgo nuevo):**
- **Zona·Flujo:** D · r (reorganizar)
- **Control:** `_open_selective_dump` (D-07) + menú contextual de `table` (D-08)
- **Ubicación actual:** `_open_selective_dump` definido en `app/ui/main_window.py:3671-3687` pero **sin wiring** (grep: 1 solo match = la definición, ningún `clicked.connect`); menú contextual de `table` solo con "Eliminar completados" (`:1882-1886`); el botón por fila "Contenido" solo abre el modo filter (`:2052-2067` → `_open_content_filter` `:3689-3710`)
- **Destino propuesto:** botón "Volcado selectivo…" en el grupo "Acciones post-ingesta" → "Operaciones" (conectar `_open_selective_dump`) **y** mantener el menú contextual — ambos accesibles (targets `01-UI-SPEC.md:186,198`)
- **Strings nuevos:** `tr("Volcado selectivo…")`
- **Riesgo:** tests: medio — `SelectiveDumpAssistant` cubierto por `tests/test_selective_dump.py`; el wiring nuevo añade una entrada, no toca el asistente. i18n: 1 string nuevo. Estética: bajo.
- **Score:** 1.0 (3 − (2+2)/2) → **P2**
- **Orden:** P2-8 (flujo reorganizar; depende de R-01, su contenedor)

**Strings nuevos del contrato (12, UI-SPEC:112) — listados sin implementar (v2 los implementará con `tr()` en los módulos destino):**

| String (ES, `tr()`) | Ítems |
|---------------------|-------|
| `tr("Añadir origen…")` | R-12 |
| `tr("Dispositivos guardados")` | R-12 |
| `tr("Dispositivos desconectados")` | R-12, R-15 |
| `tr("Descripción del proyecto")` | R-10 |
| `tr("Acciones post-ingesta")` | R-01 |
| `tr("Al terminar")` | R-01 (subgrupo) |
| `tr("Operaciones")` | R-01 (subgrupo) |
| `tr("Eliminar origen…")` | R-07 |
| `tr("Eliminar sesión…")` | R-08 |
| `tr("Eliminar proyecto…")` | R-09 |
| `tr("Volcado selectivo…")` | R-17 |
| `tr("Eliminar <elemento>")` (plantilla de confirmación D-09) | R-07, R-08, R-09 (y R-02/R-03 si aplica) |

## Riesgos y dependencias

**Tests acoplados a widgets (prohibición de renombrar, `01-UI-SPEC.md:122`):** los 20 attrs públicos congelados (`btn_start`, `table`, `source_list`, `combo_format_mode`, `chk_generate_proxies`, `proxy_resolution`, `sessions_combo`, `chk_session_delicate`, `project_combo`, `source_input`, `btn_browse_source`, `btn_receive_wifi`, `desc_input`, `btn_remove_source`, `btn_delete_session`, `btn_delete_project`, `btn_reorganize`, `chk_format_sources`, `chk_shutdown`, `btn_clear_completed`) no se renombran; los ítems solo mueven/agrupan/reordenan (D-03). Acoples verificados: `sessions_combo`+`_refresh_sessions_combo` (`tests/test_source_content.py:142-145`, `tests/test_wifi_source.py:373,388-389`), `chk_format_sources`+`combo_format_mode` (`tests/test_wifi_source.py:353-354,364`), `btn_receive_wifi` (`:96,101`), `WifiMethodDialog` mockeado (`:721,731`), `list_widget` (`tests/test_source_picker.py:28-29,67-68`), `source_list`/`table`/`btn_start` (E2E). El gate de cero código (tarea 3) verifica que `tests/` no cambia en esta fase.

**i18n (T-03-03):** los strings UI son literales en español vía `tr()`; el catálogo EN va por `.ts`/`.qm`. **No se regenera el catálogo** en esta fase (no ejecutar `tools/update_translations.ps1` ni `tools/translate_en.py` — romperían la línea base i18n). Los 12 strings nuevos del contrato se listan sin implementar (tabla al final de §3).

**Estética:** se mantienen tema oscuro/claro + acentos existentes (PROJECT.md). Ningún ítem introduce iconos nuevos ni amplía la reserva de `accent`; los contenedores nuevos (`QGroupBox`, `QTabWidget`) usan tokens QSS existentes de `app/ui/theme.py`.

**Dependencias entre reubicaciones:**
- **R-01 → R-02, R-03, R-04, R-05, R-17:** el grupo "Acciones post-ingesta" es el contenedor de sus ítems; se crea primero.
- **R-12 → R-13, R-14, R-15, R-16:** el diálogo unificado "Añadir origen" (D-12) precede a sus pestañas/secciones e invocaciones (dependencia declarada, `01-UI-SPEC.md:252`).
- **R-10 ← C-03 `desc_input`:** reutiliza el dato ya capturado por `ProjectWizard` (guardado en `:1191,3647`); no mueve el control del wizard, solo añade el display en el dashboard.
- **R-17 ← `_open_selective_dump`:** wiring de una entrada existente (`main_window.py:3671-3687`); no toca `SelectiveDumpAssistant`.

**Discrepancia D-12 (documentada para revisión humana en el plan 04):** la tabla target-state de `01-UI-SPEC.md` marca el cluster D-12 (filas `:131,174-177`) como **P1**, pero la fórmula D-06 con Esfuerzo = 5 (definicional para D-12, `:249` — toca `main_window.py` + `source_picker.py` + `device_picker.py`) arroja Score 1.0 → **P2**. Este plan aplica la fórmula (vínculo must-haves: la banda se deriva del Score) y ordena el cluster al inicio de P2 (P2-2..P2-5). La discrepancia queda pendiente de confirmación del operador en el checkpoint del plan 04 (§5).

## Estado de aprobación

**Checklist de aprobación (los rellena el operador en el plan 04):**

- [ ] Apruebo las bandas P1/P2/P3 y el orden propuesto (P1: R-10 → R-06 → R-01; P2: R-11 → R-12 → R-13 → R-14 → R-15 → R-04 → R-05 → R-17; P3: R-16)
- [ ] Apruebo los ítems destructivos R-02, R-03, R-07, R-08, R-09 (patrón D-09) — al aprobarlos reciben orden dentro de su flujo
- [ ] Reviso la discrepancia D-12 (fórmula → P2 vs. target-state → P1) y decido si se mantiene la banda de la fórmula

**Estado por banda (patrón tabla de progreso):**

| Banda | Ítems | Estado |
|-------|-------|--------|
| P1 (≥ 2.5) | 5 | Pendiente de aprobación (plan 04) |
| P2 (1.0–2.4) | 11 | Pendiente de aprobación (plan 04) |
| P3 (< 1.0) | 1 | Pendiente de aprobación (plan 04) |

**Aprobación por ítem (checklist `- [ ]`, pendiente hasta aprobación del usuario):**

- [ ] R-01 — Grupo "Acciones post-ingesta" (P1)
- [ ] R-02 — Formatear orígenes → "Al terminar" (P1 · destructivo, D-09)
- [ ] R-03 — Apagar al acabar → "Al terminar" (P1 · destructivo, D-09)
- [ ] R-04 — Reorganizar → "Operaciones" + siempre visible (P2)
- [ ] R-05 — Limpiar completados → "Operaciones" (P2)
- [ ] R-06 — Apilado vertical de sesiones (P1)
- [ ] R-07 — "Eliminar origen…" en menú contextual (P2 · destructivo, D-09)
- [ ] R-08 — "Eliminar sesión…" (P2 · destructivo, D-09)
- [ ] R-09 — "Eliminar proyecto…" con confirmación (P2 · destructivo, D-09)
- [ ] R-10 — Línea "Descripción del proyecto" (P1)
- [ ] R-11 — Columnas de `source_list` Interactive + persistencia (P2)
- [ ] R-12 — Diálogo unificado "Añadir origen" (P2)
- [ ] R-13 — Pestaña "Dispositivos" MTP (P2)
- [ ] R-14 — Pestaña "Dispositivos" FTP (P2)
- [ ] R-15 — Zona "Dispositivos desconectados" (P2)
- [ ] R-16 — `WifiMethodDialog` mantenido (P3)
- [ ] R-17 — Entrada "Volcado selectivo…" (P2)

---

*Plan de reubicación: 2026-08-15*
