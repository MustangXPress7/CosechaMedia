---
created: 2026-09-02T18:50:00Z
title: Cambios fase 1.6.0 bugs y mejoras origen WiFi
area: ui
severity: major
files:
  - app/ui/main_window.py
  - app/ui/source_picker.py
  - app/ui/device_picker.py
---

## Problem

Recuperación de cambios y bugs registrados durante la fase 1.6.0 que se perdieron de la documentación. Se necesita capturar para priorizar después.

**Bugs:**
1. Se añade "Wifi" desde orígenes, pero al abrir el QR una vez, desaparece de la tabla de orígenes.
2. Deseleccionar un origen en la tabla de orígenes es más agresivo que la propia papelera, la cual debería borrar el origen. Deseleccionar debería inhabilitar ese origen sin borrarlo del proyecto.

**Cambios:**
1. Borrar el botón de "Escanear cámaras".
2. Mover el botón de "Detectar" a la ventana de "añadir origen", la cual servirá para añadir a esa lista orígenes que el sistema detecte, tanto guardados como sin crear. En la fase donde está no tiene mucho sentido, ya que contamina proyectos ya creados.
3. La "Detección de cámara" debería suceder al seleccionar un dispositivo en la ventana de "añadir origen" que no tenga un nombre de cámara, junto a un pop-up que avise que el proceso se está desarrollando, junto a su tiempo establecido de proceso en el proyecto. Si no lo consigue, el flujo continúa con el pop-up clásico de añadir cámara de manera manual.

**Milestone a futuro (reubicado a Fase 1.7.0):**
Volcado por orden de dispositivo, para cuando solo hay un lector y hay que ir rotando las tarjetas.

Origen: cambios realizados en fase 1.6.0 anteriores.

## Solution

TBD — priorizar y planificar resolución en próximo milestone. Revisar flujo de origen WiFi, lógica de deselección vs borrado, reubicación de botones Detectar/Escanear y trigger automático de detección de cámara al añadir origen.
