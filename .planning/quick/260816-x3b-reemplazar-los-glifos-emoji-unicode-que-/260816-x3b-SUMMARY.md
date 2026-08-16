---
phase: 260816-x3b-reemplazar-los-glifos-emoji-unicode-que-
plan: 1
subsystem: ui
tags: [pyside6, qsvg, icons, i18n, emoji, svg]

# Dependency graph
requires:
  - phase: 01-auditor-a-ui-y-plan-de-reubicaci-n
    provides: UI-REVIEW hallazgo Visuals 3/4 (iconos emoji → tofu en Linux/macOS)
provides:
  - Módulo de iconos SVG tintables con la paleta (app/ui/icons.py + 13 SVGs)
  - Sustitución de todos los glifos emoji de botones de main_window.py y source_picker.py por QIcon
  - Hook de re-tinte icons.refresh_all() en _switch_theme/_switch_accent
  - Catálogo EN sincronizado (Detectar / Escanear cámaras) + tools/translate_en.py
affects: [v2, ui-review]

# Actuals (#2632) — same estimateTokens scale as the plan estimate (chars/4 over realized diff)
actuals:
  tokens: 7250
  tasks: 3
  commits: 5

# Tech tracking
tech-stack:
  added: [QSvgRenderer + QIcon con devicePixelRatio 2.0 (sin dependencias nuevas)]
  patterns:
    - "SVG placeholder `#FF00FF` → replace → QSvgRenderer → cache (patrón wheat_field)"
    - "Registro de botones por weakref + refresh_all() para re-tinte al cambiar tema/acento"
    - "QIcon con modos Normal (text) y Disabled (text_disabled)"

key-files:
  created:
    - app/ui/icons.py
    - app/ui/assets/icons/ (13 SVGs)
    - tests/test_icons.py
  modified:
    - app/ui/main_window.py
    - app/ui/source_picker.py
    - app/i18n/cosechamedia_en.ts
    - tools/translate_en.py
    - tests/test_wifi_source.py
    - tests/test_source_content.py
    - tests/test_source_picker.py

key-decisions:
  - "Iconos SVG propios con placeholder recoloreable (patrón wheat_field) en vez de QtAwesome: cero dependencias nuevas"
  - "Render 2× con devicePixelRatio 2.0 para nitidez HiDPI"
  - "Doble modo QIcon: Normal con theme.color('text') y Disabled con 'text_disabled' (paridad con el dimming QSS)"
  - "weakref en el registro de botones: los botones de fila (papelera) se crean/destruyen sin retenerse vivos"

patterns-established:
  - "Iconos de botón = QIcon SVG tintable vía icons.apply()/icons.icon(); nunca glifos unicode como texto"
  - "Re-tinte global de iconos al cambiar tema/acento vía icons.refresh_all() (weakrefs + paleta vigente)"

requirements-completed: [UI-REVIEW-Visuals]

coverage:
  - id: D1
    description: "Módulo app/ui/icons.py con 13 SVGs stroke-based tintables (icon/pixmap/apply/refresh_all + cache)"
    requirement: UI-REVIEW-Visuals
    verification:
      - kind: unit
        ref: "tests/test_icons.py#test_icon_returns_non_null_for_all_names"
        status: pass
      - kind: unit
        ref: "tests/test_icons.py#test_icon_pixmap_renders_for_all_names"
        status: pass
      - kind: unit
        ref: "tests/test_icons.py#test_svg_text_for_replaces_placeholder"
        status: pass
      - kind: unit
        ref: "tests/test_icons.py#test_apply_sets_icon_and_registers"
        status: pass
      - kind: unit
        ref: "tests/test_icons.py#test_refresh_all_discards_dead_weakrefs"
        status: pass
    human_judgment: false
  - id: D2
    description: "Sustitución de todos los glifos de botones de main_window.py por QIcon + hook refresh_all en _switch_theme/_switch_accent + catálogo EN sincronizado"
    requirement: UI-REVIEW-Visuals
    verification:
      - kind: unit
        ref: "tests/test_wifi_source.py#test_session_source_shows_wifi_origin"
        status: pass
      - kind: unit
        ref: "tests/test_wifi_source.py#test_session_source_shows_mtp_device_name"
        status: pass
      - kind: unit
        ref: "tests/test_source_content.py#test_source_list_has_per_row_delete_column"
        status: pass
      - kind: automated_ui
        ref: "python -m unittest tests.test_wifi_source tests.test_source_content tests.test_e2e -v"
        status: pass
    human_judgment: false
  - id: D3
    description: "Ítems «Desconectados» de source_picker.py con icono de teléfono SVG y texto limpio (sin prefijo emoji)"
    requirement: UI-REVIEW-Visuals
    verification:
      - kind: unit
        ref: "tests/test_source_picker.py#test_missing_section_lists_devices"
        status: pass
      - kind: automated_ui
        ref: "python -m unittest tests.test_source_picker tests.test_wifi_source -v"
        status: pass
    human_judgment: false

