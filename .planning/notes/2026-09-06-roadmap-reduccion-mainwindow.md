---
date: "2026-09-06 09:15"
plan_type: refactor-roadmap
target: app/ui/main_window.py
status: planned
---

# Roadmap de reducción de `main_window.py`

## Estado actual (2026-09-06, tras quick 260906-ci2)

- **4.589 líneas**, **138 métodos** en `MainWindow(QMainWindow, WifiMixin)`.
- Ya extraídos a `app/ui/mixins/`: `WifiMixin` (29 métodos) y `workers.py`
  (`_StageWorker`, `_TaskWorker`, `DashboardBackground`).
- Helper de nivel de módulo restantes en `main_window.py`: `ORG_TYPE_MAP`,
  `_format_drive`, `_format_sources_worker`, `_generate_proxies_worker`,
  `_reorganize_worker` (no-op muerto D-18), `_probe_device_connectivity`.

## Objetivo

Llevar `main_window.py` de 4.589 → **~1.300-1.500 líneas** (una clase `MainWindow`
que solo orquesta: `__init__`, `setup_views` descompuesto, start/stop, closeEvent
y delegación a mixins/diálogos). Todo siguiendo los dos patrones ya validados:

1. **Composición por mixins por dominio** (`class MainWindow(QMainWindow, WifiMixin, SessionsMixin, ...)`) — estado `self.*` compartido en la misma instancia.
2. **Diálogos a ficheros propios** (patrón `AboutDialog`, `FtpPickerDialog`, `AddSourceDialog`).

**Contrato duro en cada paso: refactor puro, cero cambio de comportamiento.**
Métodos movidos VERBATIM; test patching adaptado solo cuando un singleton se
resuelve desde un namespace nuevo (patrón `wifi_mixin_module.db`, ya usado para
`ingestor_module.db`).

## Vectores de extracción en orden recomendado

### Bloque 1 — Diálogos de configuración (cuatro diálogos inline, ~470 líneas)

Extraer los constructores de `QDialog` inline a ficheros propios en `app/ui/`.
Son bloques autocontenidos, cero riesgo de acoplamiento cruzado.

| Método actual | Líneas | Diálogo nuevo |
|---|---|---|
| `_show_metadata_dialog` | 726–882 (157) | `app/ui/project_settings_dialog.py` → `ProjectSettingsDialog` |
| `_show_camera_overrides_dialog` | 882–990 (109) | `app/ui/camera_overrides_dialog.py` → `CameraOverridesDialog` |
| `_show_names_manager` | 990–1098 (109) | `app/ui/names_manager_dialog.py` → `NamesManagerDialog` |
| `_manage_dump_locations` | 1119–1211 (93) | `app/ui/dump_locations_dialog.py` → `DumpLocationsDialog` |

Los métodos en `MainWindow` quedan como wrappers de 5-8 líneas:
`dlg = ProjectSettingsDialog(self); if dlg.exec(): ...` o incluso connection-only.
Clusters 1098–1119 (`_manage_footage_folders`, `_manage_containers`) pueden quedar
o pasar a un `StorageSettingsDialog` agrupado; decisión del ejecutor según la
forma final de los diálogos.

**Riesgo de tests:** estos diálogos son cableados por `test_main_window.py`
(`_show_metadata_dialog`, `_manage_dump_locations`). Si un test toca widgets del
diálogo por nombre, el test necesita apuntar al nuevo objeto. Verificar
`rg "_show_metadata_dialog|_manage_dump_locations" tests/`.

### Bloque 2 — `SessionsMixin` (~330 líneas)

Clúster de sesiones: 3019–3395 + `_open_content_filter` (4406–4431).

Métodos: `_refresh_sessions_combo`, `_reset_session_selection_ui`,
`_on_session_selected`, `_session_content_state`, `_window_value_unit_from_filter`,
`_window_days_from_filter`, `_window_filter_text`, `_update_session_dump_switch`,
`_cycle_session_content_mode`, `_open_session_dump_menu`, `_open_window_filter_dialog`,
`_add_manual_session`, `_delete_current_session`, `_on_session_dest_type_changed`,
`_save_session_override`, `_browse_session_dest`, `_browse_session_src`,
`_open_content_filter`.

