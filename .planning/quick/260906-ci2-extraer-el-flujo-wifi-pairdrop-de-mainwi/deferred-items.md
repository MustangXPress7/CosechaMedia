# Deferred Items — Quick 260906-ci2

Descubrimientos fuera de scope de este quick task (refactor WiFi). No se arreglan aquí.

1. **`test_mtp.TestThreadLocalManager.test_wpd_session_devicename_no_duplicate` falla solo en full-suite.**
   - Reproducido idéntico en worktree limpio en HEAD (271c357): `Ran 399 tests ... FAILED (failures=1, skipped=5)`.
   - En aislamiento (`python -m unittest discover -s tests -p test_mtp.py`) pasa (13 OK) en ambos árboles.
   - Causa probable: interacción/estado compartido entre tests en la misma corrida (no relacionado con el refactor).
   - Acción futura: investigar orden/aislamiento de la suite (posible contaminación de `_DEVICE_MANAGER` o mock global de comtypes).

2. **Crash del intérprete al salir tras carreras de test_wifi_source / full-suite (exit code `0xC0000409`, acceso violación).**
   - Presente también en HEAD limpio (baseline): los tests reportan "OK" y luego el proceso muere en teardown de Qt/offscreen.
   - Acción futura: revisar teardown de `QApplication` en los tests Qt bajo `QT_QPA_PLATFORM=offscreen` en Windows.