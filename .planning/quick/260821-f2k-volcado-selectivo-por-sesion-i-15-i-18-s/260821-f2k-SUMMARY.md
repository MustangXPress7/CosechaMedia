---
phase: 260821-f2k-volcado-selectivo-por-sesion-i-15-i-18-s
plan: 1
subsystem: ui-ingest
tags: [volcado-selectivo, sesiones, i15, i18, ventana-n-dias, tabla-opciones]
requires: [sessions.content_mode/content_filter (db.py, sin cambios), SelectiveDumpAssistant mode="filter", _apply_selection normalización]
provides: [switch cíclico por sesión, ventana N días real desde último volcado, filtro None = todo, tabla de orígenes 3 columnas con papelera integrada]
affects: [start_ingest (lee content_mode/content_filter ya existente), flujo WiFi/FTP (forzado a "all" intacto)]
tech-stack:
  added: []
  patterns: [switch cíclico persistente en DB, diálogo numérico QInputDialog con clamp 1–3650, cutoff calculado al iniciar ingesta]
key-files:
  created:
    - tests/test_session_content_modes.py
  modified:
    - app/core/ingestor.py
    - app/ui/main_window.py
    - app/ui/selective_dump.py
    - app/i18n/cosechamedia_en.ts
    - tests/test_source_content.py
    - tests/test_wifi_source.py
decisions:
  - "Ventana N días SIN cutoff congelado: el cutoff se calcula al INICIAR la ingesta desde el último volcado de la sesión (fallback hoy−N) — semántica T-F2K-03 aceptada"
  - "«Intervalo - todo»: filtro None se preserva como None en _init_interval_filter y _matches_filter lo trata como volcar todo"
  - "WiFi/FTP bloqueados a «Todo el contenido» en UI, coherente con el forzado de start_ingest"
  - "El modo 'dump' del asistente queda sin entry point desde MainWindow; su maquinaria interna permanece intacta"
metrics:
  duration: 0.6h
  completed: 2026-08-21
status: complete
actuals:
  tokens: 13655
  tasks: 3
  commits: 5
---

# Phase 260821-f2k Plan 1: Volcado selectivo por sesión (I-15 + I-18) Summary

Switch cíclico de volcado por sesión (Todo → Intervalo → Últimos N días → Todo) con persistencia inmediata en `sessions.content_mode/content_filter`, ventana real de N días calculada al iniciar la ingesta desde el último volcado, tabla de orígenes reducida a 3 columnas («Ruta de origen» / «Cámara» / «Opciones») con papelera integrada, y retirada del botón global «Volcado selectivo…».

## Tasks Completed

| Task | Name | Commits | Files |
| ---- | ---- | ------- | ----- |
| 1 | Core mínimo — ventana N días real y «filtro None = todo» | 64b8ebb (test RED), ad9cc23 (feat GREEN) | app/core/ingestor.py, tests/test_session_content_modes.py |
| 2 | Switch cíclico de volcado por sesión (+ bloqueo WiFi/FTP) | 7039971 (test RED), 9adab7f (feat GREEN) | app/ui/main_window.py, app/ui/selective_dump.py, tests/test_session_content_modes.py |
| 3 | Tabla 3 columnas «Opciones» + retirada botón global + i18n | 8ff5121 | app/ui/main_window.py, tests/test_source_content.py, tests/test_wifi_source.py, app/i18n/cosechamedia_en.ts |

## Verification Results

- **Task 1:** 5 tests nuevos (`TestWindowCutoffCore`) + `tests.test_ingestor` completo → 21 tests OK. Grep estructural: guard `if self._content_filter is None:` dentro de `_matches_filter` ✓, ramas `cutoff_date` intactas (≥4) ✓.
- **Task 2:** 8 tests nuevos (`TestSessionDumpSwitch`) + `tests.test_selective_dump` + `tests.test_e2e` → 41 tests OK. Grep estructural: `_cycle_session_content_mode`, `_update_session_dump_switch`, `_open_content_filter(self, session_id)`, fila `sess_dump_row` en Sesiones, kwarg `initial_mode=None` ✓.
- **Task 3:** Suite COMPLETA `python -m unittest discover -s tests` → **297 tests OK** (5 skips pre-existentes) en Qt offscreen. Grep estructural: sin rastro de `btn_selective_dump` / `_open_selective_dump` / `_build_content_button` / `_build_remove_source_button`; `setColumnCount(3)` + `_build_options_widget` presentes; entradas `<source>Opciones</source>` y `<source>Últimos %1 días</source>` en el .ts ✓.

