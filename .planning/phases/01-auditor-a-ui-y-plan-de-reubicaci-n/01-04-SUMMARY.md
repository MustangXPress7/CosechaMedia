---
phase: 01-auditor-a-ui-y-plan-de-reubicaci-n
plan: 04
subsystem: ui
tags: [aprobacion-operador, plan-reubicacion, bandas-p1-p2-p3, items-destructivos-d09, discrepancia-d12, gate-cero-codigo]

# Dependency graph
requires:
  - phase: 01-auditor-a-ui-y-plan-de-reubicaci-n
    provides: "Plan de reubicación 01-PLAN-REUBICACION.md (§1-§7) con bandas P1/P2/P3, ítems destructivos pendientes D-09 y discrepancia D-12 documentada (producto del plan 01-03)"
provides:
  - "Aprobación del operador registrada en 01-PLAN-REUBICACION.md §5: bandas P1/P2/P3 y orden aprobados, 5 ítems destructivos D-09 confirmados con orden de ejecución dentro de su flujo, discrepancia D-12 resuelta (se mantiene la banda de la fórmula P2)"
  - "Contrato de entrada de la fase v2 cerrado: 01-PLAN-REUBICACION.md pasa de draft a aprobado por el operador (2026-08-15) — listo para la ejecución UI-04/UI-05"
affects:
  - "Fase v2 UI-04/UI-05 (ejecución de las reubicaciones R-01..R-17 en el orden aprobado, incluidos los destructivos con sus confirmaciones de runtime)"
  - "REVISA OPERADOR: test_wifi_source.py:726 hang preexistente (se mantiene documentado sin cambios; fix diferido a v2)"

# Actuals (#2632) — chars/4 sobre el diff realizado (01-PLAN-REUBICACION.md: 15 689 chars de diff)
actuals:
  tokens: 3922
  tasks: 1
  commits: 2

# Tech tracking
tech-stack:
  added: [] # Ninguna dependencia ni herramienta añadida — plan 100% registro de decisión
  patterns:
    - "Checklist de aprobación con decisión verbatim del operador + fecha en cada checkbox (auditable)"
    - "Ítems destructivos D-09: de 'pendiente de confirmación' a 'aprobado con orden' sin cambiar su naturaleza destructiva (las confirmaciones de runtime ya existían)"

key-files:
  created: []
  modified:
    - ".planning/phases/01-auditor-a-ui-y-plan-de-reubicaci-n/01-PLAN-REUBICACION.md - §5 Estado de aprobación completado (aprobado), header actualizado, órdenes de los 5 destructivos asignadas, discrepancia D-12 resuelta, 17 checkboxs por ítem marcados"

key-decisions:
  - "Bandas y orden: APROBADO — 'Apruebo bandas y orden' (P1: R-10 → R-06 → R-01; P2: R-11 → R-12 → R-13 → R-14 → R-15 → R-04 → R-05 → R-17; P3: R-16)"
  - "Ítems destructivos D-09: CONFIRMADOS — 'Confirmo los 5 destructivos' (R-02 formatear orígenes, R-03 apagar al acabar, R-07 eliminar origen, R-08 eliminar sesión, R-09 eliminar proyecto); reciben orden dentro de su flujo: P1 formatear R-02 → R-03 tras R-01; P2 conectar R-07, R-09; P2 ingestar R-08"
  - "Discrepancia D-12: RESUELTA — 'Mantener banda de la fórmula (P2)': el cluster D-12 (R-12..R-16) se mantiene en P2 (la banda se deriva del Score D-06)"
  - "La fase 01 queda cerrada con el plan de reubicación aprobado como contrato de entrada de v2 (UI-04/UI-05)"
  - "El REVISA OPERADOR (hang preexistente test_wifi_source.py:726) se mantiene documentado sin cambios — fix diferido a v2"
  - "Consistencia del documento: al dar orden a los destructivos, también se actualizaron el §1 (nota de destructivos), §3 intro, §4 (discrepancia → RESUELTA) y §5-bis (notas de trazabilidad) para que el plan aprobado no se contradiga"

patterns-established:
  - "Asignación de orden de ejecución a ítems destructivos SOLO tras confirmación explícita del operador (patrón D-09: del checkbox separado en §5 al campo 'Orden:' en §3, con marca 'D-09 aprobado 2026-08-15')"
  - "Renumeración de órdenes por flujo del operador (conectar → ingestar → formatear → reorganizar): los destructivos aprobados ocupan su ranura de flujo y el resto se renumeró (P2-6..P2-8 → P2-9..P2-11) sin alterar la secuencia aprobada de los no destructivos"

