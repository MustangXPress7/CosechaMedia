# Milestones

## v1.5.0 Consolidación y bugs del flujo (Shipped: 2026-08-29)

**Phases completed:** 2 phases, 9 plans, 19 tasks

**Key accomplishments:**

- Inventario de widgets de las 4 zonas de la UI (A dashboard, B pickers, C asistentes/paneles, D post-ingesta) con 121 filas de controles citados archivo:línea, más 8 capturas offscreen de evidencia visual y el baseline git de los archivos pre-modificados
- Informe consolidado de hallazgos UI (01-HALLAZGOS.md): 7 hallazgos H-01..H-07 con citas archivo:línea verificadas (138 citas), severidad, anclas D-07..D-12 y cobertura total del inventario (121 filas, conteo verificado)
- Plan de reubicación priorizado con matriz de puntuación D-06 (17 ítems R-01..R-17 en bandas P1=5/P2=11/P3=1, trazabilidad 7/7 hallazgos, strings nuevos ES para v2) y gate de cero código con registro REVISA OPERADOR por un hang preexistente de la suite
- Aprobación del operador registrada en el plan de reubicación: bandas P1/P2/P3 y orden aprobados ('Apruebo bandas y orden'), 5 ítems destructivos D-09 confirmados con orden de ejecución dentro de su flujo ('Confirmo los 5 destructivos'), discrepancia D-12 resuelta ('Mantener banda de la fórmula (P2)') — fase 01 cerrada con el plan como contrato de entrada de v2 (UI-04/UI-05)
- copy_verified calcula el hash MD5 del origen una sola vez (pase stream-through) y lo devuelve, eliminando la relectura del destino completo que duplicaba el I/O (R4 / D-03), con la semántica de borrado de destino corrupto conservada y los tests de mismatch reescritos para el nuevo mecanismo.
- Inventario watcher persistido en SQLite con veredictos copied/filtered/errored, filter_key para identidad de ventana, y predicado should_skip compartido eliminando cap 10k

---
