---
status: resolved
trigger: Bug 5: Al deseleccionar un origen, la sesión automática creada no desaparece.
created: 2026-08-20
updated: 2026-08-21
---

## Symptoms
- Expected behavior: Al deseleccionar un origen, la sesión automática creada para ese origen debe eliminarse o desactivarse.
- Actual behavior: La sesión permanece.
- Error messages: Ninguno reportado.
- Timeline: Reportado 2026-08-20.
- Reproduction: Seleccionar origen → se crea sesión automática → deseleccionar origen → sesión sigue existiendo.

## Evidence
- 2026-08-21T00:00:00 _on_source_widget_check_changed deshabilita sesiones con enabled=0 en lugar de eliminar sesiones auto-creadas
- 2026-08-21T00:01:00 Sessions auto creadas tienen nombre "Auto (<base>)"

## Root Cause
La lógica de deselección en MainWindow._on_source_widget_check_changed solo establecía enabled=0 para las sesiones con el origen. Las sesiones automáticas creadas al seleccionar (nombre "Auto (...)") permanecían en la DB y en la UI.

## Fix
Modificar _on_source_widget_check_changed para detectar sesiones con nombre que empieza por "Auto (" y eliminarlas con db.delete_session al deseleccionar el origen; en caso contrario mantener el comportamiento de desactivación. Repoblar _source_paths y refrescar la lista de orígenes tras el borrado.

## Current Focus
hypothesis: Resuelto
next_action: archivar sesión
