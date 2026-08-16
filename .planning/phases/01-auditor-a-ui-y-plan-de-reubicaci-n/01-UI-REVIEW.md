# Phase 01 — UI Review

**Audited:** 2026-08-16
**Baseline:** 01-UI-SPEC.md (design contract) + 01-PLAN-REUBICACION.md (R-01…R-17, aprobado 2026-08-15)
**Screenshots:** not captured (aplicación de escritorio PySide6 — auditoría de código; no hay dev server web)
**Registro auditado:** no aplicable (no hay shadcn/components.json)

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Strings ES vía `tr()` correctos y específicos, pero la confirmación de borrar sesión declara una consecuencia falsa y el label del botón principal muta de caso |
| 2. Visuals | 3/4 | Jerarquía clara y focal point correcto, pero la línea de descripción del proyecto usa word-wrap en vez del ellipsis contratado y los iconos son glifos emoji |
| 3. Color | 4/4 | Paleta única centralizada (theme.py), acento dentro de la regla 60/30/10, sin colores hardcoded fuera de casos deliberados |
| 4. Typography | 4/4 | Stack Segoe UI/Helvetica/Arial + Cascadia Mono (URL WiFi), 5 tamaños y 3 pesos dentro del contrato |
| 5. Spacing | 3/4 | Escala 4/6/8/10/20 respetada en QSS y layouts, pero R-11 incumplida: col0 no es Interactive y el ancho de columnas no se persiste |
| 6. Experience Design | 2/4 | Estados cubiertos, pero hay un botón Aceptar muerto en «Guardados», ProjectWizard huérfano (código muerto), confirmación de apagado con default Yes y flujo de creación degradado |

**Overall: 19/24**

---

## Top 3 Priority Fixes

1. **Botón «Aceptar» muerto en la pestaña Guardados del diálogo «Añadir origen»** — Con la pestaña abierta y sin selección, Aceptar está habilitado pero al pulsarlo no ocurre nada (silencioso); clicar un encabezado de sección o un "(vacío)" también es un no-op silencioso. Es exactamente la clase de control que el usuario denunció como "parece que no hace nada". — `app/ui/source_picker.py:210` habilita OK incondicionalmente en `_on_tab_changed(0)` y `_accept_current` (`:226-233`) no acepta si `kind is None`. **Fix:** habilitar OK solo cuando `list_widget.currentItem()` tenga `data(UserRole)` no nulo, y conectarlo a `itemSelectionChanged`.

2. **Flujo de creación de proyecto degradado + ProjectWizard huérfano (código muerto)** — `_show_create_project` (`app/ui/main_window.py:1281-1314`) usa dos `QInputDialog` apilados (nombre → descripción), mientras el `ProjectWizard` que el propio UI-SPEC (`01-UI-SPEC.md:185`) declaró "referencia de buena organización" no se importa en ningún sitio del runtime (solo en `tools/update_translations.ps1:15` y `capture_ui.py`). El usuario pierde la config de destino, duración, organización y fecha-metadatos al crear. **Fix:** enrutar `_show_create_project` a través de `ProjectWizard` (600×520 con grupos y PrimaryAction) o eliminar el archivo y documentar el flujo QInputDialog como decisión.

3. **Consecuencia falsa en el diálogo de borrar sesión y default Yes en apagado** — `_delete_current_session` (`main_window.py:2601`) dice "¿Eliminar la sesión #%1 y todos sus archivos?" pero `db.delete_session` (`app/core/db.py:544-550`) solo borra filas de BD; el material en disco se conserva. Mensaje engañoso en ambas direcciones (el usuario que quiere liberar espacio creerá que lo hace). Además `_shutdown_computer` (`main_window.py:1944`) tiene `QMessageBox.Yes` como default: un Enter apaga el equipo, rompiendo el patrón D-09 (default No) del resto de confirmaciones. **Fix:** cambiar el copy a "…y sus registros de ingesta (los archivos en disco se conservan)" y `QMessageBox.No` como default en el apagado.

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

