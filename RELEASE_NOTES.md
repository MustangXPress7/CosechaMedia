# CosechaMedia v1.5.1 — Corrección actualizador

**Fecha:** 2026-08-30  
**Release** — Bug crítico: actualizador colgado en Windows

---

## 🐛 Bug corregido

- **Updater-Hang**: La aplicación colgaba al actualizar desde versiones legacy. El proceso no se cerraba limpiamente, dejando dos ejecutables (el nuevo y el antiguo). Solución:
  - **Timeout 30s**: El script helper ahora tiene un límite de espera y forza la terminación con `taskkill /F`
  - **Limpieza previa**: Se llama a `prepare_for_update()` para detener ingestors, watchers y threads de background
  - **Delay anti-carrera**: 500ms entre `install_update()` y `quit()` para que el helper se inicie

---

# CosechaMedia v1.5.0 — Consolidación y bugs del flujo

**Fecha:** 2026-08-29  
**Release estable** — 5 bugs de flujo resueltos + 5 mejoras de arquitectura

---

## 🐛 Bugs corregidos (CONCERNS.md)

- **F-01**: Sesión restante se refresca tras borrar otra
- **F-02**: Re-volcar si destino borrado (disco = fuente de verdad)
- **F-03**: Disco única verdad para re-volcar; resume JSON fuera de raíz
- **F-04/F-05**: Re-volcar dentro/fuera de ventana "últimos x días" si destino borrado

---

## ✨ Qué hay de nuevo

### Metadata fiable (Plan 01)
- **Retry degradado ffprobe**: timeout 10s → 1 reintento format-only 30s
- Flag `metadata_verified` en todo dict de metadata
- Marker UI "⛔ Metadatos no verificados" en celda cámara (+ tooltip), **nunca** en columna estado

### Hash MD5 único (Plan 02)
- `copy_verified` single-pass stream-through (sin relectura del destino = 2x I/O menos)
- Semántica de borrado corrupto preservada

### Inventario watcher persistente (Plan 03)
- Tabla `watcher_seen` SQLite con veredictos `copied`/`filtered`/`errored`
- `filter_key` → re-evalúa solo si la ventana de contenido cambió
- Poda 30 días, elimina cap 10k entradas
- Predicado `should_skip` compartido watcher+ingestor (preserva F-02)

### Regresiones + Gate suite (Plan 04)
- `_resolve_db_path()` CWD-independiente (test R3)
- Auto-sync off-thread vía `_run_background` (test R5)
- **Suite completa: 313 tests OK** (126 core)

---

## 📥 Descarga

| Plataforma | Artifact |
|------------|----------|
| Windows | `CosechaMedia-windows-x86_64.exe` |
| macOS | `CosechaMedia-macos.app.zip` |
| Linux | `CosechaMedia-linux-x86_64` |

> **Requisito:** FFmpeg/ffprobe en `PATH`

---

## 🔮 Próximo (v1.6.0)

- Reorganizador de footage (REQ-06)
- Registro unificado dispositivos `known_devices` (REQ-09)
- Instrumentación detección cámara ffprobe (REQ-10)
- Verificación avanzada XXH64 + ASC MHL
- Volcado selectivo multi-origen (ID-01/ID-02)