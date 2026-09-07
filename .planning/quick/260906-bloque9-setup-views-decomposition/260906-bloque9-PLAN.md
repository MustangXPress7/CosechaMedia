# Bloque 9 — Descomposición setup_views + Limpieza MainWindow

## Objetivo
Descomponer `setup_views` (438 líneas, 271–703) en 8 helpers privados `_build_*` y limpiar huérfanos a nivel de módulo. Meta final: MainWindow ~1300–1500 líneas, solo `WifiMixin` + `CameraMixin` compuestos.

---

## Tareas

### Tarea 1: Descomponer setup_views en helpers privados
**Archivos:** `app/ui/main_window.py`

**Acción:**
Extraer verbatim 8 métodos privados de `MainWindow` (sin cambiar lógica, solo indentación + `self.`):

| Helper | Líneas origen | Qué construye |
|--------|---------------|---------------|
| `_build_header` | 278–356 | `header_bar`: app_label, project_combo, botones proyecto, path_label, btn_show_metadata, status_indicator/text |
| `_build_dashboard` | 271–276, 357–393 | `dashboard_view` + `dash_layout` + `desc_box` (description) |
| `_build_sources_table` | 395–448 | `source_label_row`, `src_top` (source_input + btn_add_source), `source_list` (4 cols, eventFilter) |
| `_build_sessions_box` | 450–537 | `sess_box`: sessions_combo, botones new/delete, src/dest rows, dump mode switch (rotativo + config) |
| `_build_post_actions` | 544–605 | `post_box`: "Al terminar" (format, CSV, shutdown) + "Operaciones" (reorganize, clear_completed) |
| `_build_action_buttons` | 610–626 | `action_row`: btn_start (PrimaryAction), btn_stop (DangerAction) |
| `_build_progress_area` | 631–650 | `progress_bar` (sin texto), `stats_row` (processed/pending/errors labels) |
| `_build_files_table` | 652–673 | `table` (6 cols, sorting, context menu, styled viewport) |

Reemplazar `setup_views` por secuencia de llamadas:
```python
def setup_views(self):
    self._build_dashboard()
    self._build_header()
    self._build_sources_table()
    self._build_sessions_box()
    self._build_post_actions()
    self._build_action_buttons()
    self._build_progress_area()
    self._build_files_table()
    self._assemble_layout()       # splitter, sizes, restore_btn, dash_layout.addWidget(splitter)
    self._connect_signals()       # señales UI → slots (project_combo, source_list, table, etc.)
    self.load_existing_projects()
    self._refresh_recent_paths()
    if settings.value("autoDetectDrives", False, type=bool):
        QTimer.singleShot(200, self._auto_detect_removable_drives)
```

Añadir `_assemble_layout()` (líneas 674–699) y `_connect_signals()` (nuevo, agrupa `currentIndexChanged`, `itemChanged`, `customContextMenuRequested`, `clicked` de botones, etc.).

**Verificación:**
```bash
python -m pytest tests/test_main_window.py -x -q
```
Suite completa pasa (393 tests). No cambios de comportamiento.

**Done:**
- `setup_views` ≤ 40 líneas, solo llama a helpers
- 8 helpers `_build_*` + `_assemble_layout` + `_connect_signals` existen como métodos de `MainWindow`
- Código idéntico al original (diff solo indentación/nombres)
- `tr()` intacto en todos los strings UI

---

### Tarea 2: Limpieza de huérfanos a nivel de módulo
**Archivos:** `app/ui/main_window.py`

**Acción (orden estricto):**

1. **ELIMINAR** `_reorganize_worker` (líneas 91–96) — no-op muerto (D-18). Comentario y función completa a la basura.

2. **MANTENER en módulo** (no son de MainWindow, los usan workers/background):
   - `ORG_TYPE_MAP` (47–52) — usado por `start_ingest` vía `ORG_TYPE_MAP.get(s_org, "camera_first")`
   - `_format_drive` (54–68) — llamado por `_format_sources_worker`
   - `_format_sources_worker` (70–79) — pasado a `_run_background` en `_format_sources_after_ingest`
   - `_generate_proxies_worker` (81–89) — pasado a `_run_background` en `_generate_proxies_after_ingest`
   - `_probe_device_connectivity` (99–126) — llamado desde `_auto_sync_check` (línea 225) y test `test_probe_device_connectivity_uses_mtp_and_ftp`

   → Estos 5 se quedan **exactamente donde están** (nivel módulo, arriba de la clase). No mover a mixins.

3. **EventFilter** (línea ~2181 `eventFilter` + `_source_list_event_filter`) → **mantener en MainWindow** (único, no va a mixins).

4. **`tr()` wrapper** (líneas 129–130) → **mantener en MainWindow**.

5. **Declaración de clase** → `class MainWindow(QMainWindow, WifiMixin, CameraMixin):` (sin cambios; los otros mixins —Sources/Devices/Project/Menu/Ingest— no existen aún).

**Verificación:**
```bash
python -m pytest tests/test_main_window.py -x -q
grep -n "_reorganize_worker" app/ui/main_window.py   # debe dar 0 hits
```

**Done:**
- `_reorganize_worker` eliminado
- 5 helpers de módulo intactos en su sitio
- EventFilter y `tr()` en MainWindow
- Sin regresiones en tests

---

### Tarea 3: Verificación completa + ajuste patching tests si procede
**Archivos:** `tests/test_main_window.py` (solo si hace falta)

**Acción:**
Ejecutar suite completa. Si algún test falla por patching de `mw.db` / `camera_mixin_module.db` / `ingestor_module.db` / `me_module.db` (patrón actual: 18 setUps en 5 ficheros), **no tocar tests** — el parcheo sigue válido porque:
- No se crean nuevos módulos
- No se mueven funciones entre módulos
- Solo se refactoriza internamente `MainWindow`

Si apareciera algún fallo espurio (orden de imports, etc.), fix mínimo en el test afectado.

**Verificación:**
```bash
python -m pytest tests/ -x -q --tb=short
```
Toda la suite (14 ficheros) pasa.

**Done:**
- 393 tests pasan (igual que pre-refactor)
- 0 tests modificados
- MainWindow ~1300–1500 líneas (verificar `wc -l app/ui/main_window.py`)

---

## Criterios de aceptación globales

| Métrica | Antes | Después |
|---------|-------|---------|
| `main_window.py` líneas | 3750 | 1300–1500 |
| `setup_views` líneas | 438 | ≤ 40 |
| Helpers `_build_*` | 0 | 8 + `_assemble_layout` + `_connect_signals` |
| `_reorganize_worker` | existe | **eliminado** |
| Helpers módulo (ORG_TYPE_MAP, _format_*, _probe_*) | 6 | 5 (uno menos) |
| Mixins compuestos | 2 (Wifi, Camera) | 2 (sin cambios) |
| Tests pasando | 393 | 393 |

---

## Notas de implementación

- **Refactor puro**: copiar/pegar bloques verbatim, solo cambiar indentación y añadir `self.` donde falte. No reescribir lógica.
- **Orden de helpers** en el archivo: agrupar todos los `_build_*` juntos tras `__init__` y antes de `closeEvent` (zona "UI construction").
- **Imports**: no tocar. `DashboardBackground`, `_StageWorker`, `_TaskWorker` ya vienen de `app.ui.mixins.workers`.
- **Spanish**: docstrings/comentarios en ES, single quotes, `tr()` en todo string UI.
- **Sin checkpoints**: tarea autónoma, `autonomous: true`.