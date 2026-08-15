# Requirements: CosechaMedia

**Defined:** 2026-08-15
**Core Value:** Que el operador de cámara pueda vaciar tarjetas SD/cámaras/móviles al archivo del proyecto de forma fiable y sin perder datos — cada archivo copiado con verificación de integridad y organizado correctamente.

## v1 Requirements

Requisitos para la iniciativa de auditoría y plan de reubicación de la UI. Cada uno mapea a las fases del roadmap.

### Auditoría UI

- [ ] **UI-01**: Se auditan las cuatro zonas de la interfaz — ventana principal/dashboard, pickers de fuente (MTP/FTP/WiFi), asistentes y paneles (SelectiveDump, ShootInbox, About, ProjectWizard) y acciones post-ingesta (formateo, proxies, reorganizar, apagado) — localizando botones, opciones y flujos mal ubicados
- [ ] **UI-02**: Se documenta un informe de hallazgos por zona en `.planning/` con evidencia: ubicación actual de cada control, problema detectado, propuesta de reubicación y justificación de usabilidad para el operador de cámara
- [ ] **UI-03**: Se produce un plan de reubicación priorizado y acordado (por zona, con impacto estimado y orden de implementación) sin implementar ningún cambio de código

## v2 Requirements

Diferidos a una fase futura. Registrados pero fuera del roadmap actual.

### Implementación de reubicaciones

- **UI-04**: Se implementan las reubicaciones acordadas en el plan (UI-03) sin romper flujos existentes
- **UI-05**: Verificación visual y funcional post-cambio (estética y tests no se ven afectados; `tests/` siguen pasando con Qt offscreen)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Implementación de reubicaciones (UI-04/UI-05) | Decisión explícita del usuario: "solo plan ahora"; ejecución en fase posterior |
| Refactor del core (MainWindow god object, logging, migraciones DB) | Documentado en CONCERNS.md pero fuera de esta iniciativa |
| Rediseño estético completo | Se mantienen tema oscuro/claro y acentos existentes |
| Cambios de comportamiento de ingesta | Solo ubicación/presentación, no pipeline |
| App web/móvil, nube | Fuera del producto desktop local |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| UI-01 | Phase 1 | Pending |
| UI-02 | Phase 1 | Pending |
| UI-03 | Phase 1 | Pending |

**Coverage:**
- v1 requirements: 3 total
- Mapped to phases: 3
- Unmapped: 0 ✓

---
*Requirements defined: 2026-08-15*
*Last updated: 2026-08-15 — traceability confirmed in ROADMAP.md (UI-01, UI-02, UI-03 → Phase 1, único slice MVP: auditoría + informe + plan, sin cambios de código)*
