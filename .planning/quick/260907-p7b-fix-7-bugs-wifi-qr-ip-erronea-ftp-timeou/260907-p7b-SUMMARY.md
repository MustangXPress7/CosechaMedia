---
quick_id: 260907-p7b
slug: fix-7-bugs-wifi-qr-ip-erronea-ftp-timeou
title: Fix 7 bugs — WiFi QR/IP errónea, FTP timed out, crash «Detectar», prompts UI Añadir origen
---

# Quick Task 260907-p7b: Fix 7 bugs (WiFi/FTP/Detectar/UI Añadir origen)

Fase 1.5.0 (consolidación de bugs, fase ligera por quicks). Modo sequential;
constraint duro: sin tocar `app/ui/main_window.py` (WIP ajeno). Test gate: no
se ejecutó `tests/test_main_window.py` (rojo transitorio por el WIP ajeno).

## Problems & Fixes

| # | Bug | Fix |
|---|-----|-----|
| T1 | QR WiFi anunciaba `127.0.0.1` (móvil → `err_address_unreachable`) porque `local_ip()` dependía de conectar a `8.8.8.8` | `ftp.py`: `_default_route_ip()`, `local_ips()` (IPv4 no-loopback determinista) y `local_ip()` = ruta por defecto → primera IP local → `None`. `shoot_inbox` mantiene `127.0.0.1` solo como último recurso |
| T2 | FTP sin contexto: «timed out», sin host:puerto; escaneo multi-subred roto sin Internet | `_open_session` envuelve el fallo con `host:port` + nota (ver servidor FTP activo/red); `local_subnet_ips()` escanea las subredes /24 de todas las IPs de `local_ips()` |
| T3 | Pulsar «Detectar» → acceso COM crash (access violation, no capturable) al reutilizar `PortableDeviceManager` de apartamento cerrado | limpieza de `_manager_local.device_manager`/`_com_owner.initialized` en `list_devices` (inicio/finally), `_WpdSession.__init__` (tras `CoInitialize`) y `close()` (antes de `CoUninitialize`); `_manager()` no reutiliza caché sin COM activo |
| T4 | «Añadir origen» sin proyecto: silencio | `sources_mixin._pick_source_entry` muestra `QMessageBox.information` («Proyecto requerido») antes de `return None` |
| T5 | Carpetas locales persistidas en `known_devices` (`device_type="folder"`) | `db.delete_known_devices_by_type()`; `_browse_folder` ya no hace upsert; `AddSourceDialog.__init__` purga folders existentes (USB `usb:<ruta>` y MTP se conservan) |
| T6 | Selector de cámara: auto no tenía «— Vacío —», manual sin selección por defecto | ítem «— Vacío —» (data `"VACIO"`) en AMBOS modos (`_vacio_trigger_index = len(known)`; auto: detect tras él, `_detect_trigger_index = len(known)+1`); si `src["camera"]` vacío → `setCurrentIndex(vacio)` + `setEditText("")` |
| T7 | Filas WiFi/FTP mostraban desplegable de cámaras USB/MTP (nombre editable, con escáner) | `QLineEdit` read-only con `src["camera"] or src["label"]` en `_append_raw_source` (kind `sender`/`ftp_profile`) y en `_add_source_row` (type `WiFi`/`FTP`); `_camera_text` ya soportaba `QLineEdit` |

## Key Decisions / Deviations

- **T2 (deviation del PLAN):** se descartó el reintento de conexión con `passive`
  invertido — `passive`/`active` solo afecta al canal de datos; el flip ya se
  gestiona en `list_children`/stage. Se cumplió la intención con un error
  legible con `host:port` y con el escaneo multi-subred (esto último estaba en
  T2 del plan; `local_ip` multi-NIC se adelantó a T1).
- El bug 7 se detectó en `_add_source_row` (render real de sender/ftp en
  `_build_ui`), no solo en `_append_raw_source`; ambos caminos quedan cubiertos.
- Test `test_edit_camera_fires_callback_for_ftp` (premisa: cámara FTP editable +
  callback `ftp:<id>`) quedó obsoleto por diseño del bug 7 y se sustituyó por
  dos tests del nuevo comportamiento (read-only fijo).

## Hallazgo fuera de alcance (documentado, no reparado)

En `tests/test_add_source_dialog.py`, la clase auxiliar `class _Device` (línea
529) se cierra al nivel de indentación columna-0, por lo que los ~20 métodos
E2E posteriores (líneas 539-703, p.ej. `test_full_acceptance_flow_multiple_sources`,
`test_ftp_profile_selection`) quedan **absorbidos como métodos de `_Device`** y
unittest **nunca los descubre**. Es un bug latente preexistente de discovery
(no regresión de este quick). Rehabilitarlos requiere reconciliarlos con el
nuevo comportamiento T6/T7 (usan `_set_camera` sobre sender/ftp); se recomienda
quick futuro.

## Verification

Suites válidas (gate del plan), ejecutadas por módulo (`python -m unittest`,
proceso separado por módulo por crash nativo comtypes):

- `tests.test_ftp` → 30 OK
- `tests.test_shoot_inbox` → 34 OK
- `tests.test_mtp` → 15 OK (incluye `test_wpd_session_devicename_no_duplicate`,
  verde tras el fix T3; antes fallaba de forma order-dependent)
- `tests.test_sources_mixin` (nuevo) → 3 OK
- `tests.test_device_registry` → 16 OK
- `tests.test_db` → 23 OK
- `tests.test_add_source_dialog` → 47 OK
- `tests.test_wifi_source` → 56 OK

`tests/test_main_window.py` NO ejecutado (WIP ajeno, rojo transitorio).

## Commits

- `10fc7e3` — T1 `fix(core): local_ip() sin dependencia de Internet y no anunciar loopback en la URL del WiFi`
- `dd07468` — T2 `fix(core): error FTP con contexto host:puerto (antes solo 'timed out') y escaneo multi-subred`
- `84b0ebc` — T3 `fix(core): no reutilizar PortableDeviceManager de apartamentos COM cerrados (crash al pulsar Detectar) y tests`
- `ac48027` — T4 `fix(ui): avisar cuando se pulsa Añadir origen sin proyecto seleccionado`
- `c672e9b` — T5 `fix(core): no persistir carpetas locales como dispositivos conocidos (tipo folder) y purgar las existentes`
- `7eb5405` — T6 `fix(ui): opción 'Vacío' predeterminada en el selector de cámara para modos manual y automático`
- `3a8acbd` — T7 `fix(ui): nombre fijo (sin desplegable) en filas WiFi y FTP de Añadir origen`
- Docs: PLAN.md + SUMMARY.md + STATE.md

## Follow-ups

- Reiniciar ejecución de `local_ips()`/multi-subred en la UI (escanear todas las
  NICs añade latencia al arranque del `ShootInboxPanel`).
- lupdate (`tools/update_translations.ps1`) para los strings nuevos de T2/T4
  («No se pudo conectar al servidor FTP…», «Proyecto requerido», mensaje del
  aviso).
- Quick futuro: rehabilitar los tests E2E tragados por `class _Device`.