Acoplamiento: `_browse_session_src` es el dispatcher más ancho (8 tipos de origen:
carpeta/wifi/ftp/device/USB). Llama a `_apply_source_choice`/`_bind_wifi_sender`/
`_pick_ftp_source`/`_assign_session_folder` via `self.*` — OK en instancia compuesta.
Mejor extraer tras `DevicesMixin`/`WifiMixin` (ya fuera WiFi) o al menos verificar que
los nombres existen en el MRO; no hay requisito de orden, solo de nombres presentes.

### Bloque 3 — `CameraMixin` (~340 líneas)

Clúster de detección/nombrado de cámara: 2167–2172 (`_on_camera_rename_needed`),
2259–2288 (`_post_ingest_rename_dialog`), 2650–2916 (helpers+detect+persist),
4449–4474 (`_detect_sd_card`).

Métodos: `_on_camera_rename_needed`, `_drive_label`, `_find_smallest_media`,
`_set_camera_cell_text`, `_camera_for_path`, `_detect_camera_for_session`,
`_prompt_nombre_dispositivo`, `_detect_camera_for_source`, `_persist_camera_mapping`,
`_on_camera_cell_edited`, `_on_dialog_camera_name_changed`, `_post_ingest_rename_dialog`,
`_detect_sd_card`.

Autocontenido (sd_reader, metadata_engine, DB, QTimer/QThread). Depende de `self.tr`,
`self.current_project_id`, `self._source_paths` — presentes en instancia compuesta.
Los métodos que construyen QDialog (`_prompt_nombre_dispositivo`,
`_post_ingest_rename_dialog`, `_on_dialog_camera_name_changed`) podrían migrar a un
`CameraNameDialog` en Bloque 1 si se quiere, pero coexisten bien como mixin.

### Bloque 4 — `SourcesMixin` (~460 líneas)

Clúster de la tabla de fuentes: 2172–2208 (menú contexto, clear, current_source),
2288–2627 (doble click, prompt path, refresh list, widgets builder, options),
2916–3019 (context menu, delete/remove/hide, event filter).

Métodos: `_show_table_context_menu`, `_clear_completed_rows`, `_current_source_path`,
`_on_source_double_clicked`, `_prompt_change_source_path`, `_prompt_rename_camera`,
`_refresh_source_list`, `_update_source_list_height`, `_build_status_label`,
`_update_source_status_cells`, `_build_path_widget`, `_disable_source_in_project`,
`_on_source_widget_check_changed`, `_build_options_widget`, `_toggle_device_delicate`,
`_build_remove_file_button`, `_remove_file_row`, `_show_source_context_menu`,
`_clear_source_list_selection`, `_source_list_event_filter`, `eventFilter`,
`_delete_source_at_row`, `_remove_source_path`, `_hide_source_path`,
`_on_source_check_changed`, `_export_integrity_report`, `_export_card_content_report`.

Acoplamiento alto con cámara, sesiones y dispositivos (`_on_source_widget_check_changed`
crea sesiones, detecta cámara, repara device_id). Verificar que `eventFilter` solo
exista una vez en el MRO (queda solo en SourcesMixin). Mejor extraer DESPUÉS de
SessionsMixin y CameraMixin.

### Bloque 5 — `ProjectMixin` (~450 líneas)

Ciclo de vida de proyectos: 1223–1401 (load/select/load/set desc/create/wizard),
1475–1564 (rename/duplicate), 4085–4403 (dest path, root change, move completed,
delete, prune, create default, open data folder).

Métodos: `load_existing_projects`, `on_project_selected`, `_load_project`,
`_set_project_description`, `_edit_project_description`, `_show_create_project`,
`_on_project_wizard_finished`, `_close_project_wizard`, `_rename_current_project`,
`_duplicate_current_project`, `select_dest_path`, `_save_project_root`,
`_completed_files_under_root`, `_handle_completed_files_on_root_change`,
`_move_completed_files`, `_delete_completed_file_records`, `_prune_empty_dirs`,
`delete_current_project`, `delete_all_projects`, `_create_default_project`,
`open_data_folder`.

Acoplamiento medio: `delete_current_project`/`delete_all_projects` llaman a
`_reset_mtp_thread_local`, `_reset_ingestors`, `_reset_wifi_ingestors`,
`update_start_button_state` (otros mixins) — resuelven por MRO. `_load_project` usa
`_populate_source_paths_from_sessions` (sources). Extraer tras Bloque 2-4.

### Bloque 6 — `DevicesMixin` (~480 líneas, el más valoroso tras WiFi)

