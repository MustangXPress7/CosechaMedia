# Phase 1: Auditoría UI y Plan de Reubicación - Context

**Gathered:** 2026-08-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Entregar un diagnóstico completo de la interfaz de CosechaMedia desde la perspectiva del operador de cámara: qué controles existen, dónde están, qué está mal ubicado y hacia dónde deberían moverse. Se produce un **informe consolidado de hallazgos** (por zona, con evidencia y justificación) y un **plan de reubicación aparte**, priorizado y acordado. **No se implementa ningún cambio de código** — la ejecución es una fase posterior (v2, UI-04/UI-05). Nada puede quedar escondido en la interfaz: todo control relevante debe aparecer documentado.

</domain>

<decisions>
## Implementation Decisions

### Alcance y entregables
- **D-01:** La auditoría se organiza por **flujo del operador** (conectar → ingestar → formatear → reorganizar), cubriendo todas las zonas dentro de cada flujo. Las cuatro zonas (ventana principal/dashboard, pickers de fuente, asistentes y paneles, acciones post-ingesta) se cubren íntegramente — ninguna queda fuera. — **Reversibility:** reversible — el informe es un documento; reordenar su estructura no toca código.
- **D-02:** El entregable es **consolidado**: un único informe de hallazgos con todas las zonas, y un plan de reubicación separado. No informes sueltos por zona. — **Reversibility:** reversible.
- **D-03:** Regla transversal del usuario: **no esconder nada en la interfaz**. Todo control sigue accesible/descubrible en la propuesta. — **Reversibility:** one-way para la fase posterior — si una propuesta oculta controles, contradice la intención explícita del usuario y la fase de implementación la heredaría.

### Metodología de auditoría
- **D-04:** La evidencia combina **lectura de widgets** (estructura en `main_window.py` y diálogos) con **inspección visual** (ejecución de la app / capturas offscreen) para verificar posición y jerarquía reales de los controles. — **Reversibility:** reversible.
- **D-05:** Cada hallazgo se justifica con **heurísticas explícitas**: frecuencia de uso, consistencia entre diálogos, contexto de acción, descubribilidad y distancia de ratón. Nada se marca como problema sin criterio. — **Reversibility:** reversible.
- **D-06:** El plan de reubicación se prioriza con **matriz impacto×esfuerzo** + riesgo (tests, i18n, estética). — **Reversibility:** reversible.

### Hallazgos confirmados por el usuario (entrada directa al informe)
- **D-07:** **Zona post-ingesta** (lo que vive debajo de la barra de progreso): queda visualmente secundaria y está desordenada. Formateo/proxies/reorganizar viven ahí pero no se perciben como acciones principales del flujo. — **Reversibility:** reversible — diagnóstico.
- **D-08:** **Sesiones**: al configurar/ahondar, el panel crece hacia la derecha y come ancho de ventana; el espacio vertical disponible no se aprovecha. — **Reversibility:** reversible — diagnóstico.
- **D-09:** **Botones de eliminar**: mal ubicados Y mal presentados. Dependiendo del contexto (borrar sesión, borrar fuente, borrar origen) el control debería comportarse distinto — no un "eliminar" genérico en todas partes. — **Reversibility:** reversible — diagnóstico.
- **D-10:** **Descripción del proyecto**: el wizard la captura pero no aparece en ninguna vista posterior — dato muerto. Debe mostrarse en algún sitio (informe del proyecto / cabecera). — **Reversibility:** reversible — diagnóstico.
- **D-11:** **Tabla de orígenes**: columnas de ancho fijo sin posibilidad de redimensionar. Propuesta: columnas redimensionables. — **Reversibility:** reversible — diagnóstico.
- **D-12:** **Duplicado de "guardar dispositivos"**: elegir un origen personalizado en una sesión vs. buscar dispositivos guardados son dos flujos que parecen lo mismo pero están separados. **Decisión: un único flujo** "añadir origen" donde los dispositivos guardados son una sección/pestaña del mismo diálogo, e incluyendo una **zona de dispositivos desconectados** (dispositivos conocidos pero no presentes ahora, con su estado visible) dentro de la **misma ventana de orígenes**. — **Reversibility:** costly — unificar el flujo afecta a `source_picker.py`, `device_picker.py`, `main_window.py` y la tabla de sesiones; deshacerlo toca varios diálogos y su wiring.

### the agent's Discretion
El usuario delegó en el agente las áreas restantes con la única regla de no esconder nada:
- Detalle de la estructura interna del informe (agrupación por flujo con mapeo de zonas).
- Forma concreta de la evidencia visual (qué capturas, cuántas).
- Pesos concretos de la matriz impacto×esfuerzo.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap y requirements
- `.planning/ROADMAP.md` — Fase 1: goal, success criteria (4), `**UI hint:** yes`, `**Mode:** mvp`
- `.planning/REQUIREMENTS.md` — UI-01, UI-02, UI-03 (v1) y UI-04/UI-05 (v2, fuera de esta fase)
- `.planning/PROJECT.md` — Core value, Validated/Active requirements, constraints (no refactor core, i18n ES, cross-platform, mantener estética)

