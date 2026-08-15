# Fase 1: Inventario de Widgets

**Elaborado:** 2026-08-15
**Estado:** draft

## Método

Inventario por **lectura de widgets** (D-04): grep dirigido por atributo público con el patrón `self\.<attr> = Q…` en `app/ui/*.py`, verificando cada cita con lectura del rango correspondiente. Los controles se nombran por su **atributo público** porque así los referencian los tests (`btn_start`, `table`, `source_list` — `tests/test_e2e.py:77,95,101`). Cada fila incluye el tipo Qt y el texto/label tal como aparece en el código; las citas `archivo:línea` usan backticks con rango `inicio-fin` cuando el widget se configura en varias líneas.

**Leyenda de zonas y flujos:** las columnas `ubicación` comienzan con la abreviatura `Z·f` donde **zona** A=ventana principal/dashboard, B=pickers de fuente, C=asistentes y paneles, D=acciones post-ingesta; y **flujo** c=conectar, i=ingestar, f=formatear, r=reorganizar (D-01). Se respeta la regla de máximo 5 columnas por tabla (UI-SPEC overflow).

## Zona A — Ventana principal / dashboard

Controles de `setup_views` en `app/ui/main_window.py:261-620`: header bar (proyecto, estado), orígenes, sesiones, acciones de ingesta, progreso, tabla de archivos.

