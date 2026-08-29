---
title: "Integración MTP+SD en registro único de dispositivos"
trigger_condition: "Cuando fase 1.6.0 inicie (planificación REQ-09/10)"
planted_date: 2026-08-29
phase: "1.6.0"
requirements: ["REQ-09"]
---

## Idea
Unificar identidad de **cámara física** conectada vía:
- **MTP** hoy (cuerpo de cámara + tarjeta dentro)
- **Lector SD** mañana (misma tarjeta extraída)

Mismo registro `known_devices` → misma cámara, preferencias, historial.

## Preguntas abiertas
- ¿Clave de unión? ¿Serial de cuerpo (MTP) + serial tarjeta (SD)?
- ¿Qué pasa si MTP expone serial de cuerpo pero SD solo serial de tarjeta?
- ¿Heurística: mismo `camera_model/make` + misma `volume_label` + solape temporal → mismo dispositivo?