# PLAN — quick 260907-fb2: feedback WiFi/FTP, MTP-fantasma, sesiones «+»

## Objetivo

Arreglar los 4 problemas reportados por el usuario (sesión debug
`wifi-ftp-conexion-fantasma`; root causes confirmadas):

1. **WiFi (QR)**: IP anunciada inalcanzable desde el móvil (`err_address_unreachable`);
   el navegador del PC carga la web (el servidor vive; el fallo es la IP impresa).
2. **FTP**: el escaneo/descubrimiento no encuentra el móvil.
3. **Añadir origen**: un origen agregado por «examinar» aparece «Desconectado»
   y, al reabrir «Añadir origen», aparece un MTP fantasma que referencia `F:\`.
4. **Panel Sesiones**: el botón «+» no crea la sesión manual.

Evidencia (ya recogida):

- `app/ui/mixins/sessions_mixin.py:4` importa `QSettings` pero `_add_manual_session`
  (línea 300) usa `QDate` → `NameError`. Confirmado por introspección (`QDate`
  ausente del módulo; `QSettings` presente).
- `app/ui/mixins/devices_mixin.py:160-161` asigna `device_id = f"usb:{path}"`
  usando `utils.is_removable_drive()` **sin** el filtro de falso positivo
  (`_is_false_positive_drive`) que sí aplica `_windows_mounted_drives()`
  (`app/core/utils.py:53-75`).
- `sources_mixin._build_status_label` (líneas 122-139): `connected` solo se
  alimenta de `self._connectivity`, nunca para claves `usb:*` → siempre
  «Desconectado».
- `_disconnected_devices` (devices_mixin.py:59-116) devuelve `usb:*` como
  «desconectado» aunque la unidad esté montada; `AddSourceDialog` (add_source_dialog.py:236-243)
  los renderiza con `kind="device"`, etiqueta `[MTP] %1` → MTP fantasma.
- `app/core/ftp.py`: `local_ips()` (línea 105) incluye adaptadores virtuales
  (VMware/VPN/Hyper-V) y link-local 169.254; `local_ip()` (126) cae en
  `local_ips()[0]` (orden alfabético) cuando `_default_route_ip()` falla.

## Restricciones

- NO tocar `app/ui/main_window.py` ni `tests/test_main_window.py` (WIP externo).
- Cambios solo en `app/core/ftp.py`, `app/core/mtp.py`, mixins y
  `app/ui/add_source_dialog.py`; sin refactor de core.
- Strings nuevos vía `tr()`; español como idioma fuente.
- Commits atómicos por tarea (patrón `044b2b5`…`3a8acbd`).

## Tareas

### T1 — Sesiones «+»: import `QDate` (bug 4, confirmado)
- `app/ui/mixins/sessions_mixin.py:4`: `from PySide6.QtCore import QSettings, QDate`.
- Test: `tests/test_sessions_mixin.py` (harness ligero, patcheando `db.create_session`
  y `QInputDialog`), comprueba que `_add_manual_session` inserta y refresca.
- Commit: `fb2-T1 sesiones: import QDate (NameError en «Nueva Sesión manual»)`

### T2 — Origen «examinar»: «Desconectado» + MTP fantasma (bug 3, confirmado)
- `devices_mixin._assign_folder_source` (devices_mixin.py:160): en vez de
  `utils.is_removable_drive(path)` a secas, `usb:*` solo si `path` está en
  `utils.get_mounted_drives()` (esa función ya aplica `_is_false_positive_drive`).
- `sources_mixin._build_status_label` (122-139): para `device_id` con prefijo
  `usb:`, `connected =` la ruta está montada como extraíble (mismo criterio).
- `devices_mixin._disconnected_devices` (59-116): excluir `usb:*` cuya ruta
  esté montada (no son «desconectados»).
- `add_source_dialog.py:236-243`: render de claves `usb:*` como `[USB] ruta`
  con `type="USB"` (no `[MTP]`), también en `_sync_imported_devices` (765).
- Tests: asserts en `tests/test_add_source_dialog.py` (render usb) y cubrir
  `_build_status_label`/`_disconnected_devices` donde haya harness.
- Commit: `fb2-T2 origen usb: sin falso positivo y sin «[MTP]» fantasma`

### T3 — WiFi/FTP: IP anunciada inalcanzable + subred errónea (bugs 1a/1b)
`app/core/ftp.py`:
- `local_ips()`: excluir link-local `169.254.0.0/16`, `x.x.x.0`/`x.x.x.255`,
  multicast `224.0.0.0/4`; ordenar con preferencia RFC1918 (192.168/10/172.16-31)
  y mantener el fallback de `_default_route_ip()`.
- `local_ip()`: `_default_route_ip()` → primera RFC1918 de `local_ips()` →
  primera `local_ips()`.
- `_default_route_ip()`: fallback win32 con `GetAdaptersAddresses` (ctypes,
  guardado por `sys.platform`) que devuelve el IPv4 de la interfaz con gateway
  activo; `except` → `None` (sin romper el comportamiento actual).
- `local_subnet_ips()` se corrige solo (deriva de `local_ips()`).
- Tests en `tests/test_ftp.py`: añadir (a) excluye `169.254.x.x`, (b)
  `local_ip()` elige RFC1918 sobre otra IP local, (c) `_default_route_ip()`
  cae al helper win32 mockeado. Conservar los 5 existentes intactos.
- Commit: `fb2-T3 ips: excluir adaptadores virtuales/link-local en QR y escaneo`

### T4 — «Detectar» crash al cerrar/reabrir: cache de `list_devices` (bug 2, sospecha)
- `app/core/mtp.py`: `WpdBackend.list_devices()` con cache short-TTL (~2 s)
  thread-safe (`threading.Lock`), invalidable; reduce la churn COM de cada
  apertura del diálogo (`_pick_source_entry` sources_mixin.py:548 +
  `_disconnected_devices` devices_mixin.py:72) y del auto-sync.
- Verificar que no rompe `tests/test_mtp.py` (15) ni `test_device_registry.py` (16);
  añadir test de que dos llamadas cercanas no re-enumeran (spy).
- Commit: `fb2-T4 mtp: cache TTL en list_devices (menos churn COM)`

## Verificación

Ejecutar (por módulo, en verde en esta rama):

```
python -m unittest tests.test_ftp tests.test_shoot_inbox tests.test_mtp ^
  tests.test_sources_mixin tests.test_device_registry tests.test_db ^
  tests.test_add_source_dialog tests.test_sessions_mixin tests.test_wifi_source
```

- NO ejecutar `tests/test_main_window.py` (WIP externo sobre `main_window.py`).
- Smoke manual tras T2/T3: abrir «Añadir origen» dos veces (sin MTP fantasma),
  QR con la IP LAN real, botón «+» creando sesión.

## Riesgos / notas

- El helper win32 de `_default_route_ip()` parsea estructuras `GetAdaptersAddresses`
  con `ctypes`; si falla en algún equipo debe devolver `None` (comportamiento actual).
- Los tests de `test_ftp.TestLocalIp` mockean `socket.getaddrinfo` y
  `_default_route_ip`; el nuevo filtrado debe aplicarse SIEMPRE sobre las IPs
  recolectadas (compatible con mocks).