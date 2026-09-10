# Changelog — CosechaMedia v1.5.9-beta4

**Fecha:** 2026-09-10  
**Tipo:** Feature/UI + i18n

---

## Resumen
Control de volumen de alertas de ingesta, diálogo de opciones de sonido accesible desde el menú, y ajustes de UI/traducciones.

## Cambios
- NotificationManager ahora usa QSoundEffect con volumen configurable desde QSettings
- Nuevo diálogo SoundSettingsDialog: activar/desactivar sonidos y slider de volumen
- Menú Configuración → Opciones de sonido… abre el diálogo y recarga el gestor
- Traducciones EN actualizadas: Opciones de sonido, Alertas de ingesta, etc.
- Reordenar botones de sesión a `+ - lápiz`
- Icono modo delicado bandaid.svg convertido al formato estándar stroke #FF00FF

---

# Changelog — CosechaMedia v1.5.1

**Fecha:** 2026-08-30  
**Tipo:** Bug fix (updater hang on Windows)

---

## Resumen

Versión 1.5.1 corrige el problema crítico del actualizador: la aplicación se quedaba colgada al intentar actualizar desde versiones legacy, dejando dos ejecutables en disco y requiriendo reinicio manual.

---

## Bugs resueltos

| Bug | Descripción | Fix |
|-----|-------------|-----|
| **Updater-Hang** | Al actualizar, la app se detenía sin respuesta; al forzar cierre, quedaban 2 ejecutables y el antiguo debía borrarse manualmente | Script helper con timeout 30s + taskkill, `prepare_for_update()` antes de spawn, delay de 500ms antes de quit |

---

## Detalles técnicos

### App/core/updater.py
- Script helper Windows ahora incluye límite máximo de espera (MAX_WAIT=15 iteraciones ≈ 30s)
- Después del timeout, usa `taskkill /F` para forzar la terminación del proceso huérfano
- Logging agregado a `update_log.txt` para diagnóstico

### App/ui/about_dialog.py
- Llamada explícita a `parent.prepare_for_update()` antes de `install_update()` para detener workers/ingestors/watchers
- Delay de 500ms via `QTimer.singleShot` antes de `QCoreApplication.quit()` para permitir que el helper se inicie y el event loop procese

---

# Changelog — CosechaMedia v1.5.0

**Fecha:** 2026-08-29  
**Tipo:** Release estable (bugs de flujo de volcado + fricciones conocidas)

---

## Resumen

Versión 1.5.0 consolida la corrección de los 5 bugs activos del flujo de volcado documentados en `CONCERNS.md` (F-01 a F-05) y resuelve las fricciones de uso críticas: timeout de ffprobe, re-ingesta del watcher, DB path dependiente de CWD, doble hash MD5, y polling de dispositivos en UI thread.

La fase se ejecutó en **3 waves** con 4 planes, todos verificados con suite completa (126 tests core OK).

---

## Bugs resueltos (CONCERNS.md)

| Bug | Descripción | Plan | Fix |
|-----|-------------|------|-----|
| **F-01** | Sesión restante no se refresca tras borrar otra | Quick tasks previos | `c746b83` — refrescar sesión restante |
| **F-02** | Re-volcar si destino borrado de carpeta maestra | Quick tasks previos | `61d8754` — disco como fuente de verdad |
| **F-03** | Disco como única verdad para re-volcar; resume JSON fuera de raíz | Quick tasks previos | `903fab5` |
| **F-04** | Re-volcar dentro de ventana "últimos x días" aunque destino borrado | Quick tasks previos | `86d0b3b` |
| **F-05** | Re-volcar si destino borrado aunque fuera de ventana | Quick tasks previos | `86d0b3b` |

---

## Mejoras de arquitectura (Fase 1.5.0)

### Plan 01 — Metadata fiable (D-01/D-02, R1)
- **Retry degradado ffprobe**: ante timeout (10s) → reintento 1 vez con probe format-only (`-show_format` sin `-show_streams`) y timeout ampliado (30s) · `bc8c6c3`
- **Flag `metadata_verified`**: dict de metadata siempre incluye `metadata_verified: true/false` + `metadata_error` en fallo; `file_size` real vía `os.path.getsize` · `bc8c6c3`
- **`detect_camera_batch` no cuenta fallos**: ignora `metadata_verified=False` y `Unknown/Unknown_Camera` · `bc8c6c3`
- **Marker UI "Metadatos no verificados"**: visible en celda de cámara (col. 1) + tooltip; **nunca** en columna de estado (col. 2) → `_clear_completed_rows` intacto · `d3bbab4`