**Cumplido**
- Todos los strings nuevos pasan por `tr()` (patrón QtString) y el catálogo EN fue regenerado (`app/i18n/cosechamedia_en.ts` modificado en v2).
- Estados vacíos específicos y útiles: "No se detectaron dispositivos. Revisa el cable y pulsa Actualizar." (`app/ui/device_picker.py:136`), "(Sin sesiones)" (`main_window.py:2487`), "Sin dispositivos guardados" / "Sin dispositivos conocidos" (`source_picker.py:112,174`), "— Añadir nuevo servidor —" (`ftp_picker.py:207`).
- Confirmaciones destructivas con consecuencia nombrada: eliminar origen lista "y sus sesiones (%2)" (`main_window.py:2364`), eliminar proyecto lista "y todos sus datos" (`:3778`), formateo lista las unidades + modo + omitidos (`:1900-1907`).

**Hallazgos**
- **Falso en consecuencia** — `main_window.py:2601` "¿Eliminar la sesión #%1 y todos sus archivos?" vs `db.delete_session` (`db.py:544-550`) que solo borra registros; los archivos en disco no se tocan. El texto no describe la acción real.
- **Label del botón principal muta** — creado como "INICIAR INGESTA" (`main_window.py:547`); tras cualquier ingesta/reorganizar/proxies se reescribe "Iniciar Ingesta" (`:1628,:1760,:1823,:4044`), perdiendo el estilo inicial sin razón.
- **Muro de texto FTP** — `GUIDE_TEXT` (`ftp_picker.py:21-41`) son 20 líneas densas de tutorial en un solo QTextEdit; densidad alta en un diálogo que ya tiene 6 campos + árbol. Fragmentar en pasos o acortar.
- Glifos emoji como iconos ("🗑","📶","📱","⟳") no pasan por traducción; en Linux/macOS pueden renderizar como tofu (ver Visuals).

### Pillar 2: Visuals (3/4)

**Cumplido**
- Focal point claro: botón INICIAR INGESTA (PrimaryAction verde, 13px bold) en la columna izquierda; jerarquía header (13px bold accent) → secciones (11px 600) → contenido.
- R-06 ✓: filas de sesión apiladas verticalmente (`main_window.py:472-507` aprox.) — la sesión ocupa su fila, no 2 columnas.
- Tabla de orígenes con selección de fila, contexto y botón 🗑 deshabilitado sin selección (`:389-394`).
- Fondo de campo de trigo con tinte del acento (`DashboardBackground.paintEvent`, `:121-127`) y toggle persistente (`:1350-1353`).

**Hallazgos**
- **Desviación R-10** — `project_description_label` usa `setWordWrap(True)` + `Expanding` (`main_window.py:355-357`); el contrato (UI-SPEC D-10) pedía truncado con ellipsis + tooltip completo. Una descripción larga envuelve en varias líneas y empuja la zona de contenido hacia abajo; además "(sin descripción)" se muestra siempre (`:1256`), info constante que roba 1 fila vertical.
- **Iconos emoji en vez de iconos reales** — 6 botones de la header (`main_window.py:285-292,323`) y 2 en orígenes usan glifos unicode ("⟳ ✎ ⧉ 📁 ⚙ 🗑"). Con tooltip ✓, pero sin fallback tipográfico; en Linux sin fuente emoji quedan como cuadros.
- `MtpDevicePane._load_children` (`device_picker.py:167-171`) traga excepciones y muestra carpetas vacías sin distinguir "vacía" de "error al leer": el usuario puede elegir una carpeta que en realidad falló al enumerarse.

### Pillar 3: Color (4/4)

