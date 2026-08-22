---
phase: 260822-gi3
plan: 01
subsystem: docs
tags: [readme, documentation, i18n, v1.5]
requires: []
provides:
  - "README bilingual feature lists describing shipped v1.5 functionality"
affects: []
tech-stack:
  added: []
  patterns: []
key-files:
  created: []
  modified:
    - README.md
decisions:
  - "Version story told by features, not numbers — no version literal added anywhere (locked plan decision)"
  - "Folder examples Footage/<Camera>/<Date> / Footage/<Cámara>/<Fecha> kept unchanged (UI organization-mode labels still valid)"
  - "WiFi QR sources locked to all-content mode omitted from bullet list as too granular for README level (locked plan decision)"
metrics:
  duration: 0.2 hours
  completed: 2026-08-22
status: complete
actuals:
  tokens: 1115
  tasks: 2
  commits: 1
---

# Quick Task 260822-gi3: Actualizar README para versión 1.5 Summary

**One-liner:** README bilingual feature lists now describe all six shipped v1.5 feature areas (per-session selective dump, CSV reports, one-step projects, flexible shoot dates, persistent device naming, tintable SVG icons) with mirror symmetry between EN and ES halves.

## What Was Done

### Task 1: Update Features sections symmetrically in both language halves

Four edits per language half, applied exactly as specified:

- **EN `## Features` / ES `## Características`:**
  - Replaced the `(WIP)` camera-detection bullet with completed **Device detection / Detección de dispositivos** (automatic scanning + persistent device names set at source registration).
  - Inserted three new bullets after it: **Selective dump per session / Volcado selectivo por sesión**, **Flexible shoot dates / Fechas de rodaje flexibles**, **One-step projects / Proyectos en un solo paso**.
  - Extended **Post-ingest / Post-ingesta** bullet with CSV reports (card contents before dumping, integrity after ingest).
  - Extended **Themes and accents / Temas y acentos** bullet with tintable SVG icons following the accent.

Nothing else touched: intro taglines, folder examples, Requirements, Download, phones/cameras sections, Building, Project structure, License, Credits, images, links — all byte-identical.

### Task 2: Integrity gates

Visual diff review confirmed both hunks sit entirely inside the EN Features block and ES Características block, tone matches the surrounding concise style, and both halves read as translations of each other. Automated gates all green (see below). No fixes required — verification-only task, no additional commit.

## Verification Results

| Gate | Expected | Actual |
|------|----------|--------|
| Bullet symmetry (`^- \*\*` per half) | equal counts | **18/18** |
| Stale WIP claim removed | 0 occurrences | old-en-left: 0 · old-es-left: 0 |
| New sentinel strings present once per half | 10 strings × 1 | all 1 (incl. accented needles verified via char-code construction) |
| URL-set equality vs pre-task baseline | diff count 0 | **url-diff-count: 0** |
| Language anchors intact | 2 | **anchors: 2** |
| Hunk confinement to Features regions | 0 outside | **hunks-outside-features: 0** |
| Sentinel content untouched | ≥1 each | PolyForm license ×2, Windows exe ×2, build.yml ×4, Compilar.bat ×2, Primitive FTPd ×4, both Footage examples ×1 |

Markdown structure unchanged: same headings, same blank-line rhythm, no trailing-whitespace or em-dash artifacts introduced.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Plan arithmetic] Bullet-count expectation corrected from 16/16 to 18/18**
- **Found during:** Task 1 verification
- **Issue:** The plan's done criterion predicted `bullets en/es: 16/16`, assuming 13 bold bullets per half before edits. The actual baseline was 15 per half — the count missed the two `- **Over USB (MTP)**` / `- **Over WiFi**` bullets in the "Ingest from phones and cameras" section (present in both language halves).
- **Resolution:** No content change needed. After inserting the three new bullets per half, counts are 18/18 — perfectly symmetric, 1:1 mirror relationship intact, which is the substantive invariant the check protects. Only the expected value in the plan's arithmetic was stale.
- **Files modified:** none (documentation of expectation only)

**2. [Rule 3 - Blocking adjustment] Task 2 gates run against HEAD~1 baseline**
- **Found during:** Task 2
- **Issue:** The gates compare working tree against `HEAD`, but the atomic per-task commit requirement means HEAD already contains Task 1's changes — running against HEAD would have compared the file to itself (vacuously green).
- **Fix:** Ran the URL-equality and hunk-confinement gates against `HEAD~1` (the pre-task commit `9061ee7`'s tree state), preserving the gates' intent: prove nothing outside the two feature blocks moved relative to before execution.
- **Files modified:** none

## Authentication Gates

None occurred.

## Known Stubs

None — documentation-only change.

## Threat Flags

None — no new security-relevant surface (doc-only edit; threat model T-GI3-01/T-GI3-02 dispositions satisfied: no secrets or internal URLs introduced, every feature claim traces to a completed initiative ID recorded in STATE.md).

## Self-Check: PASSED

- FOUND: README.md (modified, committed as 768ceb0)
- FOUND: .planning/quick/260822-gi3-actualizar-readme-para-version-1-5-con-l/260822-gi3-SUMMARY.md
- FOUND: commit 768ceb0 in git log
- Working tree clean for task scope; remaining untracked files are pre-existing and out of scope (`.planning/quick/260821-nem-.../`, `app/ui/ftp_status.py`)