Dos clústeres relacionados: add-source/registry (3575–3922) + MTP/FTP staging
(3922–4090).

Métodos: `_add_source_entry`, `_apply_source_choice`, `_pick_source_entry`,
`_delete_saved_source`, `_delete_all_saved_devices`, `_delete_all_known_cameras`,
`_open_known_devices`, `_disconnected_devices`, `_register_device_source_from_picker`,
`_assign_folder_source`, `_assign_session_folder`, `_repair_folder_device_id`,
`_warn_managed_source`, `_reconfigure_ftp_source`, `_reconfigure_mtp_source`,
`_show_ftp_status`, `_show_ftp_status_for_device`, `_reset_mtp_thread_local`,
`_reset_ingestors`, `_pick_ftp_source`, `_register_device_source`,
`_stage_device_in_background`, `_on_stage_progress`, `_on_stage_done`.

Acoplamiento: `_pick_source_entry`/`_browse_session_src` dispachan a
`_bind_wifi_sender`, `_assign_folder_source`, `_pick_ftp_source` (ya en WifiMixin /
este mixin). `_on_stage_done` llama a `_detect_camera_for_session` (CameraMixin).
Extraer tras Bloque 3-4 para tener los nombres en el MRO.

### Bloque 7 — `MenuMixin` (~170 líneas)

`build_menu` (3395–3557) + `_switch_language` (3557–3566). Dispatcher puro de
acciones del menú sobre el resto de métodos (`self._show_names_manager`,
`self._manage_dump_locations`, `self.start_ingest`, etc.) — todos resuelven por MRO.
Bajo riesgo.

### Bloque 8 — `IngestMixin` + post-ingest (~620 líneas, el más acoplado → ÚLTIMO)

Ingesta y acciones posteriores: 1564–2167 (start/stop/update, callbacks de señales,
finalize, acciones post-ingesta) + 4525–4584 (reorganize/proxies).

Métodos: `start_ingest`, `stop_ingest`, `prepare_for_update`, `on_file_started`,
`_file_row_key`, `on_copy_progress`, `on_file_finished`, `_on_ingestor_complete`,
`_finalize_ingest`, `_run_next_post_ingest_action`, `_is_managed_source_path`,
`_is_managed_session`, `update_status_from_watcher`, `_run_background`,
`_cleanup_background`, `_format_candidate_paths`, `_update_format_sources_state`,
`_format_sources_after_ingest`, `_on_format_finished`, `_shutdown_computer`,
`_generate_report_after_ingest`, `_reorganize_by_metadata`, `_on_reorganize_finished`,
`_proxy_resolution_height`, `_generate_proxies_after_ingest`, `_on_proxies_finished`.

Máximo grado de acoplamiento (start/finalize tocan proyectos, sesiones, fuentes,
WiFi, dispositivos). Extraer el ÚLTIMO, cuando todos los demás mixins existen, y puede
subdividirse en `IngestMixin` (pipeline) + `PostIngestMixin` (acciones) si conviene.

### Bloque 9 — `setup_views` descompuesto + limpieza de cierre

1. `setup_views` (438 líneas, 266–703): extraer constructores de sección
   `_build_header()`, `_build_dashboard()`, `_build_sources_table()`,
   `_build_sessions_box()`, `_build_progress_bar()`, `_build_footer()` — en el
   propio MainWindow o en un `ViewBuilder`/mixin `LayoutMixin`.
2. Limpieza final:
   - `_reorganize_worker` (no-op muerto D-18) → eliminar.
   - `_on_session_dest_type_changed` (no-op vacío) → eliminar o justificar.
   - Imports muertos que quedaron tras extracciones de WiFi y sucesivas
     (`_is_system_entry`, `create_folder_structure`, `QObject`/`Signal`/`QSize`/
     `QPropertyAnimation`/`QFrame`/`QStackedWidget`/`QDateEdit`/`QSplashScreen`/
     `QSystemTrayIcon`/`QTextEdit`…) — verificar con `rg <name>` cuáles siguen en uso.
   - `ORG_TYPE_MAP` (42–47): mover a `app/ui/mixins/ingest_mixin.py` o un
     `app/ui/constants.py` y eliminar el import lazy en wifi_mixin. (Decisión al final.)

## Qué queda legítimamente en `main_window.py`