- Paleta única en `theme.py` (DARK/LIGHT + 5 acentos), QSS por placeholders `@clave`; sin dispersión de hex en los widgets (solo 2 literales, ambos deliberados: borde del QR `#333` y fondo blanco del QR en `wifi_panel.py:106,253` — necesario para contraste del código).
- Distribución 60/30/10 respetada: base neutra (`#0d1117`/`#161b22`), texto secundario/bordes ≈30%, acento `#58a6ff` solo en hover/focus/selección/tab/menú — 6 usos, ninguno decorativo.
- Acentos alternativos aplicados vía tinte al fondo (`ACCENT_TINT_RATIO=0.15`, `theme.py:71`) con recálculo en `_switch_theme`/`_switch_accent` (`main_window.py:1334-1348`).
- Contraste texto/fondo correcto en ambos temas (`#f0f6fc` sobre `#0d1117`; `#1f2328` sobre `#ffffff`).
- Nota: el CTA primario usa `success_bg` (verde) en vez del accent — decisión consistente en toda la app (Aceptar/Guardar/Crear/Conectar son verdes), no se puntúa como fallo.

### Pillar 4: Typography (4/4)

- Stack contratado presente: `'Segoe UI', 'Helvetica Neue', Arial, sans-serif` (`theme.py:88`); `Cascadia Mono, Consolas, monospace` para la URL del WiFi (`wifi_panel.py:116`).
- Tamaños: 10px (headers de tabla `theme.py:245`, status `main_window.py:341`), 11px (controles/labels), 12px (base/diálogos), 13px (PrimaryAction `theme.py:131`, app label `main_window.py:275`), 22px (título About `about_dialog.py:123`) — 5 niveles, dentro del contrato.
- Pesos: 400, 600 (headers/grupos), 700 (bold) — 3 pesos, sin abuso de extrabold.
- Sin tamaños arbitrarios fuera del sistema; el desajuste "INICIAR INGESTA" vs "Iniciar Ingesta" es un problema de copy, no de escala.

### Pillar 5: Spacing (3/4)

- Escala 4/6/8/10/20 del UI-SPEC respetada: botones 4px 10px (`theme.py:105`), inputs 3px 6px (`:164`), primary 8px 20px (`:132`), celdas 4px 6px (`:228`), diálogos 14-16px márgenes + 8-10px spacing (`source_picker.py:57-58`, `ftp_picker.py:110-111`, `main_window.py:702`), pestañas 6px + 8px (`source_picker.py:109-110`).
- Sin valores arbitrarios (`[Npx]`/`[Nrem]` de Tailwind n/a; en Qt no hay valores fuera de escala).
- **Desviación R-11 (incumplida en 2 puntos)**:
  1. `source_list` col0 = `Stretch`, col1/col2 = `Interactive` (`main_window.py:430-432`) — el contrato pedía las 3 Interactive; col0 estirada impide al usuario redimensionar la ruta a gusto y condiciona el layout.
  2. El ancho de columnas **no se persiste**: solo se guarda `windowState`/`geometry` de la QMainWindow (`main_window.py:201-211,1156`); no hay `header().saveState()`/`restoreState()` para `source_list` ni `table`. Cada arranque vuelve a `resizeSection(1,160)`, `resizeSection(2,110)` (`:434-435`).

### Pillar 6: Experience Design (2/4)

**Cumplido**
- Estados de carga: "Cargando…" (`device_picker.py:139`), escaneo FTP en QThread (`ftp_picker.py:44-50`), "Comprobando actualizaciones..." (`about_dialog.py:216`), progreso de descarga (`:252-262`), progreso de ingesta por señales Qt.
- Estados vacíos: pestañas del diálogo unificado, `(vacío)` por sección, "(Sin sesiones)", "El servidor no está activo." (`wifi_panel.py:173`), "Sin proyectos para eliminar" (`main_window.py:3819`).
- Estados de error: lectura de dispositivo (`device_picker.py:143-145`), actualización (`about_dialog.py:242-246`), errores de ingesta → `notify_ingest_failed` + bloqueo de formateo/apagado con warning enumerado (`main_window.py:1795-1806`).
- Disabled correcto: `btn_start` sin proyecto/origen (`:1355-1365`), 🗑 sin selección (`:2358`), formateo sin unidades extraíbles (`:1870-1878`), OK de pickers gated en `can_accept()`.
- R-01/R-02/R-03/R-04/R-07/R-09/R-12/R-17 implementados: grupo "Acciones post-ingesta" con subgrupos "Al terminar"/"Operaciones" (`:602-658`), confirmaciones de formateo (`:1905`), reorganizar (`:4031`), eliminar origen (`:2364`), proyecto (`:3775`), entrada unificada "Añadir origen…" (`:409-412`) con dialogo de 3 pestañas.