| ID | attr | tipo Qt | texto/label | ubicación |
|----|------|---------|-------------|-----------|
| A-01 | `app_label` | QLabel | "CosechaMedia" | A·g · `app/ui/main_window.py:275-277` |
| A-02 | (label estático) | QLabel | "Proyecto:" | A·g · `app/ui/main_window.py:280` |
| A-03 | `project_combo` | QComboBox | selector de proyecto (min 160px) | A·g · `app/ui/main_window.py:281-284` |
| A-04 | `btn_refresh_projects` | QPushButton (IconButton) | "⟳" · tooltip "Actualizar proyectos" | A·g · `app/ui/main_window.py:287,294-307` |
| A-05 | `btn_new_project` | QPushButton (IconButton) | "+" · tooltip "Nuevo proyecto" | A·g · `app/ui/main_window.py:288,294-307` |
| A-06 | `btn_delete_project` | QPushButton (IconButton) | "×" · tooltip "Eliminar proyecto" · deshabilitado sin proyecto | A·g · `app/ui/main_window.py:289,308` |
| A-07 | `btn_rename_project` | QPushButton (IconButton) | "✎" · tooltip "Renombrar proyecto" | A·g · `app/ui/main_window.py:290,309` |
| A-08 | `btn_duplicate_project` | QPushButton (IconButton) | "⧉" · tooltip "Duplicar proyecto" | A·g · `app/ui/main_window.py:291,310` |
| A-09 | `btn_browse_root` | QPushButton (IconButton) | "📁" · tooltip "Cambiar ruta maestra del proyecto" | A·g · `app/ui/main_window.py:292,294-307` |
| A-10 | `project_path_label` | QLabel | ruta raíz del proyecto (accent, max 420px) | A·g · `app/ui/main_window.py:314-319` |
| A-11 | `btn_show_metadata` | QPushButton (IconButton) | "⚙" · tooltip "Configuración" | A·g · `app/ui/main_window.py:323-332` |
| A-12 | `status_indicator` | QLabel | indicador de estado 8×8 | A·g · `app/ui/main_window.py:336-339` |
| A-13 | `status_text` | QLabel | "Listo" (text_secondary, 10px) | A·g · `app/ui/main_window.py:341-343` |
| A-14 | (label estático) | QLabel | "Orígenes:" | A·c · `app/ui/main_window.py:364-367` |
| A-15 | `btn_remove_source` | QPushButton (IconButton) | "🗑" · tooltip "Eliminar origen seleccionado" · deshabilitado sin selección | A·c · `app/ui/main_window.py:368-374` |
| A-16 | `source_input` | QComboBox (editable) | placeholder "E:\DCIM..." · entrada de origen personalizado | A·c · `app/ui/main_window.py:378-382` |
| A-17 | `btn_browse_source` | QPushButton | "Examinar" | A·c · `app/ui/main_window.py:384-386` |
| A-18 | `btn_receive_wifi` | QPushButton | "WiFi…" · tooltip "Recibir archivos de un móvil por WiFi (QR o FTP)" · deshabilitado sin proyecto | A·c · `app/ui/main_window.py:388-392` |
| A-19 | `source_list` | QTableWidget | columnas "Ruta de origen"/"Cámara"/"Contenido" · col0 Stretch, col1 Fixed 140, col2 Fixed 180 · min 60 / max 120 | A·c · `app/ui/main_window.py:396-418` |
| A-20 | `btn_detect_drives` | QPushButton | "⟳ Detectar" · tooltip "Detectar unidades extraíbles" | A·c · `app/ui/main_window.py:421-424` |
| A-21 | `btn_scan_cameras` | QPushButton | "📷 Escanear cámaras" | A·c · `app/ui/main_window.py:425-428` |
| A-22 | (label estático) | QLabel | "Sesiones:" | A·i · `app/ui/main_window.py:434-436` |
| A-23 | `sessions_combo` | QComboBox | selector de sesión (min 160 / **max 360** · `SizeAdjustPolicy`) | A·i · `app/ui/main_window.py:439-444` |
| A-24 | `btn_new_session` | QPushButton (IconButton) | "+" · tooltip "Nueva sesión" | A·i · `app/ui/main_window.py:446-451` |
| A-25 | `btn_delete_session` | QPushButton (IconButton) | "−" · tooltip "Eliminar sesión" · deshabilitado sin sesión | A·i · `app/ui/main_window.py:453-459` |
| A-26 | `session_src_label` | QLabel | origen de la sesión activa (max 240px) | A·i · `app/ui/main_window.py:461-466` |
| A-27 | `_btn_browse_sess_src` | QPushButton (IconButton) | "📁" · tooltip "Examinar origen de sesión…" | A·i · `app/ui/main_window.py:468-473` |
| A-28 | (label estático) | QLabel | "Destino:" | A·i · `app/ui/main_window.py:476` |
| A-29 | `session_dest_combo` | QComboBox | "Por defecto" / "Personalizado" (fixed 110px) | A·i · `app/ui/main_window.py:477-481` |
| A-30 | `session_dest_path` | QLineEdit | placeholder "Ruta..." (fixed 200px, oculto salvo "Personalizado") | A·i · `app/ui/main_window.py:483-488` |
| A-31 | `_btn_browse_sess_dest` | QPushButton (IconButton) | "📁" · tooltip "Examinar..." (oculto salvo "Personalizado") | A·i · `app/ui/main_window.py:490-496` |
| A-32 | `chk_session_delicate` | QCheckBox | "Modo delicado" | A·i · `app/ui/main_window.py:498-500` |
| A-33 | `btn_start` | QPushButton (PrimaryAction) | "INICIAR INGESTA" · min height 36 · deshabilitado sin configuración | A·i · `app/ui/main_window.py:507-511` |
| A-34 | `btn_stop` | QPushButton (DangerAction) | "DETENER" · min height 36 · deshabilitado por defecto | A·i · `app/ui/main_window.py:513-517` |
| A-35 | `ingest_status_label` | QLabel | estado de ingesta (italic, 10px) | A·i · `app/ui/main_window.py:523-525` |
| A-36 | `progress_bar` | QProgressBar | formato "%v / %m archivos" · min height 18 | A·i · `app/ui/main_window.py:528-532` |
| A-37 | `chk_generate_proxies` | QCheckBox | "Generar proxies" · tooltip "Genera proxies de los clips de video tras la ingesta" | A·i · `app/ui/main_window.py:536-538` |
| A-38 | `proxy_resolution` | QComboBox | "720p" / "1080p" · deshabilitado hasta marcar proxies | A·i · `app/ui/main_window.py:539-543,547` |
| A-39 | `lbl_files_processed` | QLabel | "0 procesados" (success, bold, 10px) | A·i · `app/ui/main_window.py:550-551` |
| A-40 | `lbl_files_pending` | QLabel | "0 pendientes" (warning, bold, 10px) | A·i · `app/ui/main_window.py:552-553` |
| A-41 | `lbl_files_errors` | QLabel | "0 errores" (danger, bold, 10px) | A·i · `app/ui/main_window.py:554-555` |
| A-42 | `btn_clear_completed` | QPushButton | "Limpiar completados" · en `stats_row` | A·i · `app/ui/main_window.py:560-563` |
| A-43 | `table` | QTableWidget (0×5) | columnas "Archivo"/"Cámara"/"Estado"/"Progreso"/"Destino" · Interactive + stretch última · ordenable · menú contextual | A·i · `app/ui/main_window.py:598-614` |

