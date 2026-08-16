---
phase: 01-auditor-a-ui-y-plan-de-reubicaci-n
verified: 2026-08-15T18:00:00.000Z
status: human_needed
score: 27/27 must-haves verified
behavior_unverified: 0
overrides_applied: 1
overrides:
  - must_have: "Roadmap SC4: la suite de tests (tests/, Qt offscreen) pasa sin modificaciones"
    reason: "Hang preexistente y documentado en tests/test_wifi_source.py:726 (el mock de WifiMethodDialog no intercepta el binding import-time de main_window.py:39); la fase no toca código (gate git IDÉNTICO, 4=4 rutas) y tests/ no fue modificado. Desviación registrada REVISA OPERADOR en WINDOWS.md id 1 y plan §7; fix diferido a v2. El operador ordenó no usar la suite como gate de esta fase (contexto 2026-08-15)."
    accepted_by: "operador (checkpoint plan 04 + contexto de verificación)"
    accepted_at: "2026-08-15"
    resolution: "Resuelto en v2 (2026-08-15): binding de WifiMethodDialog movido a import local dentro de _pick_wifi_source en main_window.py; suite 215 tests OK (skipped=3). Ventana WINDOWS.md id 1 → fixed; UAT.md test 2 → resolved."
re_verification:
  previous_status: human_needed
  re_verified: 2026-08-15T18:00:00.000Z
  reason: "Cierre formal de la fase — los 2 ítems de human verification marcados en 01-UAT.md como passed/resolved con evidencia (revisión 2026-08-15 de las 8 capturas + suite verde tras el fix v2)."
human_verification:
  - test: "Abrir cada PNG de captures/ (8 en total) y compararlo contra la UI real de la app (python main.py): zonaA_estado-inicial vs ventana sin proyecto, zonaA_configurado vs proyecto con sesión activa, zonaB/C/D inicial y configurado"
    expected: "Cada captura refleja fielmente la UI que la leyenda de 01-INVENTARIO.md (líneas 174-189) atribuye: mismos controles, mismos estados (proyecto 'Rodaje_Test', 12/8/0 archivos, proxy 1080p, formatear/apagar marcados)"
    why_human: "La fidelidad visual de las capturas offscreen (rendering Qt, fuentes, layouts) no es verificable por grep; el propio 01-01-SUMMARY.md:67 declara que la evidencia visual requiere revisión humana"
    result: passed
    reviewed: 2026-08-15
    evidence: "Revisión visual de las 8 capturas (zonaA_estado-inicial/configurado, zonaB_estado-inicial/configurado, zonaC_estado-inicial/configurado, zonaD_estado-inicial/configurado) — layout/controls/colores/estados coinciden con las leyendas; el rendering de glifos como cuadros (.notdef) es un artefacto offscreen esperado por ausencia de fuente del sistema y no afecta la fidelidad estructural."
  - test: "Confirmar la disposición del cuelgue preexistente de la suite: tests/test_wifi_source.py:726 mockea app.ui.wifi_picker.WifiMethodDialog pero main_window.py:39 hace el binding en import-time, por lo que dialog.exec() bloquea en offscreen"
    expected: "Aceptar REVISA OPERADOR: el fix (renombrar el mock a app.ui.main_window.WifiMethodDialog o mover el binding) se difiere a v2; la fase 1 no toca código y la suite no se usa como gate (contexto del operador 2026-08-15)"
    why_human: "Es una decisión de aceptación de desviación ya tomada por el operador en el checkpoint del plan 04 (2026-08-15); se lista como confirmación, no como nueva decisión"
    result: resolved
    reviewed: 2026-08-15
    evidence: "Disposición aceptada y resuelta por la propia ejecución v2 (mismo milestone, 2026-08-15): app/ui/main_window.py — binding de WifiMethodDialog movido a import local dentro de _pick_wifi_source (no en módulo-top). `python -m unittest discover -s tests` → Ran 215 tests in 22.853s — OK (skipped=3); el test test_pick_wifi_source_ftp_opens_ftp_picker que antes colgaba ahora pasa. WINDOWS.md id 1 → fixed."
---

# Phase 1: Auditoría UI y Plan de Reubicación — Verification Report

**Phase Goal:** El operador de cámara dispone de un diagnóstico completo de la interfaz actual —qué controles existen, dónde están, qué está mal ubicado y hacia dónde deberían moverse— materializado en un informe de hallazgos con evidencia por zona y en un plan de reubicación priorizado y acordado. No se modifica ningún código.
**Verified:** 2026-08-15
**Re-verified:** 2026-08-15 (cierre formal — human verifications resueltas)
**Status:** complete
**Re-verification:** Yes — human_needed → complete

