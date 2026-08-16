# Backlog de Refinamiento UI (v2.1)

Este documento registra la deuda técnica y de UX identificada tras la implementación de la reubicación de controles (v2). Estos ítems deben resolverse antes de dar por avanzar a nuevas funcionalidades.

## 🔴 Prioridad Alta (Bloqueantes de UX / Errores de Flujo)

| ID | Punto | Descripción | Acción Técnica Sugerida | Estado |
|----|--------|-------------|-------------------------|--------|
| B-01 | **Ubicación Volcado Selectivo** | El volcado selectivo está en "Post-ingesta", pero es una acción de *pre-ingesta* (filtrar archivos por fecha antes de copiar). | Mover el botón `btn_selective_dump` al flujo de preparación de ingesta. | ✅ Hecho |
| B-02 | **Nombre de Origen en Sesión** | Las sesiones muestran el ID/ruta técnica pero no el nombre legible del origen. | Modificar la carga de la tabla de sesiones para incluir el nombre del origen desde la DB. | ✅ Hecho |
| B-03 | **Visibilidad Descripción Proyecto** | La descripción del proyecto no es visible o no se refleja correctamente en la UI. | Verificar binding de `desc_input` y su persistencia/carga desde la base de datos. | ✅ Hecho |

## 🟡 Prioridad Media (Usabilidad y Organización)

| ID | Punto | Descripción | Acción Técnica Sugerida | Estado |
|----|--------|-------------|-------------------------|--------|
| B-04 | **Caos en "Añadir Origen"** | El diálogo unificado es redundante, repite opciones y la gestión de "Eliminar" está escondida en una pestaña específica. | Rediseñar la jerarquía de `SourcePickerDialog`. Centralizar la administración de orígenes y simplificar el flujo de añadir. | ✅ Hecho |
| B-05 | **Estética Botón Eliminar** | El botón de eliminar origen en la fila principal es visualmente disruptivo/feo. | Migrar la acción a un menú contextual (`QMenu`) sobre la fila o integrarlo en la edición del origen. | ✅ Hecho |
| B-06 | **Expansión de Tabla Orígenes** | La tabla de orígenes no tiene un límite de expansión claro o presenta saltos bruscos de tamaño. | Implementar `QScrollArea` con límites definidos o ajustar el `sizePolicy` para evitar saltos. | ✅ Hecho |

## 🟢 Prioridad Baja (Pulido Visual)

| ID | Punto | Descripción | Acción Técnica Sugerida | Estado |
|----|--------|-------------|-------------------------|--------|
| B-07 | **Temas en WiFi (PairDrop)** | El diálogo de WiFi solo soporta tema oscuro, ignorando la configuración global. | Eliminar colores hardcodeados en `WifiMethodDialog` y vincularlo al sistema de temas de `app/ui/theme.py`. | ✅ Hecho |

---
**Estado:** Completado (B-01 a B-07). Ejecutado en sesión de cierre v2.1: suite completa 223 tests OK (skipped=3).