## Zona B — Pickers de fuente

Diálogos de selección de origen/dispositivo/servidor (flujo conectar). Shell de diálogo: hint + contenido + label de selección + `[Aceptar (PrimaryAction) | Cancelar]`.

| ID | attr | tipo Qt | texto/label | ubicación |
|----|------|---------|-------------|-----------|
| B-01 | (diálogo) | QDialog | título "Seleccionar origen" · min width 460 | B·c · `app/ui/source_picker.py:18,33-35` |
| B-02 | `hint` | QLabel | "Elige un origen guardado para la sesión o explora una carpeta:" | B·c · `app/ui/source_picker.py:42-45` |
| B-03 | `list_widget` | QListWidget | secciones "Carpetas guardadas" / "Remitentes WiFi" / "Dispositivos FTP guardados" | B·c · `app/ui/source_picker.py:47-54,70-78` |
| B-04 | `browse_btn` | QPushButton | "Examinar…" | B·c · `app/ui/source_picker.py:57-59` |
| B-05 | botonera | QPushButton | "Cancelar" / "Aceptar" (PrimaryAction) | B·c · `app/ui/source_picker.py:61-67` |
| B-06 | (diálogo) | QDialog | título "Seleccionar carpeta del dispositivo" | B·c · `app/ui/device_picker.py:16,34` |
| B-07 | `device_combo` | QComboBox | "Dispositivo:" · min width 260 | B·c · `app/ui/device_picker.py:54-58` |
| B-08 | `refresh_btn` | QPushButton | "Actualizar" | B·c · `app/ui/device_picker.py:59-61` |
| B-09 | `tree` | QTreeWidget | árbol de carpetas del dispositivo | B·c · `app/ui/device_picker.py:64,70` |
| B-10 | `selection_label` | QLabel | ruta seleccionada | B·c · `app/ui/device_picker.py:72-76` |
| B-11 | `ok_btn` | QPushButton (PrimaryAction) | "Aceptar" · deshabilitado sin selección | B·c · `app/ui/device_picker.py:79-82` |
| B-12 | (diálogo) | QDialog | título "Importar por WiFi (FTP)" | B·c · `app/ui/ftp_picker.py:53,71` |
| B-13 | `profile_combo` | QComboBox | "Servidor guardado:" · "— Añadir nuevo servidor —" + perfiles | B·c · `app/ui/ftp_picker.py:93-97,189-192` |
| B-14 | `name_edit` | QLineEdit | nombre del servidor | B·c · `app/ui/ftp_picker.py:102` |
| B-15 | `host_edit` | QLineEdit | host/IP | B·c · `app/ui/ftp_picker.py:105-107` |
| B-16 | `detect_btn` | QPushButton | "Detectar en la red…" | B·c · `app/ui/ftp_picker.py:108-111` |
| B-17 | `port_spin` | QSpinBox | puerto | B·c · `app/ui/ftp_picker.py:113` |
| B-18 | `user_edit` | QLineEdit | "user" | B·c · `app/ui/ftp_picker.py:117` |
| B-19 | `pass_edit` | QLineEdit | contraseña | B·c · `app/ui/ftp_picker.py:119` |
| B-20 | `base_edit` | QLineEdit | ruta base | B·c · `app/ui/ftp_picker.py:122` |
| B-21 | `passive_check` | QCheckBox | "Modo pasivo (recomendado)" | B·c · `app/ui/ftp_picker.py:125` |
| B-22 | `connect_btn` | QPushButton | "Conectar" | B·c · `app/ui/ftp_picker.py:131-134` |
| B-23 | `conn_status` | QLabel | estado de conexión | B·c · `app/ui/ftp_picker.py:135-138` |
| B-24 | `tree` | QTreeWidget | árbol de carpetas del servidor | B·c · `app/ui/ftp_picker.py:141-147` |
| B-25 | `guide_btn` | QPushButton | "Cómo conectar (guía paso a paso)" | B·c · `app/ui/ftp_picker.py:149-153` |
| B-26 | `guide_text` | QTextEdit | guía extensa colapsable | B·c · `app/ui/ftp_picker.py:154-161` |
| B-27 | `selection_label` | QLabel | ruta seleccionada | B·c · `app/ui/ftp_picker.py:163-166` |
| B-28 | `ok_btn` | QPushButton (PrimaryAction) | "Aceptar" · deshabilitado sin selección | B·c · `app/ui/ftp_picker.py:169-172` |
| B-29 | (diálogo) | QDialog | título "Recibir por WiFi" · min width 480 | B·c · `app/ui/wifi_picker.py:13,22-24` |
| B-30 | `hint` | QLabel | "¿Cómo quieres recibir los archivos de los móviles?" | B·c · `app/ui/wifi_picker.py:31-33` |
| B-31 | `btn_pairdrop` | QPushButton (card, PrimaryAction) | "PairDrop — Compatible con Android/iOS. Sin instalar nada…" · min height 68 | B·c · `app/ui/wifi_picker.py:35-42,59-66` |
| B-32 | `btn_ftp` | QPushButton (card) | "FTP Clásico — Avanzado. El dispositivo ejecuta un servidor FTP…" · min height 68 | B·c · `app/ui/wifi_picker.py:44-50,59-66` |

