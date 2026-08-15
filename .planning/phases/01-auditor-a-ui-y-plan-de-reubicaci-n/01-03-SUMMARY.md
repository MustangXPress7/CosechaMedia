---
phase: 01-auditor-a-ui-y-plan-de-reubicaci-n
plan: 03
subsystem: ui
tags: [pyqt, pyside6, plan-reubicacion, matriz-d06, bandas-p1-p2-p3, gate-cero-codigo, trazabilidad]

# Dependency graph
requires:
  - phase: 01-auditor-a-ui-y-plan-de-reubicaci-n
    provides: "Informe de hallazgos UI 01-HALLAZGOS.md (7 hallazgos H-01..H-07) + inventario + UI-SPEC (bandas D-06, copy zero-one-many)"
provides:
  - "Plan de reubicación priorizado 01-PLAN-REUBICACION.md: 17 ítems R-01..R-17 con Score (D-06) y banda P1/P2/P3, orden por flujo del operador, strings nuevos ES con tr() para v2"
  - "Matriz de puntuación verificable (fórmula D-06, 3+ ejemplos de cálculo) y trazabilidad completa H-NN ↔ R-NN (7/7 sin huérfanos)"
  - "Gate de cero código: conjuntos git idénticos a la línea base + registro del hang preexistente de la suite como REVISA OPERADOR"
affects:
  - "01-04 (aprobación del operador: bandas, ítems destructivos D-09, discrepancia D-12)"
  - "Fase v2 UI-04/UI-05 (ejecución de las reubicaciones: los 12 strings nuevos con tr(), ítems R-NN)"
  - "REVISA OPERADOR: test_wifi_source.py:726 mock namespace bug (preexistente, no arreglado — fase diagnóstica)"

# Actuals (#2632) — chars/4 sobre el entregable realizado (01-PLAN-REUBICACION.md: 32 839 chars)
actuals:
  tokens: 8209
  tasks: 3
  commits: 4

# Tech tracking
tech-stack:
  added: [] # Ninguna dependencia ni herramienta añadida — fase 100% diagnóstico
  patterns:
    - "Bloque de ítem con labels en negrita **Control:**…**Orden:** (analog ROADMAP.md, PATTERNS.md:91)"
    - "Tabla de estado por banda + checklist de aprobación `- [ ]` (los rellena el operador en el plan 04)"
    - "Bloque de cobertura 'ítems P1: N, P2: N, P3: N, sin banda: 0 ✓' (analog REQUIREMENTS.md:36-46)"

key-files:
  created:
    - ".planning/phases/01-auditor-a-ui-y-plan-de-reubicaci-n/01-PLAN-REUBICACION.md - Plan priorizado consolidado (entregable de la fase, contrato de entrada de v2)"
  modified:
    - ".planning/phases/01-auditor-a-ui-y-plan-de-reubicaci-n/baseline_git.txt - BOM UTF-8 eliminado (fix del mecanismo del gate, rutas intactas)"

key-decisions:
  - "D-12: la fórmula D-06 manda sobre la etiqueta P1 del target-state — el cluster obtiene Score 1.0 → P2 y se ordena al inicio de P2 (R-12..R-16); discrepancia documentada para confirmación humana en el plan 04"
  - "Ítems destructivos (R-02, R-03, R-07, R-08, R-09) marcados 'pendiente de confirmación D-09' sin orden de ejecución hasta aprobación explícita en el plan 04"
  - "Los 12 strings nuevos ES del contrato se listan con tr() sin implementar (v2 los implementará en los módulos destino) — contrato del plan"
  - "Hang de la suite (test_wifi_source.py:726) es preexistente (mock de app.ui.wifi_picker.WifiMethodDialog no intercepta el binding import-time de main_window.py:39) y NO se arregla en esta fase diagnóstica; registrado REVISA OPERADOR"
  - "baseline_git.txt normalizado (BOM quitado) para que la comparación de conjuntos del gate sea exacta — desviación documentada"

patterns-established:
  - "Gate de cero código reproducible: extracción del 2º token de git status, igualdad de conjuntos contra baseline_git.txt, y registro de la salida de tests con estado explícito"

requirements-completed: [UI-03]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "Plan de reubicación consolidado 01-PLAN-REUBICACION.md: 17 ítems R-01..R-17 con Score D-06 y banda P1/P2/P3, §1 Resumen por bandas (zero/one/many), §2 Matriz, §3 Plan por zona, §4 Riesgos, §5 Aprobación, §5-bis trazabilidad, §7 Gate de cero código"
    requirement: UI-03
    verification:
      - kind: other
        ref: "python -c \"import pathlib,re; t=...; assert '## Resumen por bandas' in t; assert '## Matriz de puntuación' in t; ...\" (verify tarea 1)"
        status: pass
      - kind: other
        ref: "python -c \"... hn-tn ... assert not missing ...\" (verify tarea 2: trazabilidad 7/7)"
        status: pass
      - kind: other
        ref: "python -c \"... assert out==base ... assert 'Gate de cero c' ...\" (verify tarea 3: igualdad de conjuntos git)"
        status: pass
    human_judgment: true
    rationale: "El contenido (bandas P1/P2/P3, órdenes, ítems destructivos R-02/R-03/R-07/R-08/R-09 y la discrepancia D-12 fórmula vs target-state) requiere aprobación explícita del operador en el checkpoint del plan 04; además el gate de tests no sale 0 (hang preexistente, REVISA OPERADOR) — la automatización verifica estructura y trazabilidad, no la decisión"