### Plan 02 — Hash MD5 único stream-through (D-03, R4)
- **`copy_verified` single-pass**: calcula MD5 del origen en streaming, sin relectura del destino · `fff1ac4`
- **Semántica de borrado preservada**: destino corrupto/parcial → `os.remove` + `None` · `fff1ac4`
- **`calculate_md5` conservado** para `_handle_reference_file` y tests · `fff1ac4`

### Plan 03 — Inventario watcher persistente (D-04, R2)
- **Tabla `watcher_seen`** (SQLite aditiva): `source_path`, `file_path`, `first_seen`, `last_verdict` (`copied`/`filtered`/`errored`), `filter_key` · `fc37e23`
- **Predicado compartido `Ingestor.should_skip`**: usado por `handle_new_file` y watcher; preserva F-02 (destino borrado ⇒ re-volcar) · `ca658f0`
- **Veredicto `filtered` con `filter_key`**: solo salta si firma del content-filter coincide; ventana cambiada ⇒ re-evaluar · `ca658f0`
- **Poda por antigüedad (30 días)**: elimina cap duro de 10k entradas · `ca658f0`
- **Normalización de rutas**: `os.path.normpath` en grabar/consultar · `fc37e23`

### Plan 04 — Regresiones R3/R5 + Gate suite completa
- **R3**: Test regresión `_resolve_db_path()` independiente del CWD en dev · `28bd6ed`
- **R5**: Test `TestAutoSyncOffThread` — `_auto_sync_check` despacha `list_devices`/`is_reachable` off-thread vía `_run_background` con guards · `43dc188`
- **Suite completa**: 126 tests core pasan en verde · `98e8b1c`

---

## Exploración para 1.6.0 (capturada en planning)

- **REQ-09**: Registro unificado `known_devices` (SQLite) — aprende de ingestas MTP+SD, sugiere en "Añadir origen"
- **REQ-10**: Instrumentación detección cámara (`metadata_engine`) — log estructurado ffprobe raw
- **UI**: Tarjeta "Dispositivo conocido: Sony A7IV (tarjeta #3)" + botón "Usar esta configuración"
- **Seed**: Integración MTP+SD en mismo registro físico

---

## Archivos modificados (resumen)

### Core (`app/core/`)
- `metadata_engine.py` — retry degradado, `metadata_verified`, `detect_camera_batch` filtrado
- `ingestor.py` — `copy_verified` stream-through, `should_skip`, `_content_filter_signature`, registro veredictos
- `watcher.py` — elimina cap 10k, usa `should_skip`, inventario DB persistente
- `db.py` — tabla `watcher_seen` + `load_seen`/`save_seen`/`prune_seen`

### UI (`app/ui/`)
- `main_window.py` — marker "Metadatos no verificados" en celda cámara + tooltip

### Tests
- `tests/test_metadata_engine.py` — 4 tests regresión D-01/D-02
- `tests/test_main_window.py` — 2 tests marker D-02 + 3 tests `TestAutoSyncOffThread`
- `tests/test_ingestor.py` — test `test_should_skip_resolves_verdict` + test hash stream-through
- `tests/test_watcher_inventory.py` — **nuevo** (6 tests D-04)
- `tests/test_db.py` — 4 tests `watcher_seen` + test CWD-independence

---

## Verificación

```
$ QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -p "test_*.py"
Ran 313 tests in 39.560s
OK (skipped=2)
```

> **Nota Windows**: El intérprete puede salir con código `0xC0000409` tras imprimir `OK` (teardown PySide6/Qt conocido). La suite en sí pasa en verde.

---

## Próximos pasos (Fase 1.6.0)

- REQ-06: Reorganizador de footage (volcados a mano → `Footage/<Cámara>/<Fecha>`)
- REQ-09/10: Registro unificado dispositivos + instrumentación detección
- Verificación avanzada XXH64 + manifiestos ASC MHL encadenados
- ID-01/ID-02: Volcado selectivo multi-origen + escaneo MTP vía caché (migrados desde 1.5.0)