# Phase 1: Auditoría UI y Plan de Reubicación - Pattern Map

**Mapped:** 2026-08-15
**Files analyzed:** 2 (entregables de documentación; fase sin código)
**Analogs found:** 2 / 2 (más 3 analogs secundarios)
**Nota de fase:** Los entregables son documentos Markdown en `.planning/phases/01-*/` — no hay código, tests ni i18n que copiar. Los "patrones" aquí son convenciones de estructura/formato de documentación ya establecidas en el repo. RESEARCH.md no existe (research omitida por el usuario): la fuente de verdad de estructura es UI-SPEC.md (contrato de entregables) + los analogs de `.planning/`.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `01-HALLAZGOS.md` | audit-report | static/transform | `.planning/codebase/CONCERNS.md` | exact (misma estructura hallazgo→evidencia→fix) |
| `01-PLAN-REUBICACION.md` | relocation-plan | static/transform | `.planning/ROADMAP.md` | role-match (plan con prioridad + orden) |
| `captures/*.png` (8 capturas) | evidence-media | static | — | no-analog (media; convención de naming en UI-SPEC) |

## Pattern Assignments

### `01-HALLAZGOS.md` (audit-report, static/transform)

**Analog primario:** `.planning/codebase/CONCERNS.md` — el único doc del repo con formato "hallazgo por ítem" (Issue → evidencia → fix). **Analog secundario:** `.planning/codebase/STRUCTURE.md` (convenciones de tablas de inventario) y `01-UI-SPEC.md:212-234` (contrato exacto de secciones y columnas).

**Header de documento** (copiar patrón de `CONCERNS.md:1-4` y `01-CONTEXT.md:1-4`):
```markdown
<!-- refreshed: 2026-08-15 -->
# Codebase Concerns

**Analysis Date:** 2026-08-15
```
Para el informe: `# Fase 1: Informe de Hallazgos de UI` + `**Elaborado:** 2026-08-15` + `**Estado:** <draft/revisado>` (convención CONTEXT.md:3 `**Status:** Ready for planning`).

**Estructura de cada hallazgo** (copiar el bloque de ítem de `CONCERNS.md:8-12` — Tech Debt — y `:46-51` — Known Bugs). El patrón repo es: título en negrita con contexto entre paréntesis, luego bullets con labels en negrita:
```markdown
**`main_window.py` god object (3870 lines):**
- Issue: `app/ui/main_window.py` mixes UI construction, business orchestration ...
- Files: `app/ui/main_window.py`
- Impact: Any change risks UI-thread freezes ...
- Fix approach: Extract `app/core/ingestion_manager.py` ...
```
```markdown
**`rename_camera` uses forward-slash LIKE pattern that never matches Windows paths:**
- Symptoms: Renaming a camera does not update `files.source_path`/`dest_path` rows on Windows.
- Files: `app/core/ingestor.py` (`rename_camera`), invoked from `app/ui/main_window.py` `_on_camera_rename_needed` (1877-1885)
- Trigger: User renames a camera after files ingested ...
- Workaround: None; paths stay stale. Manual DB edit required.
- Fix approach: Use `os.sep`/both separators ...
```
**Mapeo al contrato UI-SPEC (`01-UI-SPEC.md:221`):** el hallazgo H-XX debe contener: zona, flujo, control (attr), ubicación actual (`archivo:línea` + attr), problema detectado, heurísticas violadas, propuesta de reubicación, justificación de usabilidad, referencias de evidencia (widget inv + captura), severidad. El formato repo (title + `- Label:` bullets) cubre el contrato: label `Files:` → ubicación actual; labels nuevos `Problema:`, `Heurísticas violadas:`, `Propuesta:`, `Justificación:`, `Evidencia:`, `Severidad:`.

**Citas de evidencia** (copiar formato `CONCERNS.md` en todo el doc): path + `:línea` inline entre backticks, con rango `archivo:inicio-fin`; a veces con el método/atributo entre paréntesis: `` `app/ui/main_window.py:2130-2163` (`_detect_camera_for_session`, `_prompt_unknown_camera`) `` (CONCERNS.md:62).

**Etiquetas de severidad** — la app no tiene precedente; UI-SPEC define el vocabulario: Bloqueante / Alto / Medio / Bajo (`01-UI-SPEC.md:106`). Formatearlas como `CONCERNS.md` formatea prioridad: `- Priority: High` (CONCERNS.md:258) → en el informe `- Severidad: Alto`, etc.

