---
slug: session-origen-dispositivo-mtp-fantasma
status: resolved
trigger: >-
  1. Al crear una sesión nueva y asignarle un origen, no parece pillar bien el
  dispositivo del que tiene que salir.
  2. Se siguen creando dispositivos MTP fantasma de las propias ubicaciones
  externas (E: y F:).
created: 2026-09-04
updated: 2026-09-04
---

## Symptoms

1. Al crear una sesión nueva y asignarle un origen (tarjeta/USB), no se captura bien el dispositivo del que tiene que salir.
2. Siguen apareciendo «dispositivos MTP fantasma» de las propias ubicaciones externas (en el sistema del usuario, E: y F:).

## Investigation

- Reproducido en el sistema real: `get_mounted_drives()` devuelve E:\ (removable, sin etiqueta) y F:\ (removable, etiqueta LUMIX). Ambos son tarjetas/lectores de tarjeta válidos.
- `WpdBackend().list_devices()` devolvía TAMBIÉN esas dos unidades con ids `\\?\swd#wpdbusenum#_??_usbstor#disk&ven_ts-rdf5&prod_sd__transcend...` (E:) y `...ven_mass&prod_storage_device...` (F:).
- Causa raíz bug 2: WPD enumera el almacenamiento masivo USB (lectores de tarjeta/disco externo) como si fueran dispositivos WPD/MTP. El filtro previo (`_is_false_positive_drive`) solo trataba los discos vistos como *unidades*, pero `list_devices()` los listaba además como *MTP*. Por eso aparecían dos veces: como unidades USB y como MTP fantasma.
- Causa raíz bug 1: al marcar/asignar una tarjeta como origen, la sesión podía quedar con un `device_id` `usbstor` obsoleto (del bug 2). Esos ids no son MTP reales y rompen la asociación por serial de volumen (sd_cards), de modo que la sesión «no pilla el dispositivo».

## Root Cause

- Bug 2: `WpdBackend.list_devices()` no filtra las unidades USB de almacenamiento masivo (`usbstor`); aparecen como MTP fantasma además de como unidades USB.
- Bug 1: sesiones con `device_id` `usbstor` obsoleto rompen la identificación por serial de la tarjeta (sd_cards).

## Fixes

1. `WpdBackend.list_devices()`: filtra ids que contengan `usbstor` (no son MTP reales; ya se muestran como unidades USB).
2. Nuevo `MainWindow._repair_folder_device_id(path)`: para orígenes de tarjeta removible, limpia cualquier `device_id` `usbstor` obsoleto en las sesiones asociadas y borra su mapeo cámara huérfano (`db.delete_device_settings_by_key`). Se invoca al asignar origen (lista / `_assign_folder_source` / `_assign_session_folder`).
3. Nuevo `DatabaseManager.delete_device_settings_by_key(device_key)`: borra un mapeo cámara huérfano.

## Verification

- Real (sistema del usuario): tras el fix, `WpdBackend().list_devices()` ya no devuelve E:/F: (una sola vez, como USB).
- Tests: `test_list_devices_filters_usbstor_mass_storage` (mtp), `test_repair_folder_device_id_clears_stale_usbstor` (source_content). Suite completa: 347 tests OK (5 skipped).

## Current Focus

- hypothesis: RESOLVED — filtro usbstor en list_devices + reparación de device_id obsoleto por serial
- next_action: confirmado con suite completa (347 OK)