# Metrics
duration: 120min
completed: 2026-08-15
status: complete
---

# Plan 01-03: Plan de Reubicación UI Summary

**Plan de reubicación priorizado con matriz de puntuación D-06 (17 ítems R-01..R-17 en bandas P1=5/P2=11/P3=1, trazabilidad 7/7 hallazgos, strings nuevos ES para v2) y gate de cero código con registro REVISA OPERADOR por un hang preexistente de la suite**

## Performance

- **Duration:** 120 min (2 sesiones: borrador §1-§5 + trazabilidad y gate)
- **Started:** 2026-08-15
- **Completed:** 2026-08-15
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments
- **01-PLAN-REUBICACION.md** (32 839 chars) con las 7 secciones del contrato: §1 Resumen por bandas (P1=5 ítems, P2=11 ítems, P3=1 ítem — casos zero/one/many cubiertos con copy singular/plural, sin bandas ocultas), §2 Matriz de puntuación (fila por hallazgo H-NN + matriz de 17 ítems con subpuntuaciones Impacto/Esfuerzo/Riesgo, Score D-06 y banda, 4 ejemplos de cálculo verificables), §3 Plan por zona (Zona A 5, B 5, C 1 + conservados "no reubicar — ya bien ubicado", D 6) con bloque de labels en negrita por ítem, §4 Riesgos y dependencias (tests/i18n/estética + cadenas R-01→subgrupos y R-12→tabs + discrepancia D-12), §5 Estado de aprobación (checklists + tabla por banda + 17 checkboxes), §5-bis Trazabilidad H-NN↔R-NN (7/7 sin huérfanos, cobertura P1: 5, P2: 11, P3: 1, sin banda: 0 ✓), §7 Gate de cero código.
- **Matriz D-06 verificable:** Score = Impacto − (Esfuerzo + Riesgo)/2 aplicada a los 7 hallazgos y 17 ítems; 4 cálculos mostrados a modo de ejemplo (R-01, R-06, R-12, R-16).
- **Los 12 strings nuevos ES del contrato** (Añadir origen…, Dispositivos guardados, …) listados con `tr()` mapeados a sus ítems R-NN (12/12), sin implementar — v2 los implementa.
- **Gate de cero código:** conjuntos git base vs final **idénticos** (4 rutas, igualdad de conjuntos verificada); no se ejecutaron `tools/update_translations.ps1` ni `translate_en.py`; el hang preexistente de la suite queda registrado con estado **REVISA OPERADOR**.
- **Los ítems destructivos** (R-02, R-03, R-07, R-08, R-09) marcados "pendiente de confirmación D-09" sin orden de ejecución (patrón D-09, T-03-02 mitigado).

## Task Commits

Each task was committed atomically:

1. **Task 1: Matriz de puntuación (D-06) y borrador de 01-PLAN-REUBICACION.md (UI-03)** - `32d7536` (docs)
2. **Task 2: Trazabilidad hallazgo ↔ ítem del plan (UI-03)** - `6dbc941` (docs)
3. **Task 3: Gate de cero código — línea base git y suite de tests (UI-03)** - `b14f172` (docs)

**Fix del mecanismo del gate (Rule 3):** `296f92d` (fix: strip UTF-8 BOM from baseline_git.txt)

**Plan metadata:** 4 commits de tarea + 1 fix del gate.

## Files Created/Modified
- `.planning/phases/01-auditor-a-ui-y-plan-de-reubicaci-n/01-PLAN-REUBICACION.md` - Entregable de la fase: plan priorizado con matriz D-06, bandas, plan por zona, riesgos, aprobación, trazabilidad y gate de cero código
- `.planning/phases/01-auditor-a-ui-y-plan-de-reubicaci-n/baseline_git.txt` - Solo bytes de cabecera (BOM UTF-8) eliminados; las 4 rutas de la línea base intactas

