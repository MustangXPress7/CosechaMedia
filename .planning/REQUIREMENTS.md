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

## Ideas exploradas 2026-08-29

Sesión `/gsd-explore` — definiciones acordadas con el operador. Contexto y
hallazgos con disposición en `.planning/notes/exploracion-reordenar-notificaciones-wifi-ssid.md`.

### REQ-06 · Reorganizar footage (reparador de volcados a mano)

- [ ] El reordenador es una **acción integrada de la app** (no un runner de scripts externos): botón "Reorganizar footage..." con su diálogo
- [ ] El diálogo pide la **carpeta del volcado a mano** (dondequiera que esté); el reordenador solo actúa sobre esa carpeta y nunca toca el árbol ya organizado (`Footage/<Cámara>/<Fecha>` de ingestas previas)
- [ ] Los archivos se **mueven en sitio** (rename/move atómico, sin recopiar y sin verificación MD5), reutilizando `metadata_engine` (ffprobe) para clasificar a `Footage/<Cámara>/<Fecha>`
- [ ] Los archivos no clasificables (sin metadatos útiles) se mueven a `Footage/_SinClasificar/` y quedan listados en un reporte de movimientos
- [ ] Ante una colisión de nombre en el destino, el reordenador pregunta por archivo con una capa "aplicar a todas" (saltar / renombrar con sufijo)
- [ ] El reordenador nunca borra archivos y genera un reporte (fuente → destino, no clasificados, colisiones resueltas)

### REQ-07 · Notificadores inteligentes al acabar la ingesta

- [ ] Existe una **interfaz de notificadores** configurable por proyecto con varios backends (mínimo: email SMTP y Telegram; opcionales: ntfy/Pushover)
- [ ] Los backends usan la interfaz sin dependencias de terceros irresponsables: email vía stdlib `smtplib`; Telegram a través de `python-telegram-bot` (o HTTP ligero de un solo sentido)
- [ ] La notificación se dispara **por sesión al terminar** y, cuando hay fallos, también en error
- [ ] El contenido es un resumen: archivos, tamaño (GB), cámaras, verificación MD5 (ok/fallos) y ruta destino
- [ ] Las credenciales (SMTP/token) se guardan sin exponerse en claro en la DB (revisar patrón actual plaintext)
- [ ] La configuración se hace desde la configuración del proyecto; filosofía sin-nube preservada (salida de red puntual y explícita)

### REQ-08 · WiFi por SSID y contraseña para cámaras (depende de spike)

- [ ] Un diálogo pide **SSID + contraseña** de una red WiFi existente; la app se une a ella por OS (`netsh wlan add profile`+`connect` en Windows, `networksetup -setairportnetwork` en macOS, `nmcli device wifi connect` en Linux) — sin hospedar un AP propio
- [ ] Se añade un **servidor FTP embebido** como receptor de cámaras (el `ftp.py` actual es cliente); las cámaras con FTP-over-WiFi (Canon R5/R6, Sony α7 III/α1/α9 III/FX3, Fuji GFX100 II, Nikon D780/D6) se conectan a la red y suben sin app del fabricante
- [ ] El alcance de modelos se delimita por las cámaras reales de los operadores (research question 2026-08-29) y por el resultado del spike de viabilidad (servidor FTP embebido, privilegios OS, persistencia segura de credenciales de red)
- [ ] Las credenciales de red se avisan como dato sensible (persistencia del SO: perfil cifrado Win, keychain macOS, plaintext root-only Linux)

---
*Requirements definidos: 2026-08-29 — sesión /gsd-explore. REQ-06/07/08 aún sin ruta a fase (v2 candidatas); REQ-08 bloqueado por spike de viabilidad.*