## Success Criteria

- [x] Switch cíclico por sesión operativo con persistencia inmediata (decisiones #1 y #2)
- [x] Cancelar cualquier diálogo no altera el modo persistido (tests 3 y 5)
- [x] WiFi/FTP bloqueados a «Todo el contenido» en UI (decisión #3, test 7)
- [x] Ventana N días: `{"window_days": N}` sin cutoff congelado; cutoff real al iniciar ingesta desde último volcado, fallback hoy−N (Task 1, tests 1–3)
- [x] Botón global y slot eliminados; maquinaria interna del asistente intacta (decisión #4, test B)
- [x] Tabla 3 columnas Ruta/Cámara/Opciones con papelera integrada y sin botón de filtro (decisión #5, tests A/C/D)
- [x] i18n .ts sincronizado con las 10 entradas nuevas; strings nuevos vía tr()
- [x] Sin cambios en app/core/db.py; app/core/ingestor.py limitado a los fixes de Task 1
- [x] Suite completa verde en offscreen (297 OK)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `_init_interval_filter` adicional: filtro None se preserva como None**
- **Found during:** Task 1 (fase RED)
- **Issue:** El plan describía 3 fixes, pero el guard en `_matches_filter` era insuficiente para el Test 4: con `content_mode="interval"` y `content_filter=None`, `_init_interval_filter(None)` construía un dict `{"dates": set(), ...}` (no None), así que el guard nunca se activaba y el «intervalo - todo» seguía saltándolo TODO. El propio plan exige ese comportamiento en `<behavior>` Test 4 y en must_haves («_matches_filter: content_filter None ⇒ True»).
- **Fix:** Early-return en `_init_interval_filter` que asigna `self._content_filter = None` cuando el filtro recibido es None. Es el 4º cambio en ingestor.py, requerido por la especificación de comportamiento del propio plan.
- **Files modified:** app/core/ingestor.py
- **Commit:** ad9cc23

### Notas de ejecución (no son desviaciones de comportamiento)

- **WIP previo integrado:** el árbol tenía cambios sin commitear de una sesión anterior (refactor de init de filtros + `_check_window_filter` en ingestor.py; soporte window en `content_summary` en selective_dump.py). Las anclas de línea del plan coincidían con ese estado sucio, así que el WIP se plegó en los commits de Task 1 (ingestor.py) y Task 2 (selective_dump.py).
- **Compatibilidad transitoria Task 2:** el lambda del antiguo builder de la columna Contenido pasó de `_open_content_filter(row)` a `_open_content_filter(s["id"])` para no dejar un llamador roto entre Task 2 y Task 3 (el botón desapareció en Task 3).
- **Test 7 (WiFi):** primer fallo de RED era un bug del propio test (faltaba refrescar el combo tras crear la sesión); corregido dentro de la fase RED antes de implementar.
- **Incidente de edición reparado:** durante Task 3 un Edit invirtió old/new y fusionó temporalmente `_open_selective_dump` con `_open_content_filter`; detectado por verificación inmediata de sintaxis y reparado antes de continuar (diff final limpio: −23 líneas exactas).

## Threat Model Mitigations Applied

- **T-F2K-01 (Tampering, JSON corrupto):** `_session_content_state` mantiene try/except `(TypeError, ValueError)` → None = «todo»; degradación segura sin crash.
- **T-F2K-02 (DoS, N días):** `QInputDialog.getInt` con clamp estricto min=1 max=3650; `int(days)` al persistir; defensas `int()` adicionales en `_init_window_filter` y `_calculate_window_cutoff`.
- **T-F2K-03 (Repudiation, cutoff no congelado):** semántica aceptada y documentada — la ventana es relativa al último volcado EN EL MOMENTO de iniciar la ingesta.

## Known Stubs

None — no stubs introduced.

## Self-Check: PASSED

- tests/test_session_content_modes.py existe ✓
- Commits verificados en git log: 64b8ebb, ad9cc23, 7039971, 9adab7f, 8ff5121 ✓
- Suite completa discover: 297 tests OK ✓