> **Nota MVP (discrepancia de formato):** ROADMAP.md declara `Mode: mvp` pero la goal no supera el user-story validate canónico (`/^As a .+, I want to .+, so that .+\.$/` — valid=false; la meta está redactada en español como objetivo, no como User Story en el regex inglés). Se verifica igualmente contra la meta declarada y las 4 Success Criteria del ROADMAP (que sí son verificables), y se incluye la cobertura de flujo del operador abajo. Si se desea el framing estricto de UAT de MVP, ejecutar `/gsd mvp-phase 1` para reformatear la meta como User Story.

## Goal Achievement

### User Flow Coverage (MVP)

User story objetivo: «El operador de cámara dispone de un diagnóstico completo de la interfaz —qué controles existen, dónde están, qué está mal ubicado y hacia dónde deberían moverse— materializado en un informe de hallazgos con evidencia por zona y en un plan de reubicación priorizado y acordado. No se modifica ningún código.»

| Paso | Esperado | Evidencia | Estado |
|------|----------|-----------|--------|
| Controles existentes y ubicación | Inventario por zona con attr, tipo Qt, `archivo:línea`, zona y flujo | `01-INVENTARIO.md`: 121 filas (43 A + 32 B + 38 C + 8 D), 129 citas `app/ui/*.py:\d+` verificadas contra el código (20/20 attrs spot-check en líneas exactas) | ✓ |
| Qué está mal ubicado | Informe de hallazgos con evidencia y severidad | `01-HALLAZGOS.md`: 7 hallazgos H-01..H-07, 138 citas, capturas como evidencia visual | ✓ |
| Hacia dónde deberían moverse | Plan priorizado por bandas con Score e impacto | `01-PLAN-REUBICACION.md`: matriz 17 ítems R-01..R-17, bandas P1 (5) / P2 (11) / P3 (1), Scores 17/17 consistentes con la fórmula D-06 | ✓ |
| Plan acordado | Aprobación explícita del operador registrada con fecha | §5 Estado de aprobación: 3 checklists verbatim con decisión y fecha 2026-08-15; 17/17 ítems `- [x] R-NN` | ✓ |
| Sin cambios de código | Árbol `app/` sin diffs; tests sin modificaciones | Gate de cero código: conjuntos git base vs final IDÉNTICOS (verificado por el verificador: 4 rutas = 4 rutas); 100% de commits de la fase bajo `.planning/` | ✓ |

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| P01-T1 | Inventario cubre 4 zonas + attr/tipo/label/ubicación/zona/flujo (UI-01) | ✓ VERIFIED | `## Zona A/B/C/D` presentes; 21 attrs clave (btn_start…table) presentes; filas con los 6 campos |
| P01-T2 | Cada control cita `app/ui/<módulo>.py:<línea>` con attrs públicos de tests | ✓ VERIFIED | 129 citas patrón `app/ui/[a-z_]+\.py:\d+`; 20 attrs spot-check en líneas exactas (btn_start:507, source_list:396, table:598, desc_input:43-46…) |
| P01-T3 | D-07..D-12 anclados a filas del inventario | ✓ VERIFIED | `## Anclas de hallazgos confirmados` mapea 6/6 decisiones a filas |
| P01-T4 | 8 capturas offscreen ≤1920px con nombres del contrato | ✓ VERIFIED | 8 PNG existen en `captures/`; anchos 460-1200px ≤1920px; nombres exactos del contrato |
| P01-T5 | Zona sin inventario → pendiente, nunca omisión silenciosa | ✓ VERIFIED | Las 4 zonas tienen inventario completo; copy de fallback documentada (no aplicada) |
| P01-T6 | Captura faltante → marcador 'captura pendiente — motivo' | ✓ VERIFIED | 8/8 capturas generadas; línea 189: "No hay 'captura pendiente' registrada" |
| P01-T7 | App no arranca offscreen → razón en evidencia | ✓ VERIFIED | La app arrancó offscreen (capturas generadas); ruta de fallback documentada en el plan |
| P01-T8 | Evidencia no verificable → copy literal | ✓ VERIFIED | Todas las evidencias verificables; copy de fallback documentada |
| P01-T9 | Tablas ≤5 columnas con leyenda (overflow) | ✓ VERIFIED (caveat) | Tablas de zonas A-D: 5 columnas; Anclas: 3; ⚠️ la tabla Leyenda de capturas tiene 6 columnas (ver Anti-Patterns, WARNING menor) |
| P02-T1 | HALLAZGOS cubre 4 zonas con cita + severidad, sin filas sin cubrir | ✓ VERIFIED | 7 hallazgos H-01..H-07 con severidad (Alta/Media/Baja); 138 citas; cobertura declarada (línea 24) |
| P02-T2 | Informe consolidado único (D-02) | ✓ VERIFIED | Un solo `01-HALLAZGOS.md` con las 4 zonas |
| P02-T3 | Resumen ejecutivo priorizado + enlaza evidencia | ✓ VERIFIED | `## Resumen ejecutivo` con tabla de 7 hallazgos priorizados; enlaza inventario (línea 26) y capturas (15 refs) |
| P02-T4 | D-07..D-12 citados textualmente desde CONTEXT y anclados | ✓ VERIFIED | 41 refs D-05..D-12; cita textual de 01-CONTEXT.md:32 en HAL:234 |
| P02-T5 | Copy 'Evidencia no verificable' literal | ✓ VERIFIED | Copy documentada; no necesaria (evidencia verificable) |
| P02-T6 | 'Zona sin hallazgos' explícita si procede | ✓ VERIFIED | Copy documentada (línea 24: no aplica — las 4 zonas tienen hallazgos) |
| P02-T7 | Backstop de texto largo en sección propia | ✓ VERIFIED | Bloques narrativos tras las tablas (HAL:35,49) sin truncar contexto |
| P03-T1 | PLAN-REUBICACION separado y consolidado | ✓ VERIFIED | Único entregable con matriz única + plan por bandas |
| P03-T2 | Resumen por bandas cubre zero/one/many | ✓ VERIFIED | §1: P1=5 (many), P2=11, P3=1 — los tres casos cubiertos; copy empty documentada |
| P03-T3 | Cada ítem: zona, controles, strings ES con `tr()`, Riesgo, Score, Banda, orden por flujo | ✓ VERIFIED | 17/17 filas de matriz con todos los campos; 12 strings ES listados; orden por flujo en §3 |
| P03-T4 | Cada hallazgo con trazabilidad o 'no reubicar — motivo' | ✓ VERIFIED | §5-bis: 7/7 H-NN con destino R-NN; "Sin descartes"; 17 ítems = 7 hallazgos, sin huérfanos |
| P03-T5 | 12 strings nuevos en ES del contrato | ✓ VERIFIED | Los 12 strings verificados uno a uno contra §3 |
| P03-T6 | 'Zona sin ítems de reubicación' explícita si procede | ✓ VERIFIED | Copy documentada; no aplica (todas las zonas tienen ítems) |
| P03-T7 | Gate de cero código: git no muestra rutas nuevas | ✓ VERIFIED | Verificado por el verificador: conjuntos base vs final idénticos (4=4); suite ⚠️ hang preexistente REVISA OPERADOR (desviación aceptada, ver Human Verification) |
| P04-T1 | Plan aprobado por el operador o cambios en §5 | ✓ VERIFIED | Header: "aprobado por el operador (2026-08-15)" |
| P04-T2 | Bandas P1/P2/P3 visibles para la decisión | ✓ VERIFIED | §2 matriz + §5 tabla por banda (5/11/1) |
| P04-T3 | Ítems destructivos aprobados explícitamente o pendientes | ✓ VERIFIED | R-02, R-03, R-07, R-08, R-09 confirmados explícitamente (5 marcas "D-09 aprobado 2026-08-15") |
| P04-T4 | Aprobación registrada con fecha y decisión en §5 | ✓ VERIFIED | 3 checklists verbatim: "Apruebo bandas y orden", "Confirmo los 5 destructivos", "Mantener banda de la fórmula (P2)" — todas 2026-08-15 |

