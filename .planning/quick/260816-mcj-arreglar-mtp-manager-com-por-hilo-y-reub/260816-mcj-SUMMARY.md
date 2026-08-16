---
phase: 260816-mcj-arreglar-mtp-manager-com-por-hilo-y-reub
plan: 1
subsystem: app/core/mtp.py, app/ui/main_window.py, tests
tags: [quick, mtp, com, ui, tabla-origenes, tabla-ingesta, borrado-por-fila, volcado-selectivo]
requires: []
provides: []
affects:
  - app/core/mtp.py
  - app/ui/main_window.py
  - tests/test_mtp.py
  - tests/test_source_content.py
tech-stack:
  added: []
  patterns:
    - "thread-local singleton (threading.local()) para objetos COM por hilo"
    - "columna de borrado por fila con setCellWidget + captura de item (no índice) en tablas ordenables"
key-files:
  created: []
  modified:
    - app/core/mtp.py
    - app/ui/main_window.py
    - tests/test_mtp.py
    - tests/test_source_content.py
decisions:
  - "Manager COM IPortableDeviceManager por hilo via threading.local(); sin singleton global _DEVICE_MANAGER"
  - "devicename = {name}_{serial} (sin el componente duplicado)"
  - "Volcado selectivo reubicado de op_row (Operaciones) a src_scan_row (fila de orígenes)"
  - "col0 de source_list Interactive con ancho por defecto 320; minimumSectionSize 100 -> 40 (Qt 6 clampa resizeSection al mínimo)"
  - "Borrado por fila: source_list col3 (Fixed 40) elimina el origen con confirmación existente (default No); tabla de ingesta col5 (Fixed 40) solo removeRow via indexFromItem"
  - "Retirados btn_remove_source, _remove_selected_source y _update_remove_source_button"
metrics:
  duration: "1h"
  completed_date: "2026-08-16"
status: complete
actuals:
  tokens: 5035    # chars/4 sobre el diff real de 4 archivos (20.142 chars)
  tasks: 3
  commits: 5
---

# Phase 260816-mcj Plan 1: Arreglar MTP manager COM por hilo y reubicar UI Summary

## Resumen

Fix MTP thread-local del manager COM (`IPortableDeviceManager` por hilo vía `threading.local()`, eliminado el singleton global `_DEVICE_MANAGER` que causaba `RPC_E_WRONG_THREAD` entre el staging en QThread y el `list_devices()` del hilo principal) + nombre de dispositivo compuesto `{name}_{serial}` sin duplicado. Tres mejoras UI confirmadas: «Volcado selectivo…» movido a la fila de orígenes (`src_scan_row`), columna «Ruta de origen» redimensionable (Interactive, 320 por defecto, mínimo 40), y columnas de borrado por fila (🗑 Fixed 40 px) en ambas tablas con retirada del botón papelera de la cabecera.

## Tareas Ejecutadas

| # | Tarea | Commits | Estado |
|---|-------|---------|--------|
| 1 | Manager COM por hilo (thread-local) en mtp.py + tests | RED `236eccc` + GREEN `7b27666` | ✅ |
| 2 | Volcado selectivo a `src_scan_row` + col0 Interactive/320 | `1747d48` | ✅ |
| 3 | Columnas de borrado por fila en ambas tablas + retirada papelera | RED `3e123ff` + GREEN `3bf616d` | ✅ |

## Verificación

| Verificación | Resultado |
|--------------|-----------|
| `python -m unittest tests.test_mtp -v` | 12 tests OK (3 nuevos `TestThreadLocalManager`, skip no-Windows) |
| `python -m unittest tests.test_source_content -v` | 17 tests OK (6 nuevos, 2 actualizados a 4/6 columnas) |
| `python -m unittest tests.test_e2e -v` | 1 test OK |
| Gates `python -c` con asserts (Tasks 1-3) | OK |
| `python -m unittest discover -s tests -v` | 252 tests OK, 3 skipped (MTP live, sin dispositivo — preexistente) |

## Desviaciones del Plan

### Auto-fixed Issues

**1. [Rule 1/3 - Bug en test] `comtypes.client.CoUninitialize` no existe como atributo**
- **Found during:** Task 1, fase RED (`test_wpd_session_devicename_no_duplicate`)
- **Issue:** El plan especificaba parchear `comtypes.client.CoUninitialize` → no-op, pero `CoUninitialize` vive en el módulo `comtypes` de nivel superior (no en `comtypes.client`); el patch fallaba con `AttributeError`.
- **Fix:** Parchear `comtypes.CoUninitialize` en su lugar (mismo propósito: COM uninit como no-op en el test hermético; `close()` de `_WpdSession` usa `ctypes.CoUninitialize()` real, envuelto en try/except, y es seguro).
- **Files modified:** `tests/test_mtp.py`
- **Commit:** incluido en el RED final `236eccc`

Ninguna otra desviación — el plan se ejecutó tal cual (TDD estricto RED/GREEN en tareas 1 y 3, permitido por el plan).

## Resultado de Hechos (truths del plan)

- ✅ `_manager()` crea un `IPortableDeviceManager` por hilo vía `threading.local()`; no queda `_DEVICE_MANAGER` en `app/core/mtp.py`; `list_devices` y `_WpdSession._friendly_name` (hilos distintos) usan managers propios; `devicename` es `{name}_{serial}`.
- ✅ «Volcado selectivo…» está en `src_scan_row` (tras «Escanear cámaras») y no en «Acciones post-ingesta → Operaciones»; `_open_selective_dump` sin cambios.
- ✅ Col0 de `source_list` es `Interactive` con 320 por defecto; mínimo del header 40; «sourceListWidths» persiste 4 anchos en `closeEvent`.
- ✅ `source_list` tiene 4 columnas con borrado por fila (🗑 24×24, Fixed 40) que elimina el origen con la confirmación existente (default No); `btn_remove_source`/`_remove_selected_source`/`_update_remove_source_button` no existen.
- ✅ `self.table` tiene 6 columnas con borrado por fila que solo quita la fila de la vista (`removeRow` vía `indexFromItem(row_item).row()` con guard `row < 0`); nunca toca sesiones ni archivos; funciona con `setSortingEnabled(True)`.
- ✅ Tests nuevos en `test_mtp.py` y `test_source_content.py`; suite completa `python -m unittest discover -s tests -v` en verde (252 OK, 3 skips preexistentes).

## Threat Flags

Sin flags: el fix MTP es un refactor sin nueva superficie; los botones de borrado por fila implementan las mitigaciones del threat model del plan (T-260816-mcj-02/03/04: solo-vista con `indexFromItem`, confirmación default No, guard de item huérfano).

## Known Stubs

Ninguno. Las cabeceras vacías `""` de las columnas de borrado son intencionales (spec del plan).

## Self-Check: PASSED

- Archivos verificados: `app/core/mtp.py`, `app/ui/main_window.py`, `tests/test_mtp.py`, `tests/test_source_content.py` (modificados, diff presente).
- Commits verificados: `236eccc`, `7b27666`, `1747d48`, `3e123ff`, `3bf616d` (todos en `git log`).
- Suite completa en verde tras los cambios.
