---
status: investigating
trigger: Bug 1 QR: Proyecto en blanco + añadir QR → se añaden todos los QR ya creados. Posible sync_wifi_sessions crea sesiones para todos los senders. También verificar guardado de proyectos.
created: 2026-08-20
updated: 2026-08-20
---

## Symptoms
- Expected behavior: Al crear proyecto en blanco y añadir un QR, solo se debe asociar ese QR/sender al proyecto nuevo, sin heredar QRs de otros proyectos.
- Actual behavior: Se añaden todos los QR ya creados existentes.
- Error messages: No especificado; comportamiento incorrecto de listado.
- Timeline: Reportado 2026-08-20.
- Reproduction: Crear proyecto nuevo en blanco → añadir QR → aparecen todos los QR previos.

## Current Focus
hypothesis: sync_wifi_sessions crea sesiones para todos los senders en lugar de filtrar por proyecto, o el proyecto nuevo hereda estado global de senders/QR.
next_action: gather initial evidence
