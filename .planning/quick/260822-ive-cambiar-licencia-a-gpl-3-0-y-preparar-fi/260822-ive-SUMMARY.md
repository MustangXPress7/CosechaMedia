---
phase: 260822-ive
plan: 01
subsystem: infra
tags: [licensing, gpl-3.0, spdx, ci, github-actions, codesign, macos, signpath, docs]

# Dependency graph
requires:
  - phase: none
    provides: repositorio de autor único (ventana legal para relicensing limpio)
provides:
  - LICENSE con el texto canónico GPLv3 (base legal GPL-3.0-or-later del repo)
  - Firma ad-hoc macOS en CI antes de comprimir y hashear (sidecar .sha256 = artefacto firmado)
  - docs/SIGNING.md — hoja de ruta de firma (SignPath Foundation Windows, workaround Gatekeeper macOS, estado Linux)
affects: [release-process, updater-verification, external-contributions, milestone-close]

# Actuals (#2632) — pairs with the plan's `estimate` to calibrate future estimates.
actuals:
  tokens: 12424   # chars/4 over the realized diff (49696 chars)
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Orden CI macOS: Info.plist → codesign ad-hoc → ditto → sha256sum (el sidecar siempre corresponde al artefacto firmado)"
    - "Secretos de firma documentados solo en docs/; el workflow no los referencia hasta tener credenciales"

key-files:
  created:
    - docs/SIGNING.md
    - .planning/quick/260822-ive-cambiar-licencia-a-gpl-3-0-y-preparar-fi/260822-ive-SUMMARY.md
  modified:
    - LICENSE
    - README.md
    - main.py
    - .github/workflows/build.yml

key-decisions:
  - "D-01 aplicado: licencia GPL-3.0-or-later con texto canónico descargado de gnu.org y validado por marcadores estructurales (nunca escrito de memoria)"
  - "D-02 aplicado: firma ad-hoc mínima en macOS (--force --deep -s -, sin --options runtime); SignPath Foundation solo como roadmap documentado, sin CI especulativo"
  - "Solo main.py lleva cabecera GPL en este quick; LICENSE es la referencia normativa (evitar edición masiva de módulos)"

patterns-established:
  - "Cambio de workflow confinado al script de un paso existente con gate de recuento de pasos (9) — sin YAML nuevo ni pasos espurios"
  - "README bilingüe: cualquier cambio se aplica en espejo EN/ES con posiciones equivalentes"

requirements-completed: []

# Metrics
duration: 14min
completed: 2026-08-22
status: complete
---

# Quick 260822-ive: Licencia GPL-3.0 + preparación de firma de binarios Summary

**Relicensing a GPL-3.0-or-later (LICENSE canónica + README bilingüe + cabecera en main.py) y firma ad-hoc de macOS en CI con hoja de ruta de firma documentada en docs/SIGNING.md**

## Performance

- **Duration:** 14 min
- **Started:** 2026-08-22T12:01:15Z
- **Completed:** 2026-08-22T12:15:41Z
- **Tasks:** 3
- **Files modified:** 5 (1 creado)

## Accomplishments

- LICENSE reemplazada por el texto íntegro y canónico de la GPLv3 (674 líneas), descargada por TLS de gnu.org y validada por marcadores estructurales («GNU GENERAL PUBLIC LICENSE», «Version 3, 29 June 2007», «TERMS AND CONDITIONS», «How to Apply These Terms»).
- Ambas mitades del README (EN/ES) declaran **GPL-3.0-or-later** con párrafos espejo que invitan a contribuir; secciones Credits intactas; cero referencias residuales a PolyForm fuera de `.planning/`.
- `main.py` abre con el aviso de copyright/licencia GPL estándar y compila (`py_compile` ok).
- El job macOS de CI firma ad-hoc el bundle (`codesign --force --deep -s -`) ANTES de `ditto` (zip) y de calcular el sidecar `.sha256` — el hash publicado corresponde al artefacto firmado y la verificación de `updater.py` sigue siendo válida. Los otros dos jobs y el recuento de pasos (9) no cambian.
- Nuevo `docs/SIGNING.md` en español: estado actual de firma/integridad por plataforma, instrucciones de primera apertura en macOS (clic derecho → Abrir / `xattr -dr com.apple.quarantine`), roadmap SignPath Foundation para Windows (secretos `SIGNPATH_API_TOKEN`/`SIGNPATH_ORGANIZATION_ID`/`SIGNPATH_PROJECT_SLUG`, esqueleto YAML comentado marcado como NO añadible hasta tener credenciales) y estado Linux. Enlazado desde ambas mitades del README (1 enlace por mitad).

## Task Commits

Each task was committed atomically:

1. **Task 1: LICENSE → GPLv3 canónica + secciones de licencia del README (EN/ES) + cabecera en main.py** - `69f3555` (chore)
2. **Task 2: Firma ad-hoc de macOS en build.yml** - `d5bcd70` (ci)
3. **Task 3: docs/SIGNING.md (hoja de ruta de firma) + enlaces desde ambas mitades del README** - `aec250a` (docs)

## Files Created/Modified

- `LICENSE` — texto canónico GPLv3 descargado de https://www.gnu.org/licenses/gpl-3.0.txt (sustituye PolyForm Noncommercial 1.0.0)
- `README.md` — secciones License/Licencia espejo con SPDX `GPL-3.0-or-later` + un enlace a SIGNING por mitad tras el párrafo del autoactualizador
- `main.py` — cabecera de aviso GPL/Copyright antepuesta a los imports
- `.github/workflows/build.yml` — 2 líneas de codesign ad-hoc dentro del paso «Prepare assets (macOS)», entre el heredoc del plist y `mkdir -p release`
- `docs/SIGNING.md` — nuevo; hoja de ruta de firma de binarios en español

## Decisions Made

- D-01 (del orquestador): GPL-3.0-or-later. Sin menciones a dual licensing/pago (fuera de alcance).
- D-02 (del orquestador): macOS firma ad-hoc mínima SIN `--options runtime` (hardened runtime sin entitlements revisados puede romper Qt); Windows vía SignPath Foundation queda como solicitud manual futura documentada, sin tocar el workflow; Linux sin cambios.
- El texto de la licencia nunca se escribió de memoria: descarga directa del canonical URL con fallback previsto y halt si los marcadores fallan (mitigación T-IVE-01).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. La descarga de gnu.org funcionó a la primera con TLS 1.2; todos los gates de verificación pasaron al primer intento.

## User Setup Required

None - no external service configuration required. (La solicitud a SignPath Foundation es un paso manual futuro del mantenedor, documentado en docs/SIGNING.md.)

## Next Phase Readiness

- El repo tiene un estado legal inequívoco que habilita contribuciones externas bajo GPL-3.0-or-later.
- Cuando lleguen las credenciales de SignPath, seguir docs/SIGNING.md § «Windows — SignPath Foundation (mantenedores)»: secretos de GitHub + paso entre «Prepare assets (Windows)» y «Upload release assets».
- Nota: la próxima Release publicará zips de macOS firmados ad-hoc — el sidecar `.sha256` corresponderá al zip ya firmado.

---
*Quick: 260822-ive*
*Completed: 2026-08-22*

## Self-Check: PASSED

- LICENSE, README.md, main.py, .github/workflows/build.yml, docs/SIGNING.md: FOUND en disco.
- Commits de tarea verificados como ancestros de HEAD: `69f3555`, `d5bcd70`, `aec250a`.
- Diff total confinado a los 5 ficheros del plan (sin cambios en `app/core/`, sin dependencias nuevas).
