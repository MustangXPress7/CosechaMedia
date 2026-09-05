---
status: in_progress
trigger: "Se crean dos orígenes USB por defecto llamados E y F sin siquiera ser detectados. Luego al cerrar y volver a abrir la ventana de orígenes se eliminan solos."
created: 2026-09-04
updated: 2026-09-04
slug: origenes-usb-e-f-fantasma
goal: find_and_fix
active: true
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

- **Root cause (v1):** `_refresh_physical_section()` añade USB drives sin comprobar `_explicit_mtp`, causando asimetría con `_populate()`
- **Fix (v1):** Añadir `if self._explicit_mtp:` alrededor del bucle USB en `_refresh_physical_section()` (commit `6c91c10`)
- **Archivos a modificar:** `app/ui/add_source_dialog.py` (líneas 511-522)

## REFINED DIAGNOSIS (revisión del usuario — 6c91c10 era un FALSO fix)

El fix anterior (`6c91c10`) ocultó el síntoma en lugar de resolverlo: al volcar
el bucle USB de `_refresh_physical_section()` tras `_explicit_mtp` (que en
producción es `False`), **"Detectar" dejó de detectar CUALQUIER unidad USB**,
incluida la real H: (pendrive/tarjeta que SÍ debe aparecer). El motivo por el
que E:/F: "desaparecieron" no es que se dejara de detectarlos correctamente,
sino que se deshabilitó toda la detección USB en ese flujo.

### Por qué `_explicit_mtp` es el wrong-guard

- En `main_window.py:3547` `AddSourceDialog` se crea SIN `mtp_backend` →
  `_explicit_mtp = False` en producción.
- `_explicit_mtp` solo debía aislar el CASO DE CONSTRUCCIÓN (`_populate`) para
  que los tests no enumeren la máquina real. El botón "Detectar" (`_refresh_physical_section`)
  es una acción on-demand del usuario y DEBE escanear USB siempre.
- Conclusión: **quitar el gate `_explicit_mtp` de `_refresh_physical_section()`
  (manteniéndolo solo en `_populate`)** para que H: vuelva a detectarse.

### Causa real del falso positivo E:/F: (ya mitigada)

`get_mounted_drives()`/`is_removable_drive()` (Windows) usaban solo
`GetDriveTypeW() == 2` (DRIVE_REMOVABLE). Ciertos discos USB fijos
(SSD/NVMe en carcasa, particiones extra de pendrive multi-particionado, lectores
sin medio) reportan tipo 2 sin ser realmente medios removibles → E:/F: colaban.

**Hardening aplicado (utils.py):** `is_removable_drive()` ahora exige además el
flag `FILE_REMOVABLE_MEDIA` de `GetVolumeInformationW`; `_windows_mounted_drives()`
reusa `is_removable_drive()` (antes solo `GetDriveTypeW==2`). Pendrives/tarjetas
reales (H:) sí marcan el flag; discos fijos (E:/F:) no.

- Test añadido: `tests/test_ingestor.py::TestUtils::test_is_removable_drive_windows_removable_media_flag`
- Suite completa: `python -m pytest tests -q` → 345 passed, 5 skipped.

### Pendiente (decisión abierta, usuario pidió investigar más antes de aplicar)

- Quitar `if self._explicit_mtp:` de `_refresh_physical_section()` (add_source_dialog.py:511)
  para que "Detectar" siempre escanee USB.
- Mantener el gate solo en `_populate()` (constructor, aislamiento de tests).
- Añadir test que verifique que "Detectar" con `_explicit_mtp=False` sí añade un
  USB real (H:).

## RESUELTO (gate quitado + tests)

- **Gate quitado** en `_refresh_physical_section()` (add_source_dialog.py:511):
  el bucle USB ahora corre siempre, no solo con `_explicit_mtp`. Se mantiene el
  gate en `_populate()` (constructor) para el aislamiento de tests.
- **Tests añadidos** (`tests/test_add_source_dialog.py`):
  - `test_detect_adds_usb_even_without_explicit_backend`: con `_explicit_mtp=False`,
    "Detectar" añade una unidad removable real (H:\).
  - `test_detect_skips_non_removable_usb_without_explicit_backend`: "Detectar"
    filtra unidades no removibles (F:\), manteniendo las reales (E:\).
- Combina con el hardening de `FILE_REMOVABLE_MEDIA` en utils.py: H: se detecta
  de verdad, E:/F: (no removibles) quedan fuera por el flag, no por esconderlas.
- Suite: `python -m pytest tests -q` → 346 passed, 5 skipped. Nota: el único
  fallo puntual `test_mtp.py::test_wpd_session_devicename_no_duplicate` es
  flaky de entorno (enumera dispositivos WPD reales; pasa aislado y no toca
  ni mtp.py ni esta ruta).
- **Pendiente de commit** cuando el usuario lo solicite: app/core/utils.py,
  app/ui/add_source_dialog.py, tests/test_ingestor.py, tests/test_add_source_dialog.py
  + docs `.planning/debug/*.md`.
