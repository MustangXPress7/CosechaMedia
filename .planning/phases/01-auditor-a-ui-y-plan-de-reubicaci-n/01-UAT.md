---
status: testing
phase: 01-auditor-a-ui-y-plan-de-reubicaci-n
source: [01-VERIFICATION.md]
started: 2026-08-15T00:00:00Z
updated: 2026-08-15T00:00:00Z
---

## Current Test

number: 1
name: Fidelidad visual de las 8 capturas offscreen
expected: |
  Cada captura refleja fielmente la UI que la leyenda de 01-INVENTARIO.md (líneas 174-189) atribuye: mismos controles, mismos estados (proyecto "Rodaje_Test", 12/8/0 archivos, proxy 1080p, formatear/apagar marcados).
awaiting: user response

## Tests

### 1. Fidelidad visual de las 8 capturas offscreen
expected: |
  Abrir cada PNG de captures/ (8 en total) y compararlo contra la UI real de la app (python main.py): zonaA_estado-inicial vs ventana sin proyecto, zonaA_configurado vs proyecto con sesión activa, zonaB/C/D inicial y configurado. Cada captura refleja fielmente los controles y estados que su leyenda atribuye (01-INVENTARIO.md:174-189).
result: [pending]

### 2. Confirmación de la disposición del hang preexistente (REVISA OPERADOR)
expected: |
  Confirmar la aceptación del cuelgue de tests/test_wifi_source.py:726 (el mock de WifiMethodDialog no intercepta el binding import-time de main_window.py:39; dialog.exec() bloquea en offscreen). El fix se difiere a v2; la fase 1 no toca código y la suite no se usa como gate (decisión del operador 2026-08-15, registrada en WINDOWS.md id 1 y plan §7).
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
