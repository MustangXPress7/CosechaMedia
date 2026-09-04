---
quick_id: 260904-eae
slug: fix-on-file-finished-unboundlocalerror-c
title: Fix on_file_finished UnboundLocalError (camera_item)
---

# Quick Task 260904-eae: Fix on_file_finished UnboundLocalError (camera_item)

## Problem

Al hacer una ingesta con dos sesiones del mismo origen y distinto destino, se
lanzaba:

```
UnboundLocalError: cannot access local variable 'camera_item' where it is not
associated with a value
```

en `on_file_finished` (app/ui/main_window.py:1898) →
`self.table.setItem(row, 1, camera_item)`.

Root cause: en `on_file_finished`, `camera_item` solo se asignaba en dos ramas:
- `metadata_verified is False` → marker "Metadatos no verificados"
- `camera_model != "Unknown"` → modelo de cámara

Cuando `metadata_verified` NO era False **y** `camera_model == "Unknown"`,
ninguna rama asignaba `camera_item`, pero el código seguía ejecutando
`self.table.setItem(row, 1, camera_item)` → `UnboundLocalError`. Con células
compartidas (varias sessiones/ingestores sobre la misma ruta) este caso se
dispara para archivos cuyo ffprobe devuelve cámara "Unknown".

## Fix

Añadida rama `else` que conserva el valor ya mostrado en la celda de cámara
(nombre persistido o "Detectando...") en lugar de "Unknown", de modo que
`camera_item` SIEMPRE queda enlazado antes de `setItem`. También se simplificó
el tooltip del marker dentro de la misma rama `metadata_verified is False`.

## Test

Nuevo `test_unknown_camera_keeps_existing_value_no_crash` en
`tests/test_main_window.py` (`TestMetadataUnverifiedMarker`): reproduce el
caso `camera_model == "Unknown"`, `metadata_verified True`, verifica que no
crashea y que la celda de cámara conserva "Detectando..." (columna 1) y el
estado (columna 2) es "Completado".

## Verification

- `pytest tests/test_main_window.py` -> 40 passed
- `pytest tests/test_wifi_source.py tests/test_source_content.py` -> 71 passed
- Full suite `pytest tests` -> 344 passed, 5 skipped

## Commits

- Code/test: (fix commit)
- Docs: (docs commit)
