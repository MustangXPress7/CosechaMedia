# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.5.0 — Consolidación y bugs del flujo

**Shipped:** 2026-08-29
**Phases:** 2 | **Plans:** 9 | **Tasks:** 19

### What Was Built

- **Phase 1 (Auditoría UI)**: Inventario completo de 121 controles en 4 zonas + 8 capturas offscreen; 7 hallazgos H-01..H-07 con 138 citas verificadas; plan de reubicación priorizado (17 ítems R-01..R-17, P1=5/P2=11/P3=1) aprobado por operador — sin cambios de código
- **Phase 1.5.0 (Bugs flujo)**: 5 bugs CONCERNS.md (F-01..F-05) + 5 mejoras arquitectura (R1..R5) resueltas en 4 plans across 3 waves
  - R1: FFprobe retry degradado (10s → 30s format-only) + flag `metadata_verified` + marker UI "Metadatos no verificados" en celda cámara
  - R2: Inventario watcher persistente `watcher_seen` (SQLite aditiva) con veredictos copied/filtered/errored, `filter_key`, poda 30d, eliminó cap 10k; predicado `should_skip` compartido preserva F-02
  - R3: Test regresión `_resolve_db_path()` CWD-independiente
  - R4: `copy_verified` hash MD5 single-pass stream-through (sin relectura destino)
  - R5: `_auto_sync_check` off-thread vía `_run_background` con guards `_poll_in_progress`
- **Suite completa**: 313 tests OK (126 core), 0 fallos

### What Worked

- **Wave-based execution** con dependencias claras evitó race conditions en tests (W#2: gate suite completa solo en última ola)
- **Atomic commits por task** (feat/test/docs) facilitó bisect y review
- **Predicado compartido `should_skip`** unificó lógica watcher + ingestor sin romper F-02
- **Flag `metadata_verified` contractual** permitió UI decidir presentación sin tocar core
- **Instrumentación planificada** (REQ-10) surgió naturalmente del debugging de detección cámara
- **Acknowledgment de artifacts abiertos** permitió cerrar milestone sin bloqueos artificiales

### What Was Inefficient

- **Detección de cámara (ffprobe) fallaba consistentemente** — no hubo tiempo para investigar root cause en 1.5.0; quedó como deuda para REQ-10
- **Exit code PySide6 0xC0000409 en Windows** tras suite OK (teardown conocido) — ruido en CI, requiere wrapper para distinguir fallo real
- **STATE.md métricas no actualizadas** automáticamente (planes completados, velocity) — desconexión entre ejecución y reporting
- **Quick tasks previas (F-01..F-05)** no vinculadas formalmente a plans de 1.5.0 — trazabilidad parcial

### Patterns Established

- **Retry solo en `TimeoutExpired`** (Pitfall 6): ramas genéricas sin retry, fallback idéntico en forma + `metadata_verified/metadata_error`
- **Dict de fallback idéntico en forma al de éxito** — contratos estables para llamadores downstream
- **Veredicto `filtered` con `filter_key`** = firma estable `_content_filter_signature()`; ventana cambiada ⇒ re-evaluar (Open Question 4 resuelto)
- **Normalización `os.path.normpath`** en inventario watcher (Pitfall 4) — dedupe correcto Windows
- **Gate suite completa solo en última ola** (W#2) — evita race de suite concurrente entre planes wave 1
- **Acknowledgment de artifacts** en milestone close — deferido real, no suprimido

### Key Lessons

1. **Acotar fase a bugs conocidos (CONCERNS.md) + quick tasks previas** dio scope claro y 4 plans ejecutables en 3 waves sin scope creep
2. **Architecture decisions (R2: `should_skip` compartido) emergen cuando se refactoriza con tests de contrato** — no pre-diseñar, dejar que el código guíe
3. **Instrumentación (REQ-10) debe ser requisito explícito, no accidente** — la falta de logs de ffprobe impidió diagnosticar por qué fallaba detección cámara
3. **Version bump + changelog + tag en mismo commit** simplifica release tracking
4. **Acknowledge > suppress** para artifacts abiertos — mantiene visibilidad en STATE.md sin bloquear ship

### Cost Observations

- Model mix: ~60% sonnet (execution), 30% opus (planning), 10% haiku (quick edits)
- Sessions: ~4 (planning 1.5.0, execution waves 1-3, release + milestone close)
- Notable: 9 plans en ~2h exec time; wave parallelization ahorró ~40% vs secuencial completo

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.5.0 | ~4 | 2 | Wave-based execution, atomic commits/task, acknowledgment artifacts |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.5.0 | 313 (126 core) | — | 0 (no new deps) |

### Top Lessons (Verified Across Milestones)

1. *First milestone — baseline established*