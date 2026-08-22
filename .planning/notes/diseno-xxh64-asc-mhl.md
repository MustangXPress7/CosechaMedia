---
title: Diseño XXH64 + ASC MHL (verificación avanzada)
date: 2026-08-22
context: Sesión /gsd-explore previa a planificar la fase. Decisiones acordadas con el operador/desarrollador para no re-debatir durante plan-phase.
---

# Diseño XXH64 + ASC MHL

## Decisiones (orden de conversación)

### D1 — Política de hash configurable por proyecto

Tres niveles seleccionables por proyecto (mismo patrón que organización/fechas desde v1.5):

| Nivel | Árbitro de la copia | Manifiestos |
|-------|--------------------|-------------|
| Rápida | XXH64 durante copia | solo `xxh64` |
| Equilibrada (default) | XXH64 durante copia | `md5 + xxh64` (segunda pasada MD5 sobre destino al terminar volcado) |
| Máxima | MD5 durante copia | `md5` + sidecars `.sha256` propios fuera del MHL |

Racional: XXH64 va a velocidad GB/s (MD5 por core se queda corto con CFexpress); MD5 es la compatibilidad universal (`md5sum -c`, Silverstack); SHA-256 es demanda de archivado a largo plazo, no de rodaje.

### D2 — Los manifiestos reflejan el nivel elegido

No hay MD5 garantizado siempre: el usuario asume el compromiso de compatibilidad al elegir Rápida. Decisión explícita tras ofrecer la alternativa "MD5 siempre".

### D3 — Cadena de generaciones por disco

Cada volcado completado sella **una generación nueva** en `ascmhl/` de la raíz destino (encadenado acumulativo). El disco que recibe volcados repetidos (ventanas N días, sesiones sucesivas) acumula la historia verificable completa — semántica estándar de custodia ASC MHL. Cada destino de la rotación de discos lleva su propia cadena.

### D4 — Usar el paquete oficial `ascmhl` (no escritor propio)

Verificado en sesión de investigación:

- API de librería completa: `MHLHistory.load_from_path(raíz)` → `MHLGenerationCreationSession` → `append_file_hash(ruta, size, mtime, formato, hash)` → `commit(creator_info, process_info)`. La misma sesión crea primera generación o añade generaciones a cadena existente.
- Licencia **MIT** — compatible con GPL-3.0-or-later (relicenciamiento 260822-ive).
- HashFormats soportados: `md5, sha1, xxh32, xxh64, xxh3, xxh128, c4`. **SHA-256 no implementado** → por eso los `.sha256` de Máxima van como sidecars propios fuera del estándar (D1).
- Python ≥3.11 requerido (exactamente nuestro runtime), Windows soportado, dependencias todas con wheels (click, lxml, packaging, pathspec, requests, xxhash, python-dateutil).
- Salud: v1.2 (2025-07-04), releases estables desde 2021, implementación de referencia oficial del ASC (Pomfort).

### D5 — UI: selector en wizard + menú

El selector de política vive en las opciones avanzadas del ProjectWizard **y** en el menú de configuración de proyecto — mismo patrón dual que fecha/organización desde 1.5 (wizard ≡ menú). Default silencioso si no se toca: Equilibrada.

## Implicaciones de alcance detectadas (para plan-phase)

- Dependencias nuevas: `ascmhl` (arrastra `xxhash`).
- Migraciones DB inline: columna `hash_policy` en `projects`; columnas de hashes en `files`.
- Refactor de `copy_verified` (app/core/ingestor.py): árbitro configurable, sin romper la semántica actual de borrado de destino corrupto.
- Segunda pasada de lectura MD5 sobre destino (nivel Equilibrada) tras completar el volcado.
- Informes CSV (integridad + contenido) ganan columnas de hashes.
- Tests: roundtrip de manifiestos validado contra la CLI oficial `ascmhl verify`.