# Metrics
duration: 22min
completed: 2026-08-17
status: complete
---

# Quick 260816-x3b: Reemplazo de glifos emoji por iconos SVG tintables Summary

**Módulo de iconos SVG tintables con la paleta (app/ui/icons.py + 13 SVGs), sustitución de todos los glifos emoji de botones en main_window.py y source_picker.py por QIcon, re-tinte automático al cambiar tema/acento vía icons.refresh_all(), y catálogo EN sincronizado (Detectar / Escanear cámaras)**

## Performance

- **Duration:** ~22 min
- **Started:** 2026-08-16T23:52:00Z
- **Completed:** 2026-08-17T00:14:33Z
- **Tasks:** 3 (TDD en Task 1: RED + GREEN)
- **Files modified:** 22 (7 fuentes nuevos + 15 modificados)
- **Estimate vs actuals:** estimado 30000 tokens → 7250 (chars/4 del diff realizado)

## Accomplishments

- `app/ui/icons.py`: módulo de iconos que lee SVGs de `app/ui/assets/icons/`, reemplaza el placeholder `#FF00FF` por el color de la paleta vigente, renderiza con `QSvgRenderer` a 2× (devicePixelRatio 2.0), cachea por (nombre, hex) y registra botones por weakref para re-tinte.
- 13 SVGs stroke-based 24×24 (refresh, plus, minus, x, pencil, copy, folder, gear, trash, camera, phone, wifi, globe) con un único color placeholder recolorizable.
- Todos los glifos de `main_window.py` sustituidos: 6 botones de la header (⟳ + × ✎ ⧉ 📁), ⚙ de configuración, ✎ de descripción, +/− de sesión, 📁×2 de examinar, 🗑×2 de borrado por fila y los botones de texto «⟳ Detectar»/«📷 Escanear cámaras» → «Detectar»/«Escanear cámaras» con icono QIcon.
- Prefijos emoji «📶 »/«🌐 »/«📱 » eliminados del label de origen de sesión («Origen automático: %1» queda solo con el nombre del dispositivo).
- `_switch_theme`/`_switch_accent` llaman a `icons.refresh_all()`: los iconos se re-tintan al instante al cambiar de tema o acento.
- Ítems «Desconectados» de `source_picker.py` con icono de teléfono SVG y texto limpio.
- Catálogo `cosechamedia_en.ts` sincronizado (2 entradas: source+translation limpias) y `tools/translate_en.py` actualizado (el tool fallaba con MISSING TRANSLATIONS por los source strings nuevos).
- Suite completa: 257 tests OK (3 skips esperados: tests MTP de dispositivo vivo sin hardware conectado).

## Task Commits

Cada tarea se commiteó atómicamente:

1. **Task 1 (TDD): módulo app/ui/icons.py + 13 SVGs + tests/test_icons.py**
   - `27faf3d` (test, RED) — tests del módulo de iconos
   - `dc64822` (feat, GREEN) — módulo + 13 SVGs placeholder
2. **Task 2: sustitución de glifos en main_window.py + hook re-tinte + .ts + tests wifi/source_content**
   - `ff7a54e` (feat)
3. **Task 3: icono de teléfono en ítems «Desconectados» de source_picker.py + tests**
   - `cbb2250` (feat)

**Fix de desviación (Rule 2):**
- `b28b808` (fix) — sincronización de `tools/translate_en.py` con los nuevos source strings

## Files Created/Modified

- `app/ui/icons.py` (nuevo) - Módulo de iconos: `_svg_text_for`, `pixmap`, `icon`, `apply`, `refresh_all`; placeholder `#FF00FF`, cache (nombre, hex), registro weakref, guard `_HAS_ICONS` con fallback a QIcon nulo + `print(f"Icon not found: ...")` (nunca lanza en runtime).
- `app/ui/assets/icons/*.svg` (13 nuevos) - SVGs stroke-based 24×24, `fill="none"`, `stroke="#FF00FF"`, stroke-width 1.8, linecap/linejoin round.
- `tests/test_icons.py` (nuevo) - 5 tests: QIcon no nulo por nombre, pixmap renderizado, replace de placeholder, apply+registro (modos Normal/Disabled), refresh_all con weakrefs muertas.
- `app/ui/main_window.py` - Todos los botones glifo → `icons.apply(...)`; prefijos de origen eliminados; `icons.refresh_all()` en ambos hooks.
- `app/ui/source_picker.py` - `_missing_item` con `icons.icon("phone", size=16)` y texto sin «📱 ».
- `app/i18n/cosechamedia_en.ts` - `<source>⟳ Detectar</source>`→`Detectar`, `📷 Escanear cámaras`→`Escanear cámaras` (source+translation).
- `tools/translate_en.py` - Claves del dict sincronizadas (Detectar/Detect, Escanear cámaras/Scan cameras).
- `tests/test_wifi_source.py` - `assertIn("📶"/"📱")` → `assertNotIn` (verifica limpieza de prefijos).
- `tests/test_source_content.py` - `btn.text() == "🗑"` → `assertFalse(btn.icon().isNull())`.
- `tests/test_source_picker.py` - Identificación del ítem desconectado por icono no nulo (2 aserciones + helper).