### Mapa del codebase (insumos de la auditoría)
- `.planning/codebase/ARCHITECTURE.md` — Layout de capas UI/core, responsabilidades de `MainWindow` y diálogos, patrones, anti-patterns (god object), errores de la UI
- `.planning/codebase/STRUCTURE.md` — Módulos `app/ui/` y `app/core/`, naming de widgets públicos (`btn_start`, `table`, `source_list`), ubicación de los diálogos
- `.planning/codebase/CONVENTIONS.md` — i18n (`tr()`), construcción programática de widgets (sin `.ui`), QSS centralizado en `theme.py`, patrones de diálogo
- `.planning/codebase/CONCERNS.md` — Gaps de tests de `main_window.py`, bugs UI conocidos (carrera `_cam_done`, rename con `/`), recomendaciones de PySide6

### Código fuente de la UI (territorio de la auditoría)
- `app/ui/main_window.py` — El god object: dashboard, sesiones, orígenes, post-ingesta (zona bajo la barra de progreso), menús, eliminación
- `app/ui/source_picker.py` — `SourcePickerDialog` (elegir origen personalizado vs. dispositivos guardados — el "duplicado" D-12)
- `app/ui/device_picker.py` — `DevicePickerDialog` (MTP), flujo de guardado de dispositivos
- `app/ui/ftp_picker.py` — `FtpPickerDialog` (perfil + escaneo)
- `app/ui/wifi_picker.py`, `app/ui/wifi_panel.py` — método WiFi / panel ShootInbox
- `app/ui/selective_dump.py` — `SelectiveDumpAssistant` (post-ingesta)
- `app/ui/project_wizard.py` — `ProjectWizard` (captura la descripción del proyecto — D-10)
- `app/ui/about_dialog.py` — `AboutDialog` (actualizaciones)
- `app/ui/theme.py` — Paleta/QSS (restricción estética)

### Tests
- `tests/test_e2e.py` — Conduce `MainWindow.start_ingest` offscreen; widgets públicos usados por tests
- `tests/test_source_picker.py`, `tests/test_selective_dump.py`, `tests/test_wifi_source.py` — Restricciones de compatibilidad de la fase posterior (no se implementa aquí)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `MainWindow` con widgets públicos (`btn_start`, `table`, `source_list`) — territorio de la auditoría y restricción para la fase posterior (tests dependen de estos nombres)
- `app/ui/theme.py` — paleta y QSS centralizados; cualquier propuesta estética debe respetar `@placeholder` tokens
- `SelectiveDumpAssistant` (`app/ui/selective_dump.py`) — patrón de asistente con su propio worker, referencia de cómo deberían sentirse los diálogos consistentes

### Established Patterns
- Construcción programática de widgets (sin `.ui` files) — la auditoría documenta widgets por nombre de atributo
- Diálogos `QDialog` con método `tr()` y `_build_ui()` — base para evaluar consistencia entre diálogos (heurística D-05)
- Strings UI en español literal via `tr()` — cualquier texto nuevo propuesto debe pasar por `tr()`

### Integration Points
- Ventana principal: menús + botones + zonas (dashboard, sesiones, orígenes, post-ingesta bajo la barra de progreso)
- Diálogos de origen: `SourcePickerDialog` / `DevicePickerDialog` / `FtpPickerDialog` / `WifiMethodDialog` — el "duplicado" D-12 vive entre estos
- Proyecto: `ProjectWizard` captura descripción que no se muestra después (D-10)

</code_context>

<specifics>
## Specific Ideas

- **D-12 detallado:** un único flujo "añadir origen" con los dispositivos guardados como sección/pestaña del mismo diálogo, y una zona de **dispositivos desconectados** visible en esa misma ventana de orígenes (no en la ventana principal).
- **D-09 detallado:** el control de eliminar no debe ser un "eliminar" genérico; por contexto (sesión, fuente, origen) puede necesitar presentación o ubicación distinta.
- **Regla del usuario:** "no esconder nada en la interfaz" — aplicar a toda propuesta del informe y del plan.
</specifics>

<deferred>
## Deferred Ideas

- **Implementación de reubicaciones (UI-04/UI-05)** — v2, fase posterior; debe partir del plan UI-03. Decisión explícita del usuario.
- **Refactor de `main_window.py`** (god object, logging, migraciones DB, bugs conocidos) — documentado en CONCERNS.md, fuera del alcance de esta iniciativa.
- **Rediseño estético completo** — fuera; se mantienen tema oscuro/claro y acentos existentes.
</deferred>

---

*Phase: 1-Auditoría UI y Plan de Reubicación*
*Context gathered: 2026-08-15*