requirements-completed: [UI-03]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "Aprobación del operador registrada en 01-PLAN-REUBICACION.md §5: bandas P1/P2/P3 y orden aprobados, 5 ítems destructivos D-09 confirmados con orden dentro de su flujo, discrepancia D-12 resuelta manteniendo la banda de la fórmula (P2), 17 checkboxs por ítem marcados, tabla de estado por banda 'Aprobado (operador, 2026-08-15)'"
    requirement: UI-03
    verification:
      - kind: other
        ref: "python verify-approval-01-04.py — 21 checks PASS (header aprobado, checklists [x] con decisiones verbatim, tabla de estado, órdenes P1-4/P1-5/P2-6/P2-7/P2-8 y renumeración P2-9/10/11, sin restos 'pendiente'/'draft')"
        status: pass
      - kind: other
        ref: "git status --porcelain app/ tests/ tools/ — conjunto idéntico a baseline_git.txt (4 rutas preexistentes; gate de cero código mantenido)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Fase 01 cerrada: plan de reubicación aprobado como contrato de entrada de la fase v2 (UI-04/UI-05), con el REVISA OPERADOR del hang preexistente (test_wifi_source.py:726) documentado y diferido a v2"
    verification:
      - kind: other
        ref: "git log — docs(01-04) commit e21bde8: 41 inserciones/41 borrados en 01-PLAN-REUBICACION.md (solo .planning/, sin app/ tests/ tools/)"
        status: pass
    human_judgment: true
    rationale: "El cierre de la fase y el arranque de v2 dependen de que el operador confirme que las decisiones registradas en §5 coinciden con su intención (aprobación, orden de los destructivos, mantenimiento de la banda P2 para D-12); además el hang REVISA OPERADOR requiere decisión sobre su fix en v2"

# Metrics
duration: 10min
completed: 2026-08-15
status: complete
---

# Phase 01 Plan 04: Aprobación del Plan de Reubicación — Summary

**Aprobación del operador registrada en el plan de reubicación: bandas P1/P2/P3 y orden aprobados ('Apruebo bandas y orden'), 5 ítems destructivos D-09 confirmados con orden de ejecución dentro de su flujo ('Confirmo los 5 destructivos'), discrepancia D-12 resuelta ('Mantener banda de la fórmula (P2)') — fase 01 cerrada con el plan como contrato de entrada de v2 (UI-04/UI-05)**

## Performance

- **Duration:** 10 min
- **Started:** 2026-08-15T17:05:00Z (aprox.)
- **Completed:** 2026-08-15T17:08:10Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- **§5 Estado de aprobación completado en `01-PLAN-REUBICACION.md`:** las 3 checklists de cabecera marcadas con la decisión verbatim del operador y fecha (2026-08-15): bandas P1/P2/P3 y orden ("Apruebo bandas y orden"), ítems destructivos D-09 ("Confirmo los 5 destructivos") y discrepancia D-12 ("Mantener banda de la fórmula (P2)").
- **Los 5 ítems destructivos (R-02, R-03, R-07, R-08, R-09) dejan de estar "pendiente de confirmación D-09" y reciben orden de ejecución dentro de su flujo:** P1 formatear R-02 → R-03 tras R-01 (P1-4, P1-5); P2 conectar R-07, R-09 (P2-6, P2-7); P2 ingestar R-08 (P2-8). Los no destructivos se renumeraron sin alterar la secuencia aprobada (R-04 → P2-9, R-05 → P2-10, R-17 → P2-11). La marca "D-09 aprobado 2026-08-15" en cada campo `Orden:` deja constancia de la confirmación explícita (patrón D-09 cumplido: nunca implícito).
- **Tabla de estado por banda** actualizada de "Pendiente de aprobación (plan 04)" a **"Aprobado (operador, 2026-08-15)"** para P1 (5 ítems), P2 (11 ítems) y P3 (1 ítem); los 17 checkboxs por ítem R-01..R-17 marcados `[x]`.
- **Header del plan** actualizado: `**Estado:** draft — pendiente de aprobación` → `**Estado:** aprobado por el operador (2026-08-15) — contrato de entrada de la fase v2 (UI-04/UI-05)`.
- **Consistencia del documento aprobado:** §1 (nota de destructivos), §3 intro, §4 (discrepancia D-12 → RESUELTA) y §5-bis (trazabilidad) actualizados para reflejar la aprobación; no queda ninguna referencia a "pendiente de confirmación" ni "draft" en el plan.
- **Gate de cero código mantenido:** el conjunto de rutas modificadas bajo `app/` `tests/` `tools/` es idéntico a `baseline_git.txt` (4 rutas preexistentes); este plan solo tocó `.planning/`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Revisión y aprobación del plan de reubicación (UI-03)** - `e21bde8` (docs) — checkpoint human-verify respondido por el operador con aprobación; registro de la decisión en `01-PLAN-REUBICACION.md`

