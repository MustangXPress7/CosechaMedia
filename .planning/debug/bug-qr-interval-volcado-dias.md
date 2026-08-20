---
status: resolved
trigger: Bug 3: Abrir intervalo de contenido de QR muestra opciones de volcar por días. Integración pobre I15/I18.
created: 2026-08-20
updated: 2026-08-20
---

## Symptoms
- Expected behavior: Al abrir intervalo de contenido desde QR, las opciones de volcado por días deben estar coherentes con el modo de contenido seleccionado y la sesión actual. No debe mostrarse volcado por días si la integración I15/I18 no está completa.
- Actual behavior: Se muestran opciones de volcado por días con integración pobre I15/I18, posiblemente el modo ventana no calcula correctamente.
- Error messages: No especificado.
- Timeline: Reportado 2026-08-20, código de volcado por días tocado recientemente.
- Reproduction: Abrir intervalo de contenido desde QR → ver opciones de volcado por días.

## Current Focus
hypothesis: Modo WINDOW incompleto y falta persistencia de content_mode en sesión provoca incoherencia UI al abrir desde QR.
next_action: gather initial evidence

## Resolution
root_cause: DB queries `get_sessions`/`get_session` omitían columna `content_mode`, impidiendo persistencia del modo; `SelectiveDumpAssistant` no cargaba modo/sesión al abrir diálogo, mostrando opciones de intervalo/ventana para fuentes WiFi/FTP que deben quedar en modo ALL.
fix: Añadida columna `content_mode` a SELECTs de `db.get_sessions` y `db.get_session`; `SelectiveDumpAssistant.__init__` ahora carga modo y filtro de sesión, fuerza `content_mode=ALL` y deshabilita radios para device_id wifi:/ftp:; normalización de selección completa a filtro nulo.
verification: Tests `test_selective_dump` pasan (27/27). UI muestra bloqueado para QR y modo persiste entre aperturas.