**Tabla de inventario de widgets** (copiar convención de tabla de `STRUCTURE.md:96-120` "Key File Locations" + contrato UI-SPEC:220):
```markdown
**Entry Points:**
- `main.py`: `main()` — the only process entry point
- `app/ui/main_window.py:1366`: `MainWindow.start_ingest` — ingest pipeline entry
```
Mapeo: la tabla inventario del informe (columnas ID, attr, tipo Qt, texto/label, `archivo:línea`, zona, flujo) usa el mismo estilo de citas `archivo:línea` + `attr` + descripción. Regla de legibilidad (backstop UI-SPEC:272): **máximo 5 columnas** por tabla; si el contrato pide 7, abreviar celdas (ej. zona/flujo con siglas A/B/C/D + flujo `c/i/f/r`) y explicar la leyenda encima.

**Checklist de conservación (D-03)** — copiar convención de checkbox de `REQUIREMENTS.md:12-14`:
```markdown
- [ ] **UI-01**: Se auditan las cuatro zonas de la interfaz ...
```
El checklist "todo control del inventario aparece en el estado objetivo" usa `- [ ] <attr> → <destino>` por control, con `- [x]` solo cuando el plan de reubicación confirme el destino (criterio de éxito 3, ROADMAP.md:27).

**Footer** (copiar `CONCERNS.md:284-286`):
```markdown
---

*Concerns audit: 2026-08-15*
```
→ `*Informe de hallazgos: 2026-08-15*` (el mismo patrón aparece en CONTEXT.md:113-114 `*Phase: 1-Auditoría UI y Plan de Reubicación*` + `*Context gathered: 2026-08-15*`).

---

### `01-PLAN-REUBICACION.md` (relocation-plan, static/transform)

**Analog primario:** `.planning/ROADMAP.md` (plan con fases, prioridad y orden). **Analog secundario:** `.planning/REQUIREMENTS.md:36-46` (tabla de trazabilidad + bloque de cobertura) y `01-UI-SPEC.md:224-229,246-252` (contrato de secciones + fórmula de la matriz).

**Bloque de fase/ítem con prioridad** (copiar estructura de `ROADMAP.md:19-30`):
```markdown
### Phase 1: Auditoría UI y Plan de Reubicación
**Goal**: El operador de cámara dispone de un diagnóstico completo ...
**Mode**: mvp
**Depends on**: Nothing (first phase)
**Requirements**: UI-01, UI-02, UI-03
**Success Criteria** (what must be TRUE):
  1. Las cuatro zonas ... quedan auditadas ...
```
Mapeo: cada ítem de reubicación del plan usa el mismo patrón de labels en negrita: `**Control:**` (attr + label), `**Ubicación actual:**` (archivo:línea), `**Destino propuesto:**`, `**Strings nuevos:**`, `**Riesgo:**` (tests/i18n/estética), `**Score:**`, `**Orden:**` — obligatorio por el contrato de reubicación (`01-UI-SPEC.md:200-208`).

**Tabla de estado/progreso** (copiar `ROADMAP.md:37-39`):
```markdown
| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Auditoría UI y Plan de Reubicación | 0/TBD | Not started | - |
```
Mapeo: tabla de progreso de implementación por banda P1/P2/P3, con columna `Estado: Aprobado / Pendiente` (criterio de éxito 3 = "revisado y aprobado por el usuario", ROADMAP.md:27).

**Trazabilidad y cobertura** (copiar `REQUIREMENTS.md:36-46`):
```markdown
## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| UI-01 | Phase 1 | Pending |

**Coverage:**
- v1 requirements: 3 total
- Mapped to phases: 3
- Unmapped: 0 ✓
```
Mapeo: tabla de trazabilidad ítem→zona→requisito (UI-01/02/03) + bloque de cobertura: "ítems P1: N, P2: N, P3: N, sin banda: 0 ✓" (regla cero-uno-muchos UI-SPEC:270 — singular/plural: "1 ítem P1" / "3 ítems P1").

**Lista de requisitos como checklist** (copiar `REQUIREMENTS.md:12-14`): ítems `- [ ] **<ID>**: ...` con estado pendiente hasta aprobación del usuario.

---

### `captures/*.png` (evidence-media, static)

**No hay analog en el repo** (ninguna carpeta de capturas existe). El contrato de naming viene de `01-UI-SPEC.md:234`: mínimo 2 por zona × 4 zonas = 8 capturas; PNG ≤ 1920px; nombres `zonaA_estado-inicial.png`, `zonaA_configurado.png`, etc.; tabla de leyendas en el informe. La ruta de captura relativa en el informe debe ser `captures/<nombre>.png` (columna Evidencia).

## Shared Patterns

### Metadatos de cabecera (todos los docs de `.planning/`)
**Fuentes:** `CONCERNS.md:1-4`, `CONTEXT.md:1-4`, `DISCUSSION-LOG.md:1-8`
**Aplicar a:** `01-HALLAZGOS.md` y `01-PLAN-REUBICACION.md`
```markdown
# <Título del documento>
**<Label>:** <fecha ISO>      (p.ej. **Elaborado:** 2026-08-15)
**<Label>:** <estado>          (p.ej. **Status:** Ready for planning)
```