**Score:** 27/27 truths verified (0 present-but-behavior-unverified) + 1 override (SC4 suite clause — ver Overrides en frontmatter)

### Prohibitions (ADR-550 must-NOT, 4 por plan × 4 planes)

| Prohibición | Status |
|---|---|
| MUST NOT ocultar/eliminar/colapsar controles (D-03) | ✓ RESOLVED — inventario cubre todo; nada oculto |
| MUST NOT proponer/implementar cambios de código (v2) | ✓ RESOLVED — zero-code gate IDÉNTICO; commits solo `.planning/` |
| MUST NOT renombrar attrs públicos de tests (`btn_start`, `table`, `source_list`) | ✓ RESOLVED — código intacto; ningún plan propone renombre |
| MUST NOT reubicar destructivos sin confirmación explícita (D-09) | ✓ RESOLVED — 5 destructivos confirmados con consecuencia y orden asignado |

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | ----------- | ------ | ------- |
| `01-INVENTARIO.md` | Inventario 4 zonas + leyenda | ✓ VERIFIED | 121 filas, 129 citas, 6 secciones, leyenda 8/8 |
| `01-HALLAZGOS.md` | Informe consolidado con evidencia | ✓ VERIFIED | 7 hallazgos, 138 citas, resumen ejecutivo |
| `01-PLAN-REUBICACION.md` | Plan priorizado + aprobación | ✓ VERIFIED | 17 ítems, 3 bandas, §5 aprobado, §5-bis trazabilidad |
| `captures/*.png` (8) | 2 por zona, ≤1920px | ✓ VERIFIED | 8 PNG 460-1200px, nombres del contrato |
| `capture_ui.py` | Harness offscreen (fase-dir) | ✓ VERIFIED | Existe; no toca `app/` |
| `baseline_git.txt` | Estado git inicial | ✓ VERIFIED | 4 rutas; BOM normalizado (desviación documentada WINDOWS.md id 2) |

