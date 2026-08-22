---
phase: 260822-ml7
plan: 01
subsystem: packaging/docs
tags: [homebrew, cask, macos, distribution, tap, readme]
status: complete
requires:
  - releases/v* tag con asset CosechaMedia-macos.app.zip (patrón URL verificado en .github/workflows/build.yml)
provides:
  - packaging/homebrew/Casks/cosechamedia.rb — cask listo para el tap propio del propietario
  - docs/HOMEBREW.md — guía completa de instalación, publicación del tap y mantenimiento por release
  - README bilingüe con subsección Homebrew espejo EN/ES
affects: []
key-files:
  created:
    - packaging/homebrew/Casks/cosechamedia.rb
    - docs/HOMEBREW.md
  modified:
    - README.md
decisions:
  - "Rama B del precondition: la release v1.5.0.b3 no existe (HEAD → 404 al ejecutar) ⇒ sha256 :no_check documentado, tal como planificó el planner"
  - "desc del cask en inglés (convención homebrew-cask); comentarios nuevos en español salvo ese campo (restricción del plan)"
  - "--no-quarantine recomendado y justificado en docs/HOMEBREW.md con cross-ref a SIGNING.md sin duplicar su workaround xattr"
metrics:
  duration: ~20 min
  completed: 2026-08-22
  tasks: 3
  commits: 3
  files_changed: 3
  lines_added: 92
actuals:
  tokens: 23000   # chars/4 sobre el diff realizado (+92 líneas en 3 archivos)
  tasks: 3
  commits: 3
---

# Quick Task 260822-ml7: Cask de Homebrew para distribución macOS — Summary

Distribución macOS vía Homebrew: cask propio (`packaging/homebrew/Casks/cosechamedia.rb`) para un tap del propietario, guía completa en español (`docs/HOMEBREW.md`) para publicar el tap y mantener el cask por release, y anuncio bilingüe simétrico EN/ES en el README — sin tocar `app/core/` ni `.github/workflows/`.

## Tasks Executed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Cask de Homebrew en packaging/homebrew/Casks/cosechamedia.rb | ffd2957 | packaging/homebrew/Casks/cosechamedia.rb |
| 2 | docs/HOMEBREW.md — guía de tap propio y checklist por release | cd1feb2 | docs/HOMEBREW.md |
| 3 | Subsección Homebrew espejo en ambas mitades del README | a314038 | README.md |

## Verification Results

**Task 1** — todos los gates True: `exists`, `do-open`, `version`, `url-template` (`v#{version}`), `name/desc/homepage`, `dep-formula` (ffmpeg), `dep-arch` (:arm64), `app-stanza`, `sha256-honest` (:no_check), `closes-end`. `ruby-syntax`: omitida (sin Ruby en esta máquina; permitido por los criterios done).

**Task 2** — todos los gates True: comandos literales `brew tap MustangXPress7/tap` e `install --cask --no-quarantine MustangXPress7/tap/cosechamedia`, procedimiento de hash (`shasum`/`Get-FileHash`/`certutil`), cross-ref SIGNING.md, caveat Intel, guard `:arm64`, fuente de versión `__version__`, nota `brew upgrade`, `no-xattr-dup`.

**Task 3** — todos los gates True: `hb-en:1`, `hb-es:1`, headings espejo, `tap-cmds:2`, `install-cmds:2` idénticos, `symmetry:True` (EN idx 3049 < corte 7221 < ES idx 10372). Diff revisado: exactamente las dos subsecciones nuevas (+18 líneas), nada colateral.

**Global** — `core-touch: False`, `ci-touch: False`; working tree solo contiene cambios previos de `.planning/` (ajenos a esta tarea). Total: 3 archivos, +92 líneas, 0 eliminaciones.

## Deviations from Plan

None — plan ejecutado exactamente como escrito. El precondition de Task 1 se resolvió por la rama por defecto esperada (petición HEAD única al asset → HTTP 404 ⇒ rama B con `sha256 :no_check`).

## Known Stubs

Ninguno que bloquee el objetivo del plan (los entregables son artefactos de empaquetado/documentación). Dos elementos intencionales trazados para el verificador:

1. **`sha256 :no_check`** en `packaging/homebrew/Casks/cosechamedia.rb:11` — intencional per plan y threat T-ML7-01 (la release v1.5.0.b3 no existe aún): comentario de fijado en el propio cask + checklist obligatoria por release en docs/HOMEBREW.md. Resolver fijando el hash real desde la primera release publicada.
2. **`ruby -c` no ejecutado** — sin Ruby disponible en la máquina; la validez DSL se verificó por patrones estructurales (todos los gates). Recomendado validar sintaxis con `ruby -c` o `brew audit` desde una Mac antes del primer push al tap.

> Nota broken-windows: el intento de registrar ambos items en `.planning/WINDOWS.md` falló por una inconsistencia PREVIA a esta sesión (frontmatter dice open=1 pero las 2 entradas existentes son fixed/waived ⇒ open real 0). No se reparó por quedar fuera del alcance de este quick task; registrar manualmente o reparar el contador antes del próximo `/gsd-ship` si se quiere trazar ahí.

## Threat Model Compliance

- **T-ML7-01** (sha256 :no_check): mitigado — comentario obligatorio en el cask + checklist en HOMEBREW.md ✓
- **T-ML7-02** (repo del tap mal nombrado): mitigado — HOMEBREW.md exige el nombre EXACTO `homebrew-tap` y explica la resolución `user/tap` → `github.com/<user>/homebrew-tap` ✓
- **T-ML7-03** (--no-quarantine debilita Gatekeeper): mitigado — justificación documentada + alternativa manual enlazada a SIGNING.md sin duplicar comando ✓
- **T-ML7-SC**: N/A confirmado — cero paquetes instalados, cero dependencias nuevas ✓

## Manual Step Pending (user_setup del plan)

El propietario debe crear el repo público `github.com/MustangXPress7/homebrew-tap` y subir `Casks/cosechamedia.rb` siguiendo docs/HOMEBREW.md §«Publicar el tap» (per D-01: paso MANUAL fuera de este repo, NO automatizado).

## Self-Check: PASSED

Verificado 2026-08-22: los 3 archivos entregables existen en disco y los 3 commits (ffd2957, cd1feb2, a314038) están en el historial.