## Zona C — Asistentes y paneles

Asistentes y paneles de flujo completo (proyecto, volcado selectivo, recepción WiFi, acerca/actualizaciones).

| ID | attr | tipo Qt | texto/label | ubicación |
|----|------|---------|-------------|-----------|
| C-01 | (wizard) | QWidget | título "Nuevo Proyecto" · min 600×520 | C·c · `app/ui/project_wizard.py:10,18-20` |
| C-02 | `name_input` | QLineEdit | grupo "Nombre del Proyecto" · placeholder "Ej: Rodaje_Cine_01" · min height 36 | C·c · `app/ui/project_wizard.py:33-38` |
| C-03 | `desc_input` | QLineEdit | grupo "Descripción (Opcional)" · placeholder "Breve descripción del proyecto..." · min height 36 | C·c · `app/ui/project_wizard.py:41-46` |
| C-04 | `dest_input` | QLineEdit | grupo "Ruta de Destino" · placeholder "Ej: H:/Produccion/Proyectos" · min height 36 | C·c · `app/ui/project_wizard.py:49-54` |
| C-05 | `radio_one_day` | QRadioButton | "Un solo día" · marcado por defecto | C·c · `app/ui/project_wizard.py:64-66` |
| C-06 | `radio_multiple_days` | QRadioButton | "Múltiples días" | C·c · `app/ui/project_wizard.py:68-69` |
| C-07 | `radio_no_date` | QRadioButton | "Sin fecha" | C·c · `app/ui/project_wizard.py:71-72` |
| C-08 | `org_combo` | QComboBox | grupo "Organización" · "Cámara primero (Cámara/Fecha)" / "Fecha primero (Fecha/Cámara)" / "Solo por cámara" / "Sin subcarpetas" | C·c · `app/ui/project_wizard.py:83-94` |
| C-09 | `chk_use_metadata_date` | QCheckBox | "Usar fecha de metadatos" · marcado por defecto | C·c · `app/ui/project_wizard.py:96-99` |
| C-10 | `btn_finish` | QPushButton (PrimaryAction) | "Crear Proyecto" · min height 44 | C·c · `app/ui/project_wizard.py:113-117` |
| C-11 | (asistente) | QDialog | título "Volcado selectivo por fecha" (modo dump) / "Seleccionar contenido del origen" (modo filter) | C·r · `app/ui/selective_dump.py:337,345-347` |
| C-12 | `_stack` | QStackedWidget | 4 páginas: setup / scan / select / dump | C·r · `app/ui/selective_dump.py:374-386` |
| C-13 | `btn_scan` | QPushButton (PrimaryAction) | "Escanear" | C·r · `app/ui/selective_dump.py:413-416` |
| C-14 | `scan_progress` | QProgressBar | progreso de escaneo · min height 22 | C·r · `app/ui/selective_dump.py:432-434` |
| C-15 | `btn_scan_cancel` | QPushButton | "Cancelar" | C·r · `app/ui/selective_dump.py:445-447` |
| C-16 | `calendar` | DateSelectCalendar (QCalendarWidget) | selección múltiple de días · leyenda "con archivos"/"seleccionado" | C·r · `app/ui/selective_dump.py:468-470,472-484,126` |
| C-17 | `btn_select_all` | QPushButton | "Seleccionar todo" | C·r · `app/ui/selective_dump.py:487-489` |
| C-18 | `btn_clear` | QPushButton | "Limpiar" | C·r · `app/ui/selective_dump.py:490-492` |
| C-19 | `preview_table` | QTableWidget (0×4) | columnas "Archivo"/"Fecha"/"Tamaño"/"Tipo" · col0 Stretch | C·r · `app/ui/selective_dump.py:507-517` |
| C-20 | `chk_include_nodate` | QCheckBox | "Incluir archivos sin fecha (se volcarán con la fecha de hoy)" | C·r · `app/ui/selective_dump.py:523-524` |
| C-21 | `btn_dump` | QPushButton (PrimaryAction) | "Volcar selección" (dump) / "Aplicar selección" (filter) | C·r · `app/ui/selective_dump.py:534-542` |
| C-22 | `dump_progress` | QProgressBar | progreso de volcado · min height 22 | C·r · `app/ui/selective_dump.py:557-559` |
| C-23 | `btn_dump_cancel` | QPushButton | "Detener" | C·r · `app/ui/selective_dump.py:570-572` |
| C-24 | (panel) | QWidget (Qt.Window) | título "Recibir por WiFi (PairDrop)" · 420×460 | C·c · `app/ui/wifi_panel.py:66,81-87` |
| C-25 | `qr_label` | QLabel | QR 260×260 · fondo blanco · centrado | C·c · `app/ui/wifi_panel.py:102-107` |
| C-26 | `url_label` | QLabel (mono) | URL del servidor · font `'Cascadia Mono', Consolas, monospace` · seleccionable | C·c · `app/ui/wifi_panel.py:111-119` |
| C-27 | `copy_btn` | QPushButton | "Copiar" · tooltip "Copiar enlace" | C·c · `app/ui/wifi_panel.py:121-124` |
| C-28 | `status_label` | QLabel | estado del servidor (bold) | C·c · `app/ui/wifi_panel.py:127-130` |
| C-29 | `folder_mode_cb` | QCheckBox | "Enviar una carpeta entera (modo carpeta)" | C·c · `app/ui/wifi_panel.py:141-144` |
| C-30 | `stop_btn` | QPushButton (DangerAction) | "Detener" / "Reanudar" según estado | C·c · `app/ui/wifi_panel.py:150-153` |
| C-31 | `close_btn` | QPushButton | "Cerrar" (oculta el panel, el servidor sigue) | C·c · `app/ui/wifi_panel.py:154-156` |
| C-32 | (diálogo) | QDialog | título "Acerca de CosechaMedia" | C·g · `app/ui/about_dialog.py:72,83` |
| C-33 | `tabs` | QTabWidget | pestañas "Acerca" / "Actualizaciones" | C·g · `app/ui/about_dialog.py:86-92` |
| C-34 | `lbl_current` | QLabel | versión actual instalada | C·g · `app/ui/about_dialog.py:167-170` |
| C-35 | `btn_check` | QPushButton | "Comprobar ahora" | C·g · `app/ui/about_dialog.py:177-179` |
| C-36 | `btn_download` | QPushButton | "Descargar e instalar" · deshabilitado por defecto | C·g · `app/ui/about_dialog.py:181-185` |
| C-37 | `progress` | QProgressBar | progreso de descarga | C·g · `app/ui/about_dialog.py:187-189` |
| C-38 | `chk_auto` | QCheckBox | "Buscar actualizaciones al inicio" | C·g · `app/ui/about_dialog.py:192-195` |

