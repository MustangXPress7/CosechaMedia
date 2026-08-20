---
status: resolved
trigger: Bug 2: Wizard proyecto nuevo muestra opción modo delicado, irrelevante por proyecto, solo por dispositivo.
created: 2026-08-20
updated: 2026-08-20
---

## Symptoms
- Expected behavior: El modo delicado es una propiedad del dispositivo/origen, no del proyecto. El wizard de creación de proyecto no debería mostrar opción de modo delicado.
- Actual behavior: El wizard muestra la opción modo delicado al crear proyecto nuevo.
- Error messages: Ninguno, UI confusa.
- Timeline: Reportado 2026-08-20.
- Reproduction: Abrir wizard de nuevo proyecto → ver opción modo delicado.

## Current Focus
hypothesis: El wizard reutiliza UI de configuración de origen o el flag `delicate_mode` quedó en sesiones/proyectos.
next_action: gather initial evidence

## Resolution
root_cause: ProjectWizard UI includes chk_delicate_mode checkbox and persists delicate_mode to projects table, although delicate_mode is a device-level property managed via device_settings. The wizard also loaded project_delicate_mode as fallback for ingestors.
fix: Removed chk_delicate_mode UI element from ProjectWizard, removed delicate_mode from project creation UPDATE, updated test, and changed ingest fallback to default False when device setting is absent instead of using project_delicate_mode.
verification: UI no longer shows modo delicado in new project wizard; project creation does not store delicate_mode; tests pass.
files_changed: app/ui/project_wizard.py, tests/test_main_window.py, app/ui/main_window.py
