# Research Questions — CosechaMedia

## 2026-08-29 — Registro unificado dispositivos (Fase 1.6.0)

### RQ-1: ¿Cómo correlacionar identidad MTP vs SD?
- MTP expone: PnP device ID, serial de cuerpo, storage ID
- SD expone: volume label, serial de tarjeta (via `sd_reader`), filesystem UUID
- ¿Existe overlap confiable? ¿Heurística basada en `camera_model` + timestamps?

### RQ-2: ¿ffprobe falla por falta de metadata o por matching?
- Instrumentar (REQ-10) para obtener datos reales
- Decidir: ¿registro inferido sustituye detección o solo fallback?

### RQ-3: Persistencia `card_hash` — ¿qué hash?
- `blkid` / `lsblk` UUID en Linux, `GetVolumeInformation` en Windows
- ¿Estable tras formateo? ¿Cambia con adaptador USB-SD?