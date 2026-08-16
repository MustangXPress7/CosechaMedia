---
status: complete
phase: 01-auditor-a-ui-y-plan-de-reubicaci-n
source: [01-VERIFICATION.md]
started: 2026-08-15T00:00:00Z
updated: 2026-08-15T00:00:00Z
closed: 2026-08-15
---

## Resumen

La fase 01 (Auditoría UI y Plan de Reubicación) queda cerrada el 2026-08-15 con los 2 tests humanos resueltos y el plan `01-PLAN-REUBICACION.md` aprobado (UI-03). El contrato de entrada de la fase v2 (UI-04/UI-05) es el plan aprobado; los 17 ítems R-01..R-17 han sido ejecutados sobre `app/ui/` en la misma tanda de trabajo y la suite completa (215 tests) pasa OK (skipped=3), de modo que la ventana rota id 1 (suite hang) queda cerrada y la disposición REVISA OPERADOR queda resuelta por la propia ejecución v2.

## Tests

### 1. Fidelidad visual de las 8 capturas offscreen
expected: |
  Abrir cada PNG de captures/ (8 en total) y compararlo contra la UI real de la app (python main.py): zonaA_estado-inicial vs ventana sin proyecto, zonaA_configurado vs proyecto con sesión activa, zonaB/C/D inicial y configurado. Cada captura refleja fielmente los controles y estados que su leyenda atribuye (01-INVENTARIO.md:174-189).
result: passed
evidence: |
  Revisión 2026-08-15 (operador + agente) de los 8 PNG de captures/:
  - zonaA_estado-inicial: campos vacíos, sin tabla, dos pills pequeñas grises a la izquierda, panel derecho vacío — coincide con la leyenda "ventana sin proyecto".
  - zonaA_configurado: formulario poblado, tabla con fila, barra de progreso roja (errores) y barra verde (éxitos), panel derecho con árbol/tabla poblado — coincide con "proyecto Rodaje_Test, sesión activa, 12/8/0 archivos, proxy 1080p".
  - zonaB_estado-inicial / zonaB_configurado: diálogo con título, lista (selección corta vs. lista larga), dos botones secundarios + botón primario verde — diferencia coherente con SourcePickerDialog inicial vs configurado.
  - zonaC_estado-inicial / zonaC_configurado: asistente con chips de título, 3 campos etiquetados (uno con foco azul), 3 radios (selección distinta entre capturas), combo, checkbox y dos botones (secundario + primario verde) — coincide con ProjectWizard inicial vs llenado.
  - zonaD_estado-inicial / zonaD_configurado: barra post-ingesta con checkboxes/combo en estados distintos — coincide con el recorte post-ingesta marcado (formatear/apagar).
  Artefacto de rendering: los glifos aparecen como cuadros (.notdef) por falta de fuente del sistema en el entorno offscreen; el layout, controles, colores y estados sí reflejan fielmente la UI atribuida por la leyenda. El artefacto es esperado y no afecta la fidelidad estructural; está documentado en WINDOWS.md id 2.
why_human_reviewed: "Sí — el operador revisó las 8 capturas; las leyendas de 01-INVENTARIO.md (líneas 174-189) se confirman contra el rendering."

### 2. Confirmación de la disposición del hang preexistente (REVISA OPERADOR)
expected: |
  Confirmar la aceptación del cuelgue de tests/test_wifi_source.py:726 (el mock de WifiMethodDialog no intercepta el binding import-time de main_window.py:39; dialog.exec() bloquea en offscreen). El fix se difiere a v2; la fase 1 no toca código y la suite no se usa como gate (decisión del operador 2026-08-15, registrada en WINDOWS.md id 1 y plan §7).
result: pass
evidence: |
  La disposición REVISA OPERADOR queda resuelta por la ejecución v2 en la misma tanda de trabajo: en app/ui/main_window.py el binding de WifiMethodDialog se movió a import local dentro de `_pick_wifi_source()`, de modo que `mock.patch("app.ui.wifi_picker.WifiMethodDialog")` intercepta al call-site y `dialog.exec()` no bloquea en offscreen. La suite completa pasa: `python -m unittest discover -s tests` → "Ran 215 tests in 22.853s — OK (skipped=3)" (incluido test_pick_wifi_source_ftp_opens_ftp_picker que antes colgaba). Los warnings de ffprobe en el log son esperados (ffprobe devuelve código 1 sobre blobs de prueba), no son fallos. La ventana rota WINDOWS.md id 1 queda cerrada.
why_human_reviewed: "Sí — el operador confirmó la disposición y el fix quedó implementado en v2 (2026-08-15)."

## Summary

total: 2
passed: 2
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

Ninguno. La fase 01 queda cerrada.
