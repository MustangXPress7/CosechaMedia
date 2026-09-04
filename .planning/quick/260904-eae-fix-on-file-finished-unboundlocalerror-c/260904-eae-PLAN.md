---
quick_id: 260904-eae
slug: fix-on-file-finished-unboundlocalerror-c
title: Fix on_file_finished UnboundLocalError (camera_item)
---

# Quick Task: Fix on_file_finished UnboundLocalError (camera_item)

## Why

`on_file_finished` (app/ui/main_window.py) lanza
`UnboundLocalError: cannot access local variable 'camera_item'` cuando
`metadata_verified` no es False Y `camera_model == "Unknown"`, porque
`camera_item` no se asigna en ese caso pero `setItem(row, 1, camera_item)` se
ejecuta igualmente. Visible en ingestas con dos sesiones del mismo origen y
distinto destino.

## What

Añadir una rama `else` en `on_file_finished` para que `camera_item` siempre
quede enlazado: si el modelo es "Unknown" con metadatos verificados, conservar
el valor previo de la celda de cámara (nombre persistido o "Detectando...") en
lugar de sobreescribir con "Unknown".

## Tasks

1. Fix `on_file_finished`: rama `else` que asigna `camera_item` al valor
   existente de la celda (o vacío si no hay), manteniendo el marker y el
   tooltip de "Metadatos no verificados".
2. Test: `test_unknown_camera_keeps_existing_value_no_crash` en
   `test_main_window.py` — reproduce el caso sin crashear.
3. Verificar suite completa.
