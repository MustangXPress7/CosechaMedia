---
title: Contribuir soporte SHA-256 a asc-mhl upstream
planted_date: 2026-08-22
trigger_condition: La fase "Verificación avanzada: XXH64 + ASC MHL" está cerrada y estable en producción, y hay capacidad de mantenimiento disponible. Confirmar antes si la spec ASC MHL contempla sha256 (ver .planning/research/questions.md).
---

# Contribuir soporte SHA-256 a asc-mhl upstream

## Idea

La implementación de referencia oficial (`ascmitc/mhl`, paquete `ascmhl`) soporta `md5, sha1, xxh32/64/xxh3/xxh128, c4` pero **no SHA-256**. Nuestro nivel Máxima usa sidecars `.sha256` propios fuera del estándar como solución provisional.

Si la spec contempla (o acepta) `sha256` como hashFormat, contribuir el soporte upstream convertiría nuestros manifiestos de archivado en 100% estándar y eliminaría los sidecars paralelos.

## Por qué tiene sentido desde CosechaMedia

- Ya tendremos el código de hashing SHA-256 propio (streaming sobre destino) — adaptarlo al `Hasher` de ascmhl es incremental.
- Ser contributors del estándar refuerza exactamente lo que vende la app: confianza y legitimidad en postproducción.
- GPL-3.0 no fricciona: asc-mhl es MIT.

## Primer paso cuando dispare

Abrir issue en https://github.com/ascmitc/mhl preguntando por la posición de la spec sobre sha256 antes de escribir PR alguno.
