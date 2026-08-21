# Summary — Lote de pulido UI (9 cambios)

Quick task: `260821-io6` · Fecha: 2026-08-21 · Estado: **Needs Review** (verificación visual pendiente del operador)

## Qué se hizo

4 commits atómicos:

| Commit | Contenido |
|--------|-----------|
| `da961a9` | C8 + C9 — `theme.py`: flechas de combo como triángulos (`width/height: 0` en `QComboBox::down-arrow`) y botones primarios dependientes del acento |
| `1693a82` | C1 — Wizard: «Opciones avanzadas» colapsado por defecto (checkbox que muestra/oculta Duración/Organización/Detección/Proxies); altura mínima 620→380 |
| `b2b81f3` | C2 + C3 — WiFi: `_pick_wifi_source()` abre el panel QR directamente (sin `WifiMethodDialog`); módulo `wifi_picker.py` eliminado (+ limpio en `update_translations.ps1`); orden de botones del lanzador: Examinar / USB-MTP / **WiFi QR** / FTP |
| `ed71c7e` | C4-C7 — Progreso sin texto hasta finalizar (`"%v / %m archivos"` solo en `_finalize_ingest`); combo de sesiones elástico (sin máximo 200px, política Expanding); icono de configuración = llave inglesa (`wrench.svg` nuevo, estilo Lucide tintable); tabla de orígenes: Ruta=Stretch, Cámara=70, Opciones=110 |

## Detalles de diseño

- **C9**: nuevo helper `_primary_action_colors(name, accent)` en `theme.py`. Base = color del acento elegido; con Neutro cae a `accent_selection` (azul). Oscuro: bg=mezcla 30% negro, hover=acento, pressed=55%; Claro: bg=acento, hover=18%, pressed=38%. Sustituye `@success_bg/@success_hover` en `QPushButton#PrimaryAction` (con regla `:pressed` nueva), `QProgressBar::chunk` y `QCheckBox::indicator:checked`. Los verdes semánticos de texto (éxito/peligro/aviso) se conservan. `PrimaryAction` ahora fuerza `color: @on_accent`.
- **C2**: los tests `test_pick_wifi_source_*` se reescribieron: uno verifica la llamada directa a `_open_wifi_panel(force_new_sender=True)`; el de FTP clásico se eliminó (el flujo FTP sigue vivo por su botón propio). El mock de `app.ui.wifi_picker.WifiMethodDialog` ya no es necesario.
- **C7**: test `test_source_path_column_interactive_with_default_width` actualizado a `test_source_path_stretches_and_options_fixed` con el nuevo contrato. `sourceListWidths` en `closeEvent` se deja tal cual (nunca se lee).

## Verificación

- Suite completa offscreen: `python -m unittest discover -s tests` → **Ran 296 tests — OK (skipped=5)**.
- Smoke del wizard y de `build_qss` en 2 temas × 6 acentos sin placeholders huérfanos.

## Nota para el operador (preexistente, no de esta tarea)

`tests/test_wifi_source` (y a veces la suite completa) termina con crash nativo al **salir** del proceso (exit `-1073740791`, 0xC0000409) **después** de imprimir "OK". Reproducido en `HEAD~2` (antes de este lote): es un problema de teardown Qt/hilos preexistente, no de los cambios. Los tests pasan; solo el código de salida miente. Candidato a quick task futuro.

## Segunda pasada (feedback del operador): todo el azul por defecto sigue al acento

Commit `3b699d7` — `theme.py`:

- Nuevo `_effective_accent_colors(name, accent)`: con acento elegido, sobrescribe
  `accent`/`accent_selection`/`accent_pressed` de la paleta (oscuro: acento puro y mezclas
  30 %/55 % con negro; claro: acento oscurecido 25 % para contraste sobre blanco, pressed 45 %).
  Con Neutro devuelve `{}` → paleta base (azul) intacta.
- `build_qss()` aplica esas claves: bordes hover/focus de botones, selecciones de listas/tablas/menús,
  radio marcado, handle del splitter, título de groupbox en hover… todo sigue al acento.
- `color('accent'|'accent_selection'|'accent_pressed')` ahora es consciente del acento → la barra de
  proyecto (`project_path_label`), la etiqueta de app, títulos del wizard/about/volcado selectivo y el
  pintor de cabeceras del volcado siguen al acento sin tocar sus call sites.
- `_primary_action_colors` refactorizado para derivar de las claves efectivas (misma salida en Neutro;
  en claro con acento no neutro los primarios quedan algo más oscuros = mejor contraste con texto blanco).

Verificación: QSS sin placeholders ni azules base en dark/light × 5 acentos; suite completa
296 tests OK (skipped=5).

## Pendiente del operador

- Revisión visual: tema oscuro/claro × cada acento (botón INICIAR INGESTA, barra de progreso, checkboxes marcados).
- Regenerar traducciones si se quiere catálogo EN al día (`tools/update_translations.ps1`): hay strings nuevos («Opciones avanzadas», tooltip) y entradas huérfanas de `WifiMethodDialog` en el `.ts`.