**Hallazgos**
1. **Aceptar muerto en «Guardados»** (`source_picker.py:210,226-233`): OK habilitado siempre en tab 0; sin selección (o con selección en un encabezado/`(vacío)`, cuyo `role` es None) el clic no hace nada y no hay feedback. Patrón "botón que no hace nada".
2. **ProjectWizard huérfano**: cero imports en el runtime (grep `ProjectWizard|project_wizard` → solo `.ts`, `tools`, `capture_ui.py`). El flujo real de creación son 2 QInputDialog apilados (`main_window.py:1282-1290`) que omiten destino, duración, organización y fecha-metadatos que el wizard capturaba. Dead code + flujo degradado.
3. **Apagado con default Yes** (`main_window.py:1944`): un Enter apaga el equipo; todas las demás destructivas usan default No. Riesgo real en rodaje.
4. **Controles ocultos en vez de eliminados**: `btn_browse_source.hide()` (`main_window.py:407`) y `btn_receive_wifi.hide()` (`:418`) permanecen en el layout con su lógica viva; los tests siguen ejerciendo `btn_receive_wifi.isEnabled()` (`tests/test_wifi_source.py:96,101`). Funcional: el WiFi entra por el diálogo, pero queda código zombie que confunde futuras refactorizaciones.
5. **`_on_search_again` acopla a privado** (`source_picker.py:206` llama `self.mtp_pane._load_devices()`): funciona, pero es una dependencia entre clases por método privado.
6. **Falsas consecuencias en borrado de sesión** (ver Pillar 1) — rompe la confianza en el diálogo destructivo.

---

## Files Audited

- `app/ui/main_window.py` (4091 líneas — Zona A completa: header, R-10, R-11, R-12, R-01…R-09, handlers de sesión/origen/proyecto/post-ingesta)
- `app/ui/source_picker.py` (324 — diálogo unificado D-12, 3 pestañas, gestión de guardados)
- `app/ui/device_picker.py` (287 — MtpDevicePane/DevicePickerDialog, estados y DCIM-suggest)
- `app/ui/ftp_picker.py` (507 — FtpDevicePane, guía, scan en hilo, perfiles)
- `app/ui/theme.py` (698 — paleta, QSS, acentos, tintes)
- `app/ui/wifi_panel.py` (284 — ShootInboxPanel no modal, QR, copiar/parar)
- `app/ui/selective_dump.py` (889 — asistente 4 páginas, workers con cancelación)
- `app/ui/about_dialog.py` (310 — Acerca de/Actualizaciones, estados y cancelación)
- `app/ui/project_wizard.py` (172 — **huérfano**, sin import en runtime)
- `app/core/db.py` (solo `delete_session`, `:544-550` — semántica del borrado)
- `tests/test_wifi_source.py` (referencias a `btn_receive_wifi`, `:96,101`)
- Referencias de contrato: `01-UI-SPEC.md`, `01-PLAN-REUBICACION.md`, `01-INVENTARIO.md`

---

## Notas de alcance

- Auditoría de código puro (app de escritorio Qt, sin servidor web capturable); las capturas de la fase 1 (`captures/zona*.png`) cubren la verificación visual previa.
- `ProjectWizard` queda en `app/ui/` sin uso runtime — candidato a eliminar o reactivar (ver Fix #2).
- Hang preexistente documentado en `tests/test_wifi_source.py:726` (mock namespace) fuera del alcance de v2; no se puntúa aquí.
