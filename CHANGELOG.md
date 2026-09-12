# Changelog — CosechaMedia v1.6.1

**Fecha:** 2026-09-12  
**Tipo:** Patch release (fix sonido + alertas WiFi)

---

## Resumen

Corrección del silenciado del control de volumen (todo sonido quedaba mudo desde v1.6.0) y nueva alerta al recibir archivos por WiFi: mismo sonido que la ingesta completada + aviso en la bandeja del sistema.

---

## Cambios

- **Fix volumen**: `QSoundEffect` ahora se crea una vez en el hilo principal y se reutiliza; el slider de volumen vuelve a funcionar. Antes el efecto se creaba dentro de un thread sin event loop de Qt y el objeto se recolectaba al instante, silenciando todas las alertas (con `winsound`/`afplay`/`aplay` de respaldo que nunca llegaban a ejecutarse).
- **Feat WiFi**: al llegar un archivo por WiFi suena la alerta de "ingesta completada" (respectando `soundsEnabled` y el volumen) y salta un globo en la bandeja del sistema con remitente, nombre y tamaño, visible aunque la ventana esté detrás de otras apps — incluso sin proyecto seleccionado.
- **Bandeja**: icono en el tray del sistema (si está disponible); un clic devuelve la ventana al frente.
- **i18n**: nuevas cadenas ES→EN "Archivo recibido por WiFi" y "Recibido de %1: %2 (%3).".

---

## Archivos modificados (resumen)

- `app/core/notifications.py` — `play_sound_file` con efecto persistente en hilo principal, `notify_wifi_file_received`
- `app/ui/main_window.py` — `_create_tray` / `_on_tray_activated`
- `app/ui/mixins/wifi_mixin.py` — `_notify_wifi_file_received` / `_format_size`
- `app/i18n/cosechamedia_en.ts` / `.qm` — cadenas nuevas
- `tools/translate_en.py` — traducción nueva

---

## Verificación

```
$ QT_QPA_PLATFORM=offscreen python -m unittest tests.test_main_window tests.test_wifi_source
Ran 114 tests — OK
```

---

# Changelog — CosechaMedia v1.6.0

**Fecha:** 2026-09-10  
**Tipo:** Feature release (UI overhaul + device registry + footage reorganiser)

---

## Resumen

Reestructuración integral de la interfaz: diálogo unificado de orígenes, registro global de dispositivos con nombres persistentes, reorganizador de footage, opciones de sonido, filtro de ventana por días/semanas/meses, y descomposición de MainWindow en mixins.

---

## Nuevas funcionalidades

| Función | Descripción |
|---------|-------------|
| **AddSourceDialog** | Sustituye a SourcePickerDialog. Tabla plana sin pestañas con 3 secciones (USB/MTP, WiFi/QR, FTP) y 5 columnas. Detección off-thread, precarga de nombres conocidos, errores WPD no-bloqueantes. |
| **DeviceRegistry** | Tabla `known_devices` en SQLite. Nombres de cámara persistentes entre proyectos con popup de confirmación y checkbox "No volver a preguntar". Importación/exportación JSON. |
| **ReorganizeDialog** | Escaneo de carpetas de proyecto para detectar archivos *SinClasificar*, re-verificación MD5 y re-registro en DB. Accesible desde el menú Herramientas. |
| **SoundSettingsDialog** | Activar/desactivar alertas de ingesta y slider de volumen. Menú Configuración → Opciones de sonido… |
| **Filtro ventana sesión** | Selector de unidad (días/semanas/meses) en el filtro "Últimos N…" de la configuración de sesión. |
| **NamesManagerDialog** | Diálogo reutilizable para gestionar nombres de carpetas de footage / contenedores (añadir, renombrar, eliminar, duplicar). |

---

## Mejoras

- **COM threading**: `CoInitialize`/`CoUninitialize` balanceados en hilo de staging; espera de hilo al resetear proyecto.
- **FTP multi-subred**: escaneo en todas las subredes locales, auto-detección passive→active flip, panel de estado y configuración.
- **WiFi local_ip()**: detección de IP local sin dependencia de Internet; no anuncia loopback en la URL del QR.
- **Identidad USB unificada**: normalización `usb:<LETRA>:/ usb:<LETRA>:\ → usb:<LETRA>:\\` y eliminación de claves fantasma.
- **SinClasificar**: sustituye a `Unknown_Camera` como nombre por defecto para archivos sin metadatos de cámara.
- **Botón FTP**: renombrado y reconfigurado para abrir panel de estado/configuración.
- **Tabla de orígenes**: etiqueta FTP visible, ocultación de caché WiFi/FTP al añadir origen.
- **Pre-fill de cámara**: filas USB en Añadir origen muestran el nombre conocido del dispositivo.
- **Reorganización menú**: renombrar menús Herramientas, reestructuración de la barra de menú.
- **Icono modo delicado**: bandaid.svg convertido al formato estándar stroke #FF00FF.
- **Botones de sesión**: reordenados a `+ - lápiz`.
- **Stretch superior**: 5:1 para bajar controles inferiores en la columna izquierda.
- **Actualizador**: comparación correcta de sufijos pre-release (beta1 < beta2).

