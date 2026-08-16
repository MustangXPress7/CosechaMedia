# CosechaMedia

## What This Is

Aplicación de escritorio (PySide6/Qt 6, Python 3.11) para producción audiovisual: ingesta verificada (MD5) de tarjetas SD, cámaras y teléfonos (MTP/USB, FTP, WiFi vía PairDrop-style HTTP) a un archivo organizado por cámara/fecha, con detección de metadatos via ffprobe, generación de proxies, rotación de discos y formateo de tarjetas. Orientada a operadores de cámara/plataforma de rodaje en local (sin nube).

## Core Value

Que el operador de cámara pueda vaciar tarjetas SD/cámaras/móviles al archivo del proyecto de forma fiable y sin perder datos — cada archivo copiado con verificación de integridad y organizado correctamente.

## Requirements

### Validated

- ✓ Ingesta verificada por MD5 de SD/cámara a proyectos organizados por cámara/fecha — existing
- ✓ Acceso a dispositivos MTP (Windows COM/WPD) y FTP con staging incremental — existing
- ✓ Recepción WiFi móvil (servidor HTTP local tipo PairDrop con token por remitente) — existing
- ✓ Detección de metadatos (cámara, fecha, codec, fps) via ffprobe con caché LRU — existing
- ✓ Generación de proxies (720p/1080p) via ffmpeg — existing
- ✓ Rotación multi-disco al llenarse un volumen y resume de sesión — existing
- ✓ Formateo de tarjetas (exFAT) tras ingesta — existing
- ✓ Temas oscuro/claro + acentos, i18n ES/EN (ES fuente) — existing
- ✓ Auto-sync periódico de dispositivos registrados — existing
- ✓ Actualizador desde GitHub Releases con verificación SHA-256 — existing

### Active

- [ ] UI-01: Auditoría de la interfaz completa — ventana principal/dashboard, pickers de fuente, asistentes y paneles, y acciones post-ingesta — para localizar botones, opciones y flujos mal ubicados
- [ ] UI-02: Informe de hallazgos por zona con evidencia (ubicación actual, problemas, propuesta de reubicación y justificación de usabilidad para el operador de cámara)
- [ ] UI-03: Plan de reubicación acordado (pero NO implementado en esta fase) — la implementación será una fase posterior

### Out of Scope

- Implementación de reubicaciones — se entrega solo auditoría + plan; la ejecución es una fase posterior (decisión explícita del usuario)
- Reescritura del backend/core (MainWindow 3870 líneas, logging, migraciones) — la UI se revisa sin refactorizar el core; el god object y deuda técnica se documentan pero no se abordan en esta iniciativa
- Rediseño estético completo (nueva identidad, paleta, tipografía) — se mantienen tema oscuro/claro y acentos existentes
- Aplicación web/móvil, sincronización en la nube
- Cambios de comportamiento de ingesta (pipeline MD5, rotación, metadatos) — solo ubicación/presentación

## Context

- Proyecto brownfield: `app/ui/main_window.py` (3.870 líneas) es un god object orquestador; la UI vive en `app/ui/` (10 módulos + assets) sobre `app/core/` (12 módulos).
- `MainWindow` agrupa dashboard, proyectos/sesiones, ingesta, WiFi/QR, MTP/FTP staging, auto-sync, formateo, proxies, detección de cámara y actualizaciones — muchos flujos conviven en una ventana, lo que genera zonas saturadas y opciones dispersas (menús, botones, contextos).
- Diálogos (`DevicePickerDialog`, `FtpPickerDialog`, `SourcePickerDialog`, `SelectiveDumpAssistant`, `WifiMethodDialog`, `ShootInboxPanel`, `AboutDialog`, `ProjectWizard`) tienen patrones propios; la coherencia entre ellos es irregular.
- El operador de cámara usa la app en plató/croma: flujos rápidos (conectar → INICIAR INGESTA → progreso → formatear) deben ser evidentes.
- Tests: 14 suites `unittest` con Qt offscreen; `tests/test_e2e.py` ya conduce `MainWindow.start_ingest`. `main_window.py` no está testeado (gaps documentados en `.planning/codebase/CONCERNS.md`).
- Sin CI (ningún `.github/workflows/` de test; `build.yml` solo empaqueta).
- Estética actual: tema oscuro/claro con acentos, fondo animado de trigo (`wheat_field.py`), paleta en `app/ui/theme.py`.

## Constraints

- **Tech stack**: PySide6 (Qt 6, `>=6.5,<7`), Python 3.11 — no cambiar framework
- **Idioma fuente**: español (los strings UI son literales en ES; catálogo EN via `.ts`/`.qm`) — los textos nuevos deben pasar por `tr()`
- **Compatibilidad**: Windows (incl. MTP COM), macOS, Linux — cambios UI cross-platform
- **No refactor core**: la revisión UI no debe tocar `app/core/` salvo necesidad mínima; los cambios son de `app/ui/`
- **Estética**: mantener tema oscuro/claro + acentos existentes

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Auditoría primero, implementación después | El usuario pidió "análisis primero"; reubicar sin diagnóstico previo produciría cambios a ciegas | ✓ Good |
| Alcance: diagnóstico + plan, no rediseño completo | Revisar dónde y cómo están botones/opciones, proponer reubicación por zona, implementar solo lo acordado | ✓ Good |
| Todos los flujos con igual prioridad | El operador de cámara usa la app de extremo a extremo; ninguna zona es descartable a priori | — Pending |
| Inversión parcial de D-12 (lanzador de orígenes) | El diálogo unificado con 3 pestañas embebidas se rediseñó como lanzador compacto: lista de Guardados por secciones + botones que abren DevicePickerDialog/FtpPickerDialog/cadena WiFi en ventanas propias | ✓ Good — registrado 2026-08-16 (quick 260816-jlt) |

---
*Last updated: 2026-08-15 after initialization*

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state
