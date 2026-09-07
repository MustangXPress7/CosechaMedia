# Bloque 9 — Descomposición setup_views + Limpieza MainWindow

## Resumen

**Plan:** Bloque 9 — Descomposición setup_views + Limpieza MainWindow  
**Fecha:** 2026-09-07  
**Commit:** 7598f5d  
**Estado:** complete

---

## Cambios realizados

### Tarea 1: Descomposición de `setup_views` (438 → 5 líneas)

Se ha extraído el método `setup_views` original (líneas 277–703, 438 líneas) en **10 métodos privados** de `MainWindow`:

| Helper | Líneas | Qué construye |
|--------|--------|---------------|
| `_build_dashboard` | 208–237 | `dashboard_view`, `dash_layout`, `desc_box` (descripción) |
| `_build_header` | 239–320 | `header_bar`: app_label, project_combo, botones proyecto, path_label, btn_show_metadata, status_indicator/text |
| `_build_sources_table` | 321–376 | `source_label_row`, `src_top` (source_input + btn_add_source), `source_list` (4 cols, eventFilter) |
| `_build_sessions_box` | 378–469 | `sess_box`: sessions_combo, botones new/delete, src/dest rows, dump mode switch (rotativo + config) |
| `_build_post_actions` | 470–532 | `post_box`: "Al terminar" (format, CSV, shutdown) + "Operaciones" (reorganize, clear_completed) |
| `_build_action_buttons` | 533–554 | `action_row`: btn_start (PrimaryAction), btn_stop (DangerAction) |
| `_build_progress_area` | 555–577 | `progress_bar` (sin texto), `stats_row` (processed/pending/errors labels) |
| `_build_files_table` | 578–601 | `table` (6 cols, sorting, context menu, styled viewport) |
| `_assemble_layout` | 602–653 | splitter, tamaños, restore_btn, `dash_layout.addWidget(splitter)` |
| `_connect_signals` | 654–675 | Carga proyectos, rutas recientes, auto-detección drives |

**Nuevo `setup_views` (5 líneas):**
```python
def setup_views(self):
    self._build_dashboard()
    self._build_header()
    self._assemble_layout()
    self._connect_signals()
```

### Tarea 2: Limpieza de huérfanos a nivel de módulo

**Eliminado:**
- `_reorganize_worker` (líneas 97–102 en el original) — no-op muerto (D-18). Comentario y función completa eliminados.

**Mantenidos intactos (5 helpers de módulo, usados por workers/background):**
- `ORG_TYPE_MAP` (línea 53) — usado por `start_ingest`
- `_format_drive` (línea 60) — llamado por `_format_sources_worker`
- `_format_sources_worker` (línea 76) — pasado a `_run_background` en `_format_sources_after_ingest`
- `_generate_proxies_worker` (línea 87) — pasado a `_run_background` en `_generate_proxies_after_ingest`
- `_probe_device_connectivity` (línea 97) — llamado desde `_auto_sync_check` y test `test_probe_device_connectivity_uses_mtp_and_ftp`

**Verificaciones:**
- `grep "_reorganize_worker" app/ui/main_window.py` → 0 hits ✓
- `eventFilter` y `tr()` wrapper se mantienen en `MainWindow` ✓
- Declaración de clase: `MainWindow(QMainWindow, WifiMixin, CameraMixin, MenuMixin, DevicesMixin, SourcesMixin, ProjectMixin, SessionsMixin, IngestMixin)` ✓

### Tarea 3: Verificación completa

**Suite completa:** `python -m pytest tests/ -q --tb=short`

| Métrica | Antes | Después |
|---------|-------|---------|
| `main_window.py` líneas | ~920 | 961 |
| `setup_views` líneas | 438 | 5 |
| Helpers `_build_*` | 0 | 8 + `_assemble_layout` + `_connect_signals` |
| `_reorganize_worker` | existe | **eliminado** |
| Helpers módulo | 6 | 5 (uno menos) |
| Mixins compuestos | 2 (Wifi, Camera) | 8 (sin cambios en composición) |
| Tests pasando | 393 | 393 |
| Tests modificados | 0 | 0 |

**Resultado:** 393 passed, 5 skipped, 1 pre-existing failure (test_mtp.py::TestThreadLocalManager::test_wpd_session_devicename_no_duplicate)

---

## Desviaciones del plan

**Ninguna** — Refactor puro verbatim:
- Código idéntico al original (diff solo indentación/nombres)
- `tr()` intacto en todos los strings UI
- Single quotes mantenidos
- Comentarios en español preservados
- Sin cambios de comportamiento

---

## Archivos modificados

- `app/ui/main_window.py` — Refactor completo (+167/-132 líneas netas)

---

## Métricas

- **Duración:** ~15 min
- **Tasks completadas:** 3/3
- **Commits:** 1
- **Líneas netas cambiadas:** +35 (debido a docstrings y estructura de helpers)