## Decisions Made

- **Sin dependencias nuevas:** SVG propios + QSvgRenderer en vez de QtAwesome (requisito explícito del plan).
- **Placeholder + replace + cache:** mismo patrón de recolor que `wheat_field.py`; cache de módulo por `(name, hex)`.
- **HiDPI:** render a `size*2` px con `setDevicePixelRatio(2.0)` — nítido en pantallas 2×.
- **Modos de icono:** Normal con `theme.color(color_key)` y Disabled con `theme.color("text_disabled")` (paridad con el dimming que el QSS aplicaba a los glifos deshabilitados).
- **Registro por weakref:** `_registry[id(btn)] -> (weakref, name, size, color_key)`; los botones de fila (papelera) se crean y destruyen continuamente y el registro no los retiene vivos.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] tools/translate_en.py desincronizado con los nuevos source strings**
- **Found during:** Task 2 (verificación final de no-regresión, grep de limpieza)
- **Issue:** El tool de traducción `tools/translate_en.py` tenía las claves antiguas `"⟳ Detectar"` y `"📷 Escanear cámaras"` en su dict `TRANSLATIONS`. Al cambiar los `tr()` en `main_window.py`, los sources del `.ts` son ahora `Detectar`/`Escanear cámaras`; al ejecutar el tool, `TRANSLATIONS.get("Detectar")` devuelve None y el tool **aborta con exit 1 (MISSING TRANSLATIONS)**, además de dejar claves obsoletas.
- **Fix:** Sustituidas las 2 claves antiguas por `"Detectar": "Detect"` y `"Escanear cámaras": "Scan cameras"` (las traducciones de los tooltips ya existían).
- **Files modified:** `tools/translate_en.py`
- **Verification:** Script de verificación: los 510 sources del `.ts` están cubiertos por el dict; suite completa verde.
- **Committed in:** `b28b808` (commit propio, no mezclado con la tarea)

---

**Total deviations:** 1 auto-fixed (1 Rule 2 — missing critical)
**Impact on plan:** Fix necesario para no romper el pipeline de traducciones; cambio de 2 líneas sin alcance adicional.

## Issues Encountered

- El shim bash de gsd-tools no funciona en PowerShell — se invocó `node gsd-tools.cjs` directamente. Sin impacto en la ejecución.
- El tool `rg` no está disponible en PATH; se usó la herramienta Grep (que maneja UTF-8) para la verificación de glifos.
- Skips esperados: 3 tests de `test_mtp_integration` (`test_device_connected`, `test_stage_small_folder`, `test_storages_listed`) saltan por "sin dispositivo MTP conectado" — son pruebas de hardware vivo, no regresiones.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Los hallazgos Visuals 3/4 del UI-REVIEW (iconos emoji → tofu) quedan resueltos: ningún botón de `main_window.py` ni `source_picker.py` usa glifos unicode como icono.
- `app/ui/icons.py` queda como patrón reutilizable para cualquier botón futuro (`icons.apply(btn, name, size)`); el glob de datas de `main.spec` (`('app/ui/assets', 'app/ui/assets')`) ya empaqueta `app/ui/assets/icons/` sin cambios.
- Pendiente del UI-REVIEW para fases futuras: resto de hallazgos Visuals del 01-UI-REVIEW.md y el `📅` de `tools/translate_en.py` (stale pre-existente, fuera de alcance).

---
*Quick: 260816-x3b-reemplazar-los-glifos-emoji-unicode-que-*
*Completed: 2026-08-17*

## Self-Check: PASSED

- FOUND: app/ui/icons.py, 13 SVGs en app/ui/assets/icons/, tests/test_icons.py
- FOUND: commits 27faf3d, dc64822, ff7a54e, cbb2250, b28b808
- Suite completa: 257 tests OK (3 skips esperados de hardware MTP vivo)