## Decisions Made
- **D-12 (fórmula manda):** el cluster "guardar dispositivos" puntúa 1.0 (Esfuerzo=5 definicional) → banda **P2**, aunque el target-state de UI-SPEC lo etiquete P1; se ordena al inicio de P2 (R-12..R-16) y la discrepancia queda para decisión del operador en el plan 04.
- **Destructivos sin orden:** R-02, R-03, R-07, R-08, R-09 quedan "pendiente de confirmación D-09" (checkbox separado en §5) — no reciben orden de ejecución hasta aprobación explícita.
- **Zero-one-many:** las tres bandas están pobladas (5/11/1), así que el copy plural aplica ("5 ítems P1", "11 ítems P2", "1 ítem P3"); la variante zero ("Zona sin ítems de reubicación") se declara como regla, no se omite (UI-03).
- **Strings v2:** los 12 strings nuevos se listan con `tr()` sin implementar — es el contrato del plan (must-have), no un stub accidental.
- **Hang de la suite:** se diagnostica como bug preexistente del test (mock namespace) y se registra REVISA OPERADOR sin arreglarlo (fase diagnóstica, T-03-04).
- **BOM del baseline:** normalizado para que la comparación de conjuntos del gate sea exacta (el verify lee el archivo con encoding utf-8 plano).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] BOM UTF-8 en baseline_git.txt rompía la comparación de conjuntos del gate**
- **Found during:** Task 3 (Gate de cero código)
- **Issue:** `baseline_git.txt` (capturado en el plan 01) tenía un BOM UTF-8 (`\ufeff`) en la primera línea; el verify automatizado lee el archivo con `encoding='utf-8'` plano, así que `'\ufeffapp/i18n/...' != 'app/i18n/...'` y la igualdad de conjuntos daba falso negativo para cualquiera que ejecutara el gate
- **Fix:** Eliminados solo los 3 bytes de cabecera del BOM; las 4 rutas intactas (verificado byte a byte contra HEAD y set-equality tras el fix)
- **Files modified:** `.planning/phases/01-auditor-a-ui-y-plan-de-reubicaci-n/baseline_git.txt`
- **Verification:** `python` set-equality final: `sets equal: True | extra: [] | missing: []`; verify de tarea 3 pasa
- **Committed in:** `296f92d` (commit fix independiente)

**2. [Rule 1 - Bug] Hang de la suite: mock no intercepta el binding import-time de WifiMethodDialog**
- **Found during:** Task 3 (Gate de cero código)
- **Issue:** `python -m unittest discover tests/` no sale 0: cuelga en `test_wifi_source.py:726` (`test_pick_wifi_source_ftp_opens_ftp_picker`). El test mockea `app.ui.wifi_picker.WifiMethodDialog`, pero `main_window.py:39` hace `from app.ui.wifi_picker import WifiMethodDialog` (binding en import-time), así que `_pick_wifi_source()` instancia el diálogo **real** y `dialog.exec()` bloquea para siempre en offscreen. Sonda confirmó `mw.WifiMethodDialog is mock → False`. 12/13 módulos pasan en <90 s; el fallo es preexistente (import y test en código commiteado, `tests/` sin cambios).
- **Fix:** **No arreglado por diseño** — el plan (tarea 3) ordena "no arreglar: la fase es diagnóstico" y la ejecución es v2 (UI-04/UI-05). Se registró la discrepancia con estado **REVISA OPERADOR** en §7 del plan y se remite al checkpoint del plan 04 (fix sugerido: mockear `app.ui.main_window.WifiMethodDialog` o mover el binding).
- **Files modified:** ninguno (solo registro en el plan)
- **Verification:** diagnóstico con sonda read-only + corridas por módulo (timeout 90 s); verify de tarea 3 pasa (solo exige igualdad git + presencia de la sección)
- **Committed in:** `b14f172` (parte del commit de tarea 3)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug diagnosticado sin fix por prohibición del plan)
**Impact on plan:** El fix del BOM era necesario para que el gate fuera verificable; el hang de la suite es preexistente y su tratamiento (registro + REVISA OPERADOR) es el prescrito por el plan. Sin scope creep; la fase sigue siendo 100% diagnóstica (0 cambios en app/ tests/ tools/).

## Issues Encountered
- **Suite de tests cuelga (preexistente):** `test_pick_wifi_source_ftp_opens_ftp_picker` (y por extensión su gemela pairdrop, que nunca llega a ejecutarse por orden alfabético) bloquea el runner completo. 12/13 módulos EXIT 0. **No arreglado** — decisión del plan (fase diagnóstica); fix sugerido para v2: mockear el símbolo en `app.ui.main_window` o cambiar el binding de `main_window.py:39`.
- **BOM del baseline:** artefacto de captura del plan 01 que producía falso negativo en el gate; normalizado (fix 1).

## User Setup Required

None - no external service configuration required. En el plan 04, el operador solo debe revisar y aprobar: bandas P1/P2/P3, los ítems destructivos (checkbox D-09), y la discrepancia D-12 (fórmula → P2 vs target-state → P1).

## Next Phase Readiness
- **Plan 04 (aprobación):** el plan de reubicación está listo con checklists pendientes — solo requiere la aprobación del operador (bandas, destructivos, discrepancia D-12) y revisión del estado **REVISA OPERADOR** del gate de tests.
- **Fase v2 (UI-04/UI-05):** contrato de entrada completo — 17 ítems R-NN con Score, banda, orden, zona, controles, strings nuevos ES con `tr()` y riesgos.
- **Blocker a revisar en plan 04:** hang preexistente de la suite (`test_wifi_source.py:726` + `main_window.py:39`), pendiente de decisión si se arregla en v2 (mock namespace) — registrado en §7 del plan.

---
*Phase: 01-auditor-a-ui-y-plan-de-reubicaci-n*
*Completed: 2026-08-15*