- `__init__` (78 líneas) + helpers de estado transversal.
- `setup_views` descompuesto (orquestación de layout) o `LayoutMixin`.
- `tr`, `closeEvent`, `eventFilter` (o su ubicación única), `_style_table_viewports`,
  `_set_status_color`, `_refresh_accent_labels`, `_switch_theme`, `_switch_accent`,
  `_toggle_wheat_background`, splitter helpers, `update_start_button_state`.
- Use of `QSettings`, `QTimer` de auto-sync, `_auto_sync_check`/`_process_device_poll`
  (si no van a `DevicesMixin`).
- Entry `if __name__ == "__main__":`.

## Resultado previsto

| Bloque | Contenido | Reducción estimada |
|---|---|---|
| 1 | 4 diálogos inline | −470 (→ wrappers, −410 neto) |
| 2 | `SessionsMixin` | −330 |
| 3 | `CameraMixin` | −340 |
| 4 | `SourcesMixin` | −460 |
| 5 | `ProjectMixin` | −450 |
| 6 | `DevicesMixin` | −480 |
| 7 | `MenuMixin` | −170 |
| 8 | `IngestMixin` (+PostIngest) | −620 |
| 9 | setup_views + limpieza | −438 (setup) + dead code |
| **Total** | | **~4.589 → ~1.300-1.500** |

**Nuevos ficheros en `app/ui/`:** 4 diálogos (`project_settings_dialog.py`,
`camera_overrides_dialog.py`, `names_manager_dialog.py`, `dump_locations_dialog.py`).
**Nuevos mixins en `app/ui/mixins/`:** `sessions_mixin.py`, `camera_mixin.py`,
`sources_mixin.py`, `project_mixin.py`, `devices_mixin.py`, `menu_mixin.py`,
`ingest_mixin.py` (+ opcional `post_ingest_mixin.py`, `layout_mixin.py`).

## Orden de ejecución (dependencias → flujo)

1. **Bloque 1** (diálogos) — independiente, cero riesgo.
2. **Bloque 6 DevicesMixin** — alto valor; depende de CameraMixin para `_on_stage_done`.
   → requiere Bloque 3 primero, o mover `_on_stage_done` con import lazy. Preferible
   extraer antes CameraMixin.
3. **Bloque 3 CameraMixin** → **Bloque 2 SessionsMixin** → **Bloque 4 SourcesMixin**
   → **Bloque 5 ProjectMixin** → **Bloque 6 DevicesMixin** → **Bloque 7 MenuMixin**
   → **Bloque 8 IngestMixin** (último, más acoplado).
4. **Bloque 9** setup_views + limpieza (cierre).

Orden canónico propuesto: **1 → 3 → 2 → 4 → 5 → 6 → 7 → 8 → 9** (cámara antes que
dispositivos porque `_on_stage_done` y `_on_source_widget_check_changed` dependen de
`_detect_camera_for_session`).

## Fricción de tests por bloque (importante)

Cada mixin que importa un singleton a nivel de módulo (db, metadata_engine, sd_reader,
ffmpeg, updater) exige adaptar el patching en tests:

- Los tests usan `mw.db = self.db`, `ingestor_module.db = self.db`,
  `wifi_mixin_module.db = self.db`. Al extraer un mixin, los métodos movidos resuelven
  el singleton desde el namespace del NUEVO módulo mixin → añadir parche paralelo:
  `sessions_mixin_module.db`, `camera_mixin_module.metadata_engine`, etc.
  (patrón ya consolidado, coste ~2-4 líneas por archivo de test afectado).
- `test_main_window.py` (1421 líneas) es el principal afectado; `test_session_content_modes.py`
  (342), `test_selective_dump.py` (436), `test_e2e.py` (227) y `test_wifi_source.py`
  (988) también.
- Regla GSD/refactor: SIEMPRE comprobar `python -m unittest tests.<archivo>` aislado
  + `main_window`/`wifi_source`/`e2e` por bloque. Los tests NO se reescriben, solo se
  ajusta el patching de singletons.

## Restricciones no negociables

- Cero cambio de comportamiento; métodos movidos VERBATIM.
- No reordenar/renombrar/reformatear bloques no movidos.
- Cada bloque se ejecuta como un `/gsd-quick` autónomo (plan + plan checker + executor
  + summary + commit atómico). Con `--validate` si se quiere verificación.
- Convenciones de CLAUDE.md: comentarios/docstrings en español, comillas simples,
  `tr()` intacto, imports lazy para ciclos (patrón `ORG_TYPE_MAP`).
- `eventFilter` debe existir una única vez en el MRO final.