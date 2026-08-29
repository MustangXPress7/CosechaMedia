---
title: "UI: Sugerencias contextuales en 'Añadir origen' para dispositivos conocidos"
date: 2026-08-29
priority: high
phase: "1.6.0"
requirements: ["REQ-09"]
---

## Descripción
Cuando el usuario abre "Añadir origen" y la app detecta una ruta/volumen que coincide con `known_devices`:
- Muestra tarjeta: **"Dispositivo conocido: Sony A7IV (tarjeta #3)"** con botón **"Usar esta configuración"**
- Al pulsar: pre-rellena cámara (model/make), ventana de contenido, destino predeterminado
- Usuario solo confirma → salta configuración manual

## Controles de edición (simples)
- **Renombrar cámara** (edita `camera_model` en el registro)
- **Olvidar dispositivo** (borra entrada de `known_devices`)

## Archivos a tocar
- `app/ui/source_picker.py` / diálogo "Añadir origen"
- `app/core/db.py` (métodos `get_known_device`, `update_known_device`, `forget_known_device`)
- `app/core/ingestor.py` (hook post-ingesta para aprender/actualizar registro)