---

## Bugs corregidos

| Bug | Fix |
|-----|-----|
| Sesiones fantasma USB al pulsar Detectar | Filtrado de usbstor fantasma + reparación device_id de tarjetas |
| Borrado de origen con device_id deseleccionaba mal | Deseleccionar deshabilita origen y limpia fantasma USB |
| FTP etiqueta y picker incorrectos | Botón FTP abre panel de estado/config, sesiones FTP registran como FTP |
| Cache WiFi/FTP visible en Añadir origen | Ocultada correctamente |
| Crash al pulsar Detectar con COM cerrado | No reutilizar PortableDeviceManager de apartamentos COM cerrados |
| Error FTP solo mostraba "timed out" | Contexto host:puerto en mensaje de error |
| `local_ip()` dependía de Internet | Funciona sin conexión, no anuncia loopback |
| Carpetas locales persistidas como dispositivos | No persistir carpetas tipo `folder` y purgar las existentes |
| Añadir origen sin proyecto seleccionado | Aviso al usuario |
| Nombre fijo (sin desplegable) en filas WiFi/FTP | Corregido en Añadir origen |
| Opción "Vacío" predeterminada en selector de cámara | Corregido para modos manual y automático |
| `on_file_finished` crashea con `camera_model` 'Unknown' | Corregido con metadatos verificados |
| `_browse_session_src` rompe al desempaquetar orígenes | Corregido |
| Ghost USB E/F solo aparecen en Detectar | Filtrado de dispositivos fantasma |
| Actualizador cuelga en Windows (desde v1.5.1) | Script helper con timeout + taskkill, `prepare_for_update()` antes de spawn |
| Sesión restante no se refresca al borrar otra | Refresco correcto |
| Re-volcar si destino borrado de carpeta maestra | Disco como fuente de verdad |
| DB path dependiente de CWD | Independiente del directorio de trabajo |
| Actualizador: comparación pre-release incorrecta | Sufijos beta comparados correctamente |

---

## Descomposición de MainWindow

MainWindow se ha descompuesto en 8 mixins para mejorar la mantenibilidad:

| Mixin | Responsabilidad |
|-------|----------------|
| `MenuMixin` | Menú y cambio de idioma |
| `DevicesMixin` | Registro de dispositivos y staging MTP/FTP |
| `SourcesMixin` | Tabla de fuentes y menús |
| `SessionsMixin` | Gestión de sesiones |
| `CameraMixin` | Detección/nombrado de cámara y lectura SD |
| `IngestMixin` | Pipeline de ingesta y acciones post-ingesta |
| `ProjectMixin` | Ciclo de proyecto |
| `Workers` | Helpers de hilos de trabajo |

---

## Archivos modificados (resumen)

### Core (`app/core/`)
- `db.py` — tabla `known_devices`, migración legacy, `upsert_known_device`, `get_known_devices`, `get_known_device`
- `mtp.py` — CoInit/CoUninit balanceado, retry en `0x80070081`, `list_devices` con caché 2s
- `ftp.py` — multi-subred, passive→active flip, timeouts y keepalive
- `ingestor.py` — `should_skip`, `copy_verified` stream-through
- `metadata_engine.py` — retry degradado, `metadata_verified`, `SinClasificar`
- `notifications.py` — QSoundEffect con volumen configurable
- `utils.py` — `local_ip()` sin Internet, detección USB montado

### UI (`app/ui/`)
- `add_source_dialog.py` — **nuevo** — AddSourceDialog (sustituye SourcePickerDialog)
- `reorganize_dialog.py` — **nuevo** — ReorganizeDialog
- `sound_settings_dialog.py` — **nuevo** — SoundSettingsDialog
- `names_manager_dialog.py` — **nuevo** — NamesManagerDialog
- `mixins/` — **nuevo** — 8 mixins (camera, devices, ingest, menu, project, sessions, sources, wifi, workers)
- `main_window.py` — reestructurado, delega a mixins
- `selective_dump.py` — botones de sesión reordenados
- `wifi_panel.py` — QR con IP local sin Internet
- `ftp_status.py` — panel de estado/ config FTP

### Tests
- `tests/test_add_source_dialog.py` — **nuevo** (8 tests E2E)
- `tests/test_ingestor.py` — tests de `should_skip` y hash stream-through
- `tests/test_db.py` — tests `known_devices`, `watcher_seen`, CWD-independence
- `tests/test_metadata_engine.py` — tests retry y `SinClasificar`
- `tests/test_mtp.py` — tests CoInit balanceado

---

## Verificación

```
$ QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -p "test_*.py"
Ran 313+ tests — OK
```

> **Nota Windows**: El intérprete puede salir con código `0xC0000409` tras imprimir `OK` (teardown PySide6/Qt conocido). La suite en sí pasa en verde.

---

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