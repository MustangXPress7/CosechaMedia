# Phase 1: Auditoría UI y Plan de Reubicación - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-15
**Phase:** 1-Auditoría UI y Plan de Reubicación
**Areas discussed:** Organización de la auditoría, Evidencia visual, Criterios explícitos, Priorización formal, Entregable consolidado, Hallazgos confirmados (post-ingesta, sesiones, eliminar, descripción, tabla orígenes, duplicado guardar dispositivos)

---

## Organización de la auditoría

| Option | Description | Selected |
|--------|-------------|----------|
| Organización por flujo | Auditar por flujo del operador (conectar → ingestar → formatear → reorganizar) en vez de por zona estática; cada zona se cubre dentro de su flujo | ✓ (agente, delegado) |
| (zona estática) | Auditar por zona estática (dashboard, pickers, asistentes, post-ingesta) | |

**User's choice:** Delegó en el agente ("lo demás me da igual mientras obvio no escondas nada en la interfaz").
**Notes:** Se eligió por flujo del operador con cobertura íntegra de todas las zonas (D-01). Regla transversal: no esconder nada (D-03).

---

## Evidencia visual

| Option | Description | Selected |
|--------|-------------|----------|
| Evidencia visual | Complementar la lectura de widgets con inspección visual (ejecutar app / capturas offscreen) | ✓ (agente, delegado) |

**User's choice:** Delegó en el agente.
**Notes:** D-04 — lectura de widgets + inspección visual (capturas offscreen) como evidencia de posición y jerarquía reales.

---

## Criterios explícitos

| Option | Description | Selected |
|--------|-------------|----------|
| Criterios explícitos | Fijar heurísticas (frecuencia de uso, consistencia entre diálogos, contexto de acción, distancia de ratón) para justificar cada hallazgo | ✓ (agente, delegado) |

**User's choice:** Delegó en el agente.
**Notes:** D-05 — heurísticas explícitas; nada se marca como problema sin criterio.

---

## Priorización formal

| Option | Description | Selected |
|--------|-------------|----------|
| Priorización formal | Matriz impacto×esfuerzo + riesgo (tests, i18n, estética) | ✓ (agente, delegado) |

**User's choice:** Delegó en el agente.
**Notes:** D-06.

---

## Entregable consolidado

| Option | Description | Selected |
|--------|-------------|----------|
| Entregable consolidado | Un informe consolidado (hallazgos por zona) + un plan de reubicación aparte | ✓ |
| (informes separados por zona) | Un informe por zona + plan global | |

**User's choice:** "Entregable consolidado" (seleccionado explícitamente).
**Notes:** D-02 — un único informe de hallazgos + plan separado.

---

## Hallazgos confirmados por el usuario

**Zona post-ingesta** (debajo de la barra de progreso):
> "Siento que en las partes de post-ingesta (lo que vive debajo de la barra de progreso) está mal ubicado o queda más secundario... Pero esa zona está muy desordenada."

**Sesiones:**
> "Las sesiones, cuando más ahondas, más se come la interfaz hacia la derecha y se podría jugar más hacia abajo."

**Botones de eliminar:**
> "Los botones de eliminar también están mal puestos."

**Descripción del proyecto:**
> "En cada proyecto se añade una descripción que luego no aparece en ningún puesto."

**Tabla de orígenes:**
> "La tabla de orígenes también me gustaría que se pudiera mover el tamaño de las columnas."

**Duplicado de guardar dispositivos:**
> "A nivel menús me siento que hay dos 'duplicados' en cuanto a guardar dispositivos: cuando seleccionas un origen personalizado en una sesión y cuando buscas los dispositivos guardados. Podría ser lo mismo pero está separado."

**Aclaración D-12:** el usuario eligió la opción (a) — un único flujo "añadir origen" con dispositivos guardados como sección del mismo diálogo, más una zona de **dispositivos desconectados** en la misma ventana de orígenes.

**Aclaración D-09:** el usuario indicó que el problema del eliminar es *ambas* (ubicación y presentación); depende del contexto debería ser de diferente manera que ahora.

---

## the agent's Discretion

- Estructura interna del informe (agrupación por flujo con mapeo de zonas).
- Forma concreta de la evidencia visual (qué capturas, cuántas).
- Pesos concretos de la matriz impacto×esfuerzo.

## Deferred Ideas

- Implementación de reubicaciones (UI-04/UI-05) — v2, fase posterior.
- Refactor de `main_window.py` (god object, logging, migraciones, bugs) — fuera de alcance.
- Rediseño estético completo — fuera; se mantienen tema y acentos.