## Zona D — Acciones post-ingesta

Fila final de la columna izquierda bajo `stats_row` (`main_window.py:566-593`), más la entrada de volcado selectivo. Acciones que se ejecutan al cierre del ciclo de operador (flujo formatear/reorganizar).

| ID | attr | tipo Qt | texto/label | ubicación |
|----|------|---------|-------------|-----------|
| D-01 | `btn_reorganize` | QPushButton | "Reorganizar por metadatos" · tooltip "Reorganiza los archivos en 'Unknown_Camera' detectando su cámara por metadatos" | D·r · `app/ui/main_window.py:570-573` |
| D-02 | `chk_format_sources` | QCheckBox | "Formatear orígenes al acabar:" · tooltip "Formatea las unidades de origen al acabar el volcado y la comprobación" | D·f · `app/ui/main_window.py:577-579,585` |
| D-03 | `combo_format_mode` | QComboBox | "Rápido" / "Completo" · fixed 100px · deshabilitado hasta marcar formatear | D·f · `app/ui/main_window.py:580-585` |
| D-04 | `chk_shutdown` | QCheckBox | "Apagar al acabar" · tooltip "Apaga el ordenador al finalizar todas las tareas de ingesta" | D·f · `app/ui/main_window.py:589-591` |
| D-05 | `btn_clear_completed` | QPushButton | "Limpiar completados" · en `stats_row` (mismo control que A-42) | D·r · `app/ui/main_window.py:560-563` |
| D-06 | botón por fila "Contenido" | QPushButton | resumen del filtro de contenido (ej. "3 días · sin fecha") → abre `SelectiveDumpAssistant` en modo filter | D·r · `app/ui/main_window.py:2052-2067,3689-3710` |
| D-07 | `_open_selective_dump` | (método, sin wiring directo) | entrada de volcado selectivo en modo dump (requiere proyecto + origen) | D·r · `app/ui/main_window.py:3671-3687` |
| D-08 | menú contextual de `table` | QMenu | "Eliminar completados" (única acción) | D·r · `app/ui/main_window.py:1882-1886` |

