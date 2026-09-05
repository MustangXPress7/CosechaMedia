# Deferred Items — Plan 01.6.0-04

Hallazgos fuera de scope de este plan, registrados para fases futuras. No corregidos aquí
(regla de límite de scope: solo auto-fix issues causados directamente por los cambios del plan).

## 4. Flake pre-existente de timing en `tests/test_e2e.py` (suite completa)

- **Dónde:** `TestEndToEndIngest` — `test_ingest_to_dump_targets`, `test_redump_after_master_delete`,
  `test_redump_in_window_mode_when_older_than_window`.
- **Problema:** en suite completa fallan de forma rotativa (distinta prueba en cada ejecución) por
  "La segunda ingesta no terminó a tiempo" (timeout 30 s de `_wait_done`), con "database is locked"
  y "No space left on device" en los logs (disco C: con ~4,4 GB libres). Pasan aisladas y el módulo
  completo pasa solo (3/3). Observado durante la verificación del plan 01.6.0-05 (3 ejecuciones
  completas de `python -m pytest tests/`): pruebas distintas fallaron cada vez.
- **Acción futura sugerida:** subir el timeout de `_wait_done` bajo carga, aislar los watchers
  entre tests (tornar a apagarlos en tearDown), o ejecutar e2e en CI como job separado; liberar
  espacio en disco C: de la máquina de desarrollo.

## 1. Ghost-cleanup de `sd_cards` en borrado de proyecto (misma clase que el bug corregido)

- **Dónde:** `app/ui/main_window.py` — `delete_current_project` y `delete_all_projects` (bucle
  `DELETE FROM sd_cards WHERE serial = ?` por cada serial recogido de sesiones del proyecto).
- **Problema:** al borrar un proyecto, se eliminan filas de `sd_cards` cuyo serial no tenga otras
  sesiones... de OTROS proyectos también se revisa, pero el borrado es global: si un proyecto
  borrado contiene una tarjeta cuyo serial el usuario reutiliza en otro proyecto, el conocimiento
  guardado de esa tarjeta en `sd_cards` de OS/TARJETA se pierde. Es la misma clase de pérdida de
  datos globales que este plan corrigió para `device_settings` (B-20).
- **Traza:** el plan 01.6.0-04 solo pedía proteger `device_settings`. `sd_cards` quedó como está
  (comportamiento previo), no se tocó para no ampliar el scope.
- **Acción futura sugerida:** decidir la semántica de `sd_cards` (global vs por proyecto) y, si es
  global, no borrarla en borrado de proyecto; tests en `tests/test_main_window.py`.

## 2. Flake pre-existente por orden de suite: `tests/test_mtp.py`

- `TestThreadLocalManager::test_wpd_session_devicename_no_duplicate` falla en suite completa
  (`PNP1_<MagicMock...>` vs `PNP1_SERIAL9`) y pasa aislado (0.24 s). `app/core/mtp.py` no se tocó en
  este plan; fallo dependiente del orden de tests (estado thread-local del manager COM).
- **Acción futura sugerida:** revisar el aislamiento de `_ThreadLocalDeviceManager` (reset de estado
  global en setUp/tearDown) o marcar el test con `@pytest.mark.order`.

## 3. Ausencia de servidor FTP embebido (desviación de interpretación del plan)

- El plan 01.6.0-04 asumía «servidor FTP embebido»; el producto solo tiene cliente FTP
  (`FtpBackend`/`FtpSession`) y servidor HTTP WiFi (`ShootInboxServer`). El endurecimiento se aplicó a
  las superficies reales (ver SUMMARY). Si en el futuro se añade un servidor FTP, aplicarle los mismos
  patrones (settimeout + keepalive + límites).