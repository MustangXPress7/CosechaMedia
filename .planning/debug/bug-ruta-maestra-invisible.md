---
status: resolved
trigger: Bug 4: Ruta maestra no visible en barra superior de la app — B-17. project_path_label con QSizePolicy.Ignored.
created: 2026-08-20
updated: 2026-08-20
---

## Symptoms
- Expected behavior: La ruta maestra del proyecto debe ser visible en la barra superior de la app.
- Actual behavior: La ruta no es visible.
- Error messages: Ninguno.
- Timeline: Reportado 2026-08-20, B-17 pendiente.
- Reproduction: Abrir app → barra superior → project_path_label no visible.

## Current Focus
hypothesis: project_path_label tiene QSizePolicy.Ignored, lo que hace que el layout lo colapse.
next_action: fixed

## Resolution
root_cause: QSizePolicy.Ignored horizontal en project_path_label hace que QHBoxLayout lo colapse a 0 px con stretch posterior.
fix: Cambiado SizePolicy a QSizePolicy.Preferred en app/ui/main_window.py:350-351
files_changed: app/ui/main_window.py
verification: label visible en barra superior con ancho máximo 420
