---
created: 2026-09-03T00:00:00Z
title: Plan de accion post-incidente Fase 1.6.0 (recuperacion + avance)
area: planning
severity: major
files:
  - .planning/phases/01.6.0-registro-known-devices-req-09/01.6.0-CONTEXT.md
  - app/ui/main_window.py
  - app/ui/source_picker.py
  - app/ui/add_source_dialog.py
  - app/ui/reorganize_dialog.py
  - tests/test_source_picker.py
---

## Contexto (para cuando se pierda el hilo del chat)

La primera ejecución de la Fase 1.6.0 salió mal (casi insalvable): se desmadró
`app/ui/main_window.py` y el botón "añadir origen" (hacía desaparecer la ventana de
abrir origen). Se revirtió y se reformularon bugs ya resueltos.

- La **discusión/contexto YA está capturada y commiteada**:
  `.planning/phases/01.6.0-registro-known-devices-req-09/01.6.0-CONTEXT.md`
  (decisiones D-01..D-25) + `01.6.0-DISCUSSION-LOG.md` (commits `990cb62`, `5366e2d`).
- Lo que "se desmadró" fue **main_window.py + añadir origen**; el test de esa área
  (`tests/test_source_picker.py`) **CUELGA** — señal de que quedó roto.
- El fix de SC4 (thread-local COM) está **escrito pero sin commitear** en
  `main_window.py` y sus tests (`test_main_window.py`, `test_mtp.py`) pasan.
- El árbol de trabajo está **muy sucio** (15 `mtp_debug*.py`, `fix_*.py`,
  `old_main*.py`, `run_*.py`, 8 dirs de fases fantasma, `main_window.py` +
  `ROADMAP.md` modificados sin commitear).

**Regla para downstream:** seguir el orden A → B → C. NO planificar/editar sobre un
árbol sucio con un test colgante.

---

## A — Limpieza y estabilización del repositorio (PRIMERO)

1. Sanar el árbol de trabajo: apartar/eliminar del repo raíz el código de debug sin
   commitear (`mtp_debug*.py`, `fix_mtp.py`, `fix_device_picker.py`, `old_main.py`,
   `old_main_75.py`, `replace_method.py`, `run_ast*.py`, `run_semantic.py`,
   `run_merge.py`, `run_step*.py`). Mover a temp si se quiere conservar. NO commitear.
2. Resolver `app/ui/main_window.py` modificado sin commitear: es el fix SC4 que
   probablemente SÍ se quiere (thread-local COM + `_reset_ingestors` + invocaciones en
   borrar/cambiar proyecto). Commitearlo como fix o absorberlo en el plan; no dejarlo
   colgado.
3. Limpiar dirs de fases fantasma (`03-`..`10-` con solo `.gitkeep`) y el PROPOSED.md
   stale `1.6.0-verificacion-avanzada-reorganizador/` (causa warning de fase duplicada).
4. Commit de housekeeping del rename staged (`revisar-awesome-python.md` →
   `1.8.0-revisar-awesome-python.md`) y el delete sin commitear de
   `ui-sugerencias-dispositivos-conocidos.md`.
5. Registrar en STATE.md el incidente: 1.6.0 se reinicia desde el contexto recién
   capturado; el código huérfano de la 1.6.0 fallida se descarta/absorbe vía plan.

## B — Verificación del estado base (gate de entrada a plan-phase)

6. Arreglar/aislar el cuelgue de `tests/test_source_picker.py` (el resto de la suite
   pasa). Localizar qué test cuelga (QThread/timer/QDialog modal del añadir origen) y
   corregirlo.
7. Correr la suite completa (`tests/`, Qt offscreen) hasta que pase sin cuelgues; usar
   timeouts por módulo.
8. Si el fix SC4 sin commitear está correcto, absorberlo en el plan (D-23..D-25 ya lo
   describen; verificar CoUninitialize balanceado y `.stop()` de ingestors/watchers).

## C — Implementación (debe salir del plan de `/gsd-plan-phase 1.6.0`)

9. **D-01..D-04 — Diálogo "Añadir origen" plano** (`app/ui/add_source_dialog.py`):
   tabla única 3 secciones (física MTP/USB/SD, WiFi, FTP) sin pestañas; columnas
   checkbox | ubicación | nombre | estado | papelera; guardados + detectados
   integrados; reemplaza `SourcePickerDialog`. **CRÍTICO:** no romper la apertura de la
   ventana (síntoma del desastre original).
10. **D-05..D-07 — Menú dispositivo SC1**: solo botón QR para WiFi en columna Ruta;
    quitar USB/FTP (reconfigurar = borrar+crear); fix "WiFi no desaparece al abrir QR".
11. **D-08..D-09 — Detección de cámara**: mover "Detectar" al diálogo, quitar "Escanear
    cámaras", auto-detección non-blocking al seleccionar sin nombre + fallback manual.
12. **D-10..D-12 — Eliminar vs inhabilitar SC2**: check=inhabilitar (fila atenuada),
    papelera=borrar del proyecto, columna papelera por dispositivo + kill-switch menú.
13. **D-13..D-15 — Distinción MTP vs USB masivo**: columna tipo + flujo por tipo; fallo
    WPD/COM = aviso non-bloqueante, nunca crashear.
14. **D-16..D-22 — Reorganizador "_SinClasificar" SC3** (`app/ui/reorganize_dialog.py`):
    carpeta nueva `SinClasificar/` sustituye `Unknown_Camera`; diálogo selector +
    resumen; sustituye a "Reorganizar por metadatos" + opción en menú; verificación/
    re-registro MD5 (override del roadmap); sin CSV; independiente de ingesta activa.
15. **D-23..D-25 — Thread-local COM SC4**: ya implementado sin commitear → revisar/gate
    de tests y formalizar en TODOS los resets (borrar + cambiar proyecto + stop/restart
    de ingesta) + detener timers (auto-sync/detección).

## D — Cierre

16. Commit por cambio (atómico, estilo GSD de la repo: `feat(...)`/`fix(...)`/`docs(...)`).
17. Suite completa verde + actualizar `STATE.md`/histórico.