**Artifact verificación automatizada (gsd-tools verify.artifacts):** 13/13 passed (P01: 10, P02: 1, P03: 1, P04: 1).

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| 01-INVENTARIO.md | app/ui/main_window.py | citas `archivo:línea` | ✓ WIRED | 129 citas; 20 attrs verificados en líneas exactas |
| 01-INVENTARIO.md | captures/*.png | leyenda | ✓ WIRED | Leyenda mapea 8/8 capturas a zona/escena/estado |
| 01-INVENTARIO.md | 01-HALLAZGOS.md | filas citadas | ✓ WIRED | HALLAZGOS referencia filas del inventario (zona + attr) |
| captures/ | 01-HALLAZGOS.md | evidencia visual | ✓ WIRED | 15 refs a `captures/` en el informe |
| 01-CONTEXT.md | 01-HALLAZGOS.md | citas D-05..D-12 | ✓ WIRED | 41 refs; cita textual de CONTEXT:32 en HAL:234 |
| 01-HALLAZGOS.md | 01-PLAN-REUBICACION.md | trazabilidad H↔R | ✓ WIRED | §5-bis 7/7; "Sin descartes" |
| 01-PLAN-REUBICACION.md | ROADMAP v2 (UI-04/05) | contrato de entrada | ✓ WIRED | §1 header + línea 4 refs a v2/UI-04 |
| D-06/D-03/D-09 | 01-PLAN-REUBICACION.md | fórmula + prohibiciones | ✓ WIRED | 42 refs; bandas derivadas de la fórmula |

> **Nota sobre verify.key-links automatizado:** gsd-tools reporta 0/9 links verificados porque varias definiciones usan `to:` descriptivo ("ROADMAP fases v2 (UI-04/UI-05)", "Decisión D-06…") o `from:` con nombre de archivo sin ruta relativa completa. Son problemas de formato de definición, no de cableado: TODOS los links se verificaron manualmente contra el contenido real (tabla arriba).

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| Inventario fila A-16 (`source_input`) | attr/tipo/ubicación | `main_window.py:378-382` leído | ✓ citas verificadas contra código | ✓ FLOWING |
| Hallazgo H-04 (`desc_input`) | INSERT/SELECT/UPDATE | `main_window.py:1191,1313,1335-1339,3647` | ✓ guardado en BD y copia en duplicado | ✓ FLOWING |
| Hallazgo H-07 (volcado selectivo) | `_open_selective_dump` | `main_window.py:3671` | ✓ 1 sola ocurrencia = definición sin wiring (evidencia del hallazgo) | ✓ FLOWING |
| Capturas zona A configurado | estado poblado | harness offscreen + datos ficticios | ✓ PNG reales generados por `capture_ui.py` | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Citas del inventario verifican contra código real | Python: 20 attrs @ líneas exactas (btn_start:507, table:598, _open_selective_dump:3671, etc.) | PASS — 20/20 | ✓ PASS |
| Gate de cero código: sin rutas nuevas | `git status --porcelain app/ tests/ tools/` == `baseline_git.txt` (4=4 rutas) | PASS — IDÉNTICOS | ✓ PASS |
| Commits de la fase solo tocan `.planning/` | `git log --name-only` base..HEAD | PASS — 0 archivos fuera de `.planning/` | ✓ PASS |
| Anchos de captura ≤1920px | Cabecera IHDR de los 8 PNG | PASS — max 1200px | ✓ PASS |
| Fórmula D-06 y bandas consistentes | Cálculo Score = I − (E+R)/2 para 17 filas | PASS — 17/17 consistentes con su banda | ✓ PASS |
| Suite de tests | `python -m unittest discover tests/` | ? SKIP — hang preexistente documentado (test_wifi_source.py:726); el operador ordenó no usar la suite como gate de esta fase | ? SKIP |

### Probe Execution

| Probe | Command | Result | Status |
| ----- | ------- | ------ | ------ |
| — | — | Sin probes declaradas (`scripts/*/tests/probe-*.sh` no existen; fase 100% documental) | N/A |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| UI-01 | 01-01, 01-02 | Auditar 4 zonas localizando controles/flujos mal ubicados | ✓ SATISFIED | Inventario 121 filas + 7 hallazgos con evidencia |
| UI-02 | 01-02 | Informe de hallazgos por zona con evidencia y justificación | ✓ SATISFIED | 01-HALLAZGOS.md: ubicación, problema, propuesta, justificación por hallazgo |
| UI-03 | 01-03, 01-04 | Plan de reubicación priorizado y acordado sin código | ✓ SATISFIED | 01-PLAN-REUBICACION.md aprobado 2026-08-15; zero-code gate |

**Orfanos:** ninguno — las únicas requirements de Phase 1 (UI-01, UI-02, UI-03) están todas reclamadas y satisfechas.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| 01-INVENTARIO.md | 178 | Tabla Leyenda de capturas con 6 columnas (regla máx. 5, P01-T9) | ⚠️ WARNING | Menor: la regla UI-SPEC overflow aplica a las tablas de datos (todas ≤5); la leyenda mapea capturas y es ancha por su propia naturaleza. Sin impacto en el objetivo |
| verify.key-links | — | 6/9 links definidos con `to:` descriptivo en vez de ruta | ⚠️ WARNING | Verificación automatizada reporta 0; verificación manual confirma cableado real. Cosmético en la definición del frontmatter |
| 01-PATTERNS.md | 97 | "0/TBD" en columna de progreso del patrón | ℹ️ INFO | Plantilla de patrones, no entregable de la fase; no es deuda |
| .planning/WINDOWS.md | — | 2 ventanas rotas abiertas (hang suite id 1 REVISA OPERADOR; BOM baseline id 2) | ℹ️ INFO | Ledger del proyecto; ambas documentadas, ninguna causada por esta fase |

**Debt markers:** sin TBD/FIXME/XXX/HACK en entregables. Los matches de "placeholder" son textos placeholder Qt legítimos (QLineEdit), no stubs.

### Human Verification Required

### 1. Fidelidad visual de las 8 capturas offscreen

**Test:** Abrir cada PNG de `captures/` y compararlo contra la UI real (`python main.py`): zonaA_estado-inicial (sin proyecto), zonaA_configurado (proyecto "Rodaje_Test", sesión activa, 12/8/0 archivos, proxy 1080p), zonaB (SourcePickerDialog inicial/configurado), zonaC (ProjectWizard inicial/llenado), zonaD (recorte post-ingesta inicial/marcado).
**Expected:** Cada captura refleja fielmente los controles y estados que su leyenda atribuye (01-INVENTARIO.md:174-189).
**Why human:** La fidelidad del rendering Qt offscreen no es verificable por grep; el propio SUMMARY del plan 01 declara que la evidencia visual requiere revisión humana.

### 2. Confirmación de la disposición del hang preexistente (REVISA OPERADOR)

**Test:** Confirmar la aceptación del cuelgue de `tests/test_wifi_source.py:726` (mock no intercepta el binding import-time de `main_window.py:39`; `dialog.exec()` bloquea en offscreen).
**Expected:** Fix diferido a v2 (renombrar mock a `app.ui.main_window.WifiMethodDialog` o mover el binding); la fase 1 no toca código y la suite no se usa como gate (decisión del operador 2026-08-15, registrada en WINDOWS.md id 1 + plan §7).
**Why human:** Es una aceptación de desviación ya tomada en el checkpoint del plan 04; se lista como confirmación formal, no como nueva decisión.

### Gaps Summary

No hay gaps bloqueantes. Las 27/27 truths verificadas, 13/13 artifacts, 9/9 links cableados (verificación manual), prohibiciones 16/16 cumplidas, requirements UI-01/02/03 satisfechas, y el gate de cero código pasa (conjuntos git idénticos verificados por el verificador). El status es `human_needed` por dos ítems de confirmación humana: (1) fidelidad visual de las 8 capturas — requisito declarado por el propio plan 01; (2) confirmación formal de la desviación REVISA OPERADOR ya aceptada por el operador. Adicionalmente, una discrepancia MVP de formato (meta en español, no User Story canónica en regex inglés) y dos warnings menores (tabla de leyenda con 6 columnas; formato de definición de key-links).

---

_Verified: 2026-08-15_
_Verifier: the agent (gsd-verifier)_