### Footer de firma (todos los docs)
**Fuente:** `CONCERNS.md:284-286`, `CONTEXT.md:111-114`, `REQUIREMENTS.md:49-50`
```markdown
---

*<Nombre del documento>: <fecha>*
```

### Citas `archivo:línea` (todos los docs técnicos)
**Fuente:** `CONCERNS.md` (16+ call sites), `STRUCTURE.md:96-120`, `01-UI-SPEC.md` (uso intensivo)
Formato: backticks, `path.py:inicio-fin`, método entre paréntesis si aporta: `` `app/ui/main_window.py:2130-2163` (`_detect_camera_for_session`) ``. Siempre que un hallazgo nombre un control, la cita incluye su atributo público (`btn_start`, `table`, `source_list`) porque así los nombran los tests (`tests/test_e2e.py`).

### Tablas Markdown (todos los docs)
**Fuente:** `CONCERNS.md`, `ROADMAP.md:37-39`, `REQUIREMENTS.md:36-42`, `DISCUSSION-LOG.md:14-17`
- Pipe tables con separador `|-------|`.
- **Máximo 5 columnas** en tablas anchas (backstop UI-SPEC:272 — evitar scroll horizontal del visor). Tablas de >5 columnas: abreviar celdas con leyenda.
- Texto largo en celdas: resumen corto + detalle en subsección (backstop long-text UI-SPEC:269 — el informe registra qué opción usó).

### Etiquetas de severidad/prioridad
**Fuente:** `01-UI-SPEC.md:106-107` (vocabulario) + `CONCERNS.md:258,264,270` (formato)
- Informe: `- Severidad: Bloqueante | Alto | Medio | Bajo`
- Plan: `- Banda: P1 (≥ 2.5) | P2 (1.0–2.4) | P3 (< 1.0)` — fórmula `Score = Impacto − (Esfuerzo + Riesgo)/2` (UI-SPEC:246-252)
- Formato de label en negrita igual que `- Priority: High`.

### Checklist `- [ ]` / `- [x]`
**Fuente:** `REQUIREMENTS.md:12-14`, `01-UI-SPEC.md:294-303` (Checker Sign-Off)
Usos: checklist de conservación D-03 (informe), estado de aprobación por ítem (plan), sign-off final del plan ("revisado y aprobado").

### Copy de estados vacíos (solo estos dos docs)
**Fuente:** `01-UI-SPEC.md:102-109`
- Informe, zona sin hallazgos: "Zona sin hallazgos" + "Ningún control de esta zona requiere reubicación. Se mantiene la ubicación actual."
- Plan, zona sin ítems: "Zona sin ítems de reubicación"
- Evidencia no verificable: "Evidencia no verificable — registrar el motivo en la columna Evidencia y volver a capturar en la fase de ejecución."
- Inventario sin cobertura: se registra como pendiente, nunca se omite en silencio (UI-SPEC:264).

### Idioma
**Fuente:** todo `.planning/` — español (español fuente; los strings propuestos para tr() se listan tal cual, `01-UI-SPEC.md:111-112`).

## No Analog Found

| Elemento | Role | Data Flow | Reason | Referencia a usar |
|----------|------|-----------|--------|-------------------|
| Matriz impacto×esfuerzo (tabla de scores) | — | static/transform | Ningún doc del repo tiene matriz de scoring; los docs de plan (ROADMAP) solo listan prioridad | `01-UI-SPEC.md:246-252` — fórmula completa (`Score = Impacto − (Esfuerzo + Riesgo)/2`, bandas P1/P2/P3, pesos, orden por flujo, dependencia D-12) |
| Inventario de widgets con coordenadas | — | static/transform | STRUCTURE.md tiene tablas de ubicación pero no inventario por atributo con tipo Qt | `01-UI-SPEC.md:220` (columnas) + `STRUCTURE.md:122-146` (convención de naming de atributos `btn_*`, `_btn_*`, `chk_*`) |
| Capturas offscreen (media) | evidence-media | static | No existe carpeta de capturas ni precedente | `01-UI-SPEC.md:234` (naming + dimensiones + tabla de leyendas) |

## Metadata

**Analog search scope:** `.planning/` completo (PROJECT, REQUIREMENTS, ROADMAP, STATE, codebase/*, phases/01-*/), `README.md`, `CLAUDE.md` (proyecto)
**Files scanned:** 14 archivos Markdown en `.planning/` + 2 raíz
**Pattern extraction date:** 2026-08-15