## Anclas de hallazgos confirmados

Mapeo de cada decisión confirmada por el usuario (01-CONTEXT.md:26-32) a las filas del inventario que la evidencian.

| Decisión | Hallazgo (01-CONTEXT.md) | Filas que evidencian |
|----------|--------------------------|----------------------|
| D-07 | Zona post-ingesta visualmente secundaria y desordenada: formateo/proxies/reorganizar mezclados sin jerarquía | D-01, D-02, D-03, D-04, D-05, D-06 |
| D-08 | Panel de sesiones crece a la derecha y come ancho de ventana; el espacio vertical libre no se aprovecha | A-23 (max 360), A-26, A-27, A-29, A-30, A-31, A-32 |
| D-09 | Botones de eliminar mal ubicados y presentados de forma genérica (sesión ≠ origen ≠ proyecto) | A-06 (`btn_delete_project`), A-15 (`btn_remove_source`), A-25 (`btn_delete_session`) |
| D-10 | Descripción del proyecto capturada en el wizard pero nunca mostrada después — dato muerto | C-03 (`desc_input`) |
| D-11 | Columnas de `source_list` de ancho fijo sin posibilidad de redimensionar | A-19 (`source_list`: col1/col2 Fixed, `app/ui/main_window.py:400-405`) |
| D-12 | Duplicado "guardar dispositivos": origen personalizado de sesión vs. dispositivos guardados son dos flujos separados que parecen lo mismo | A-16, A-17, A-18 (entrada de origen manual) + B-01..B-05 (`SourcePickerDialog`) + B-06..B-11 (`DevicePickerDialog`) + B-12..B-28 (`FtpPickerDialog`) + B-29..B-32 (`WifiMethodDialog`) |

---

*Inventario de widgets: 2026-08-15*