**Plan metadata:** `(próximo commit: 01-04-SUMMARY.md)`

## Files Created/Modified

- `.planning/phases/01-auditor-a-ui-y-plan-de-reubicaci-n/01-PLAN-REUBICACION.md` - §5 Estado de aprobación completado (aprobado, 2026-08-15): checklists [x] con decisiones verbatim, tabla de estado por banda, 17 checkboxs por ítem; header → aprobado; órdenes de los 5 destructivos asignadas (P1-4/P1-5, P2-6/P2-7/P2-8) y renumeración P2-9/10/11; discrepancia D-12 resuelta; §1/§3/§5-bis consistentes

## Decisions Made

- **Bandas y orden:** APROBADO — "Apruebo bandas y orden" (P1: R-10 → R-06 → R-01; P2: R-11 → R-12 → R-13 → R-14 → R-15 → R-04 → R-05 → R-17; P3: R-16).
- **Ítems destructivos D-09:** CONFIRMADOS — "Confirmo los 5 destructivos" (R-02 formatear orígenes, R-03 apagar al acabar, R-07 eliminar origen, R-08 eliminar sesión, R-09 eliminar proyecto); reciben orden dentro de su flujo (ver §3 "Orden:").
- **Discrepancia D-12:** RESUELTA — "Mantener banda de la fórmula (P2)": el cluster D-12 (R-12..R-16) se ejecuta en P2, no en P1 (la banda se deriva del Score D-06).
- **Renumeración P2:** al insertar los destructivos en su flujo, los no destructivos pasaron de P2-6/7/8 a P2-9/10/11 — la secuencia relativa aprobada (R-11→…→R-15→R-04→R-05→R-17) no cambia.
- **REVISA OPERADOR:** el hang preexistente de la suite (`test_wifi_source.py:726`) se mantiene documentado sin cambios; fix diferido a v2.

## Deviations from Plan

None - plan executed exactly as written. El checkpoint human-verify fue respondido por el operador con aprobación total; el executor registró la decisión verbatim en §5 sin desviaciones (no se tocó `app/`, `tests/` ni `tools/`).

## Issues Encountered

- **Working tree con modificaciones preexistentes fuera de alcance:** `git status` muestra modificaciones de línea base bajo `app/` (`cosechamedia_en.qm`, `cosechamedia_en.ts`, `main_window.py`), `tools/translate_en.py` (el conjunto baseline del gate de cero código — sin cambios respecto a la línea base) y `.gitignore`/`.planning/STATE.md` (propiedad del orquestador). Este plan solo commiteó `01-PLAN-REUBICACION.md`; el resto queda fuera de alcance y sin tocar.
- **Hang de la suite (preexistente, no encontrado en este plan):** el registro REVISA OPERADOR de §7 se mantiene tal cual (fix diferido a v2, UI-04/UI-05).

## User Setup Required

None - no external service configuration required. La única acción humana era la aprobación del plan, ya realizada por el operador (2026-08-15).

## Next Phase Readiness

- **Fase 01 CERRADA:** el plan de reubicación está aprobado y es el contrato de entrada de la fase v2 (UI-04/UI-05) — 17 ítems R-NN con Score, banda, orden (incluidos los 5 destructivos con sus confirmaciones D-09), zona, controles, strings nuevos ES con `tr()` y riesgos.
- **Listo para:** planificar la fase v2 (UI-04/UI-05) sobre el plan aprobado, respetando el orden por flujo (conectar → ingestar → formatear → reorganizar) y las prohibiciones D-03 (no ocultar controles) / renombrar widgets públicos acoplados a tests.
- **Pendiente para v2:** decisión sobre el fix del hang REVISA OPERADOR (`test_wifi_source.py:726` / `main_window.py:39`).

---
*Phase: 01-auditor-a-ui-y-plan-de-reubicaci-n*
*Completed: 2026-08-15*

## Self-Check: PASSED

- FOUND: `.planning/phases/01-auditor-a-ui-y-plan-de-reubicaci-n/01-PLAN-REUBICACION.md`
- FOUND: `.planning/phases/01-auditor-a-ui-y-plan-de-reubicaci-n/01-04-SUMMARY.md`
- FOUND: commit `e21bde8` (docs(01-04): registrar aprobacion del operador del plan de reubicacion)
- 21/21 checks de verificación del plan PASAN (aprobación registrada verbatim, órdenes asignadas, gate de cero código mantenido)
