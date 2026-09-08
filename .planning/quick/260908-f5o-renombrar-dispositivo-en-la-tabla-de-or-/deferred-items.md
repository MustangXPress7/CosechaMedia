# Deferred Items — quick 260908-f5o

Out-of-scope discoveries logged during execution (scope boundary rule).

| Date | Item | Status | Notes |
|------|------|--------|-------|
| 2026-09-08 | `tests/test_main_window.py::TestRenameDialogPersistence::test_rename_in_dialog_ftp_prefix` falla (`'QLineEdit' object has no attribute 'setEditText'`) | pre-existing | Causado por los cambios sin commitear previos en `app/ui/add_source_dialog.py` (38+/24- al iniciar la tarea); no relacionado con este quick task. Verificar tras el commit de los cambios pendientes de add_source_dialog. |