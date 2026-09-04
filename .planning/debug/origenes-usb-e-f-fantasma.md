---
status: resolved
trigger: "Se crean dos orígenes USB por defecto llamados E y F sin siquiera ser detectados. Luego al cerrar y volver a abrir la ventana de orígenes se eliminan solos."
created: 2026-09-04
updated: 2026-09-04
slug: origenes-usb-e-f-fantasma
goal: find_and_fix
resolution:
  root_cause: "_refresh_physical_section() añade USB drives sin comprobar _explicit_mtp, causando asimetría con _populate()"
  fix: "Añadido `if self._explicit_mtp:` alrededor del bucle USB en _refresh_physical_section()"
  commit: 6c91c10
---

# Debug Session: origenes-usb-e-f-fantasma

## Symptoms

- Al hacer click en "Detectar" (del diálogo/ventana de orígenes) aparecen dos
  orígenes USB por defecto llamados "E" y "F", sin que se detecten como
  dispositivos reales.
- E: y F: son unidades reales conectadas, pero NO son extraíbles (drives fijos
  / no removibles).
- Esos orígenes E/F solo aparecen en la apertura actual de la ventana; al
  cerrar y volver a abrir la lista de orígenes se eliminan solos (no quedan
  persistidos ni en sesiones ni visualmente).

## Current Focus

- hypothesis: ASIMETRÍA entre `_populate()` y `_refresh_physical_section()` en `add_source_dialog.py`
- test: N/A (bug visual, no reproducible localmente)
- expecting: Fix de consistencia en la adición de USB drives
- next_action: apply fix

## NOTA CRÍTICA (aclara el usuario)

- Este bug se reproduce en OTRA MÁQUINA DE TESTING, NO en esta máquina de
  desarrollo. En la máquina de testing hay dos unidades reales E: y F: que NO
  son extraíbles (drives fijos / no removibles).
- Por tanto NO se puede reproducir directamente en este entorno: la
  investigación debe basarse en el CÓDIGO (ruta de "Detectar" y enumeración de
  unidades), no en la máquina local.
- En esta máquina también había E:/F: (lectores) en el bug 2 previo, pero el
  alcance de este bug es distinto.

## Contexto previo del proyecto

- Bug 2 previo (resuelto, commit a583d85): `WpdBackend.list_devices()` devolvía
  E: y F: como WPD/MTP con ids `usbstor` (almacenamiento masivo USB); se filtró
  la subcadena `usbstor` en esa ruta. Eso afectaba a la lista de dispositivos
  MTP del diálogo.
- Este bug es DISTINTO: aparición al pulsar "Detectar" y ruta de detección USB
  (no MTP). Parece enumerar unidades no extraíbles E:/F: y auto-crear orígenes.

## ROOT CAUSE

### Causa primaria: Asimetría `_populate()` vs `_refresh_physical_section()`

En `app/ui/add_source_dialog.py`:

- **`_populate()` (línea 194):** Los USB drives solo se añaden cuando
  `self._explicit_mtp` es `True`:
  ```python
  if self._explicit_mtp:
      for drive in utils.get_mounted_drives():
          ...
  ```

- **`_refresh_physical_section()` (líneas 511-522):** Los USB drives se añaden
  SIEMPRE, sin comprobar `_explicit_mtp`:
  ```python
  for drive in utils.get_mounted_drives():
      ...
      if utils.is_removable_drive(drive_path) and \
              self._row_for_source("usb", drive_path) is None:
          self._append_raw_source(...)
  ```

Cuando el diálogo se abre desde `main_window.py` (línea 3547), NO se pasa
`mtp_backend`:
```python
dialog = AddSourceDialog(self, folders=folders, senders=senders,
                          devices_missing=..., devices_connected=...,
                          on_delete=..., on_detect=..., on_qr=...)
```

Esto hace `mtp_backend=None` → `self._explicit_mtp = False`.

**Flujo del bug:**
1. Diálogo se abre → `_populate()` corre con `_explicit_mtp=False` → USB NO se añaden → E:/F: NO aparecen
2. Usuario pulsa "Detectar" → `_refresh_physical_section()` corre SIN guardia `_explicit_mtp` → USB SÍ se añaden → E:/F: APARECEN
3. Usuario cierra y reabre → `_populate()` otra vez con `_explicit_mtp=False` → USB NO se añaden → E:/F: "desaparecen"

### Causa secundaria: `_is_false_positive_drive()` incompleto

`_windows_mounted_drives()` solo acepta `GetDriveTypeW() == 2` (DRIVE_REMOVABLE).
En algunos SSDs/NVMe, Windows reporta DRIVE_REMOVABLE para discos fijos. La
función `_is_false_positive_drive()` filtra etiquetas de sistema y carpetas de
sistema, pero los discos de datos sin carpetas Windows pasan el filtro.

## Evidence

- Línea 82: `self._explicit_mtp = mtp_backend is not None`
- Línea 194: `_populate()` USB solo con `_explicit_mtp=True`
- Líneas 511-522: `_refresh_physical_section()` USB sin guardia `_explicit_mtp`
- Línea 3547: `AddSourceDialog` se llama SIN `mtp_backend`

## Eliminated

- No es bug MTP (bug 2 previo, ya resuelto)
- No es persistencia de sesiones (DB OK)
- No es el auto-detect del main window (ruta distinta)

## Resolution

- **Root cause:** `_refresh_physical_section()` añade USB drives sin comprobar `_explicit_mtp`, causando asimetría con `_populate()`
- **Fix:** Añadir `if self._explicit_mtp:` alrededor del bucle USB en `_refresh_physical_section()`
- **Archivos a modificar:** `app/ui/add_source_dialog.py` (líneas 511-522)
