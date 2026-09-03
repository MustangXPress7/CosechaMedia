# Inventario Consolidado — Acciones para Fases y Olas

**Estado**: Revisión completada — estructurado para planificación  
**Obs**: Fase 1.6.0: Añadir origen (prioridad), reorganizador, bugs. Verificación en 1.8.0

## FASE 1.6.0 — Añadir Origen + Reorganizador Footage + Bug Fixes

### Ola 1 — Mejoras Añadir Origen (PRIORIDAD ALTA)

**Bugs:**
1. WiFi desaparece al abrir QR (main_window.py)
2. Deseleccionar borra origen — debería inhabilitar (main_window.py)

**Cambios:**
1. Borrar botón "Escanear cámaras" (main_window.py)
2. Botón "Detectar" → ventana añadir origen (source_picker.py)
3. Detección cámara al seleccionar dispositivo sin nombre (main_window.py)

**Files pendientes:**
- `2026-09-02-cambios-fase-1-6-0-bugs-mejoras-origen-wifi.md`
- `1.6.0-mejoras-add-source-dialog.md`

| Accion | Archivo | Prioridad | Estado |
|--------|---------|-----------|--------|
| Menú dispositivo en "Ruta de origen" (QR/FTP) | main_window.py | Alta | ⏳ |
| Eliminar dispositivos guardados desconectados | db.py | Alta | ⏳ |
| Botón "Usar configuración" en dialog | source_picker.py | Media | ⏳ |
| Tabla plana de orígenes (sin pestañas) | source_picker.py | Alta | ⏳ |
| Mejorar detección cámara al añadir origen | main_window.py | Media | ⏳ |

### Ola 2 — Reorganizador Footage (REQ-06)
| Accion | Archivo | Prioridad |
|--------|---------|-----------|
| Crear `app/ui/reorganize_dialog.py` | NUEVO | Alta |
| Mover en sitio con metadata_engine | metadata_engine.py | Alta |

### Ola 3 — Bug Fixes
| Accion | Archivo | Prioridad |
|--------|---------|-----------|
| Limpiar `_stage_thread` en reset | main_window.py | Media |
| Verificar timers en detención | main_window.py | Media |

---

## FASE 1.7.0 — Registro devices + notificadores

### Ola 1 — Registro Dispositivos (REQ-09)
| Accion | Archivo | Prioridad |
|--------|---------|-----------|
| Tabla `known_devices` | db.py | Alta |
| Crear `device_registry.py` | NUEVO | Alta |

### Ola 2 — Notificadores (REQ-07)
| Accion | Archivo | Prioridad |
|--------|---------|-----------|
| Interfaz notificadores | notifications.py | Alta |
| Backend SMTP | notifications.py | Alta |
| Backend Telegram | notifications.py | Media |

---

## FASE 1.8.0 — WiFi SSID + verificación

### Ola 1 — WiFi SSID (REQ-08)
| Accion | Archivo | Prioridad |
|--------|---------|-----------|
| Servidor FTP embebido | shoot_inbox.py | Alta |
| Conectar a red OS | utils.py | Alta |

### Ola 2 — Verificación XXH64+ASC MHL
| Accion | Archivo | Prioridad |
|--------|---------|-----------|
| Crear `app/core/integrity.py` | NUEVO | Alta |
| Añadir columna `hash_policy` | db.py | Alta |
| Usar paquete `ascmhl` | deps | Media |
| Modificar `copy_verified` | ingestor.py | Alta |

---

## FASE 2.0 — Modo guiado + Bienvenida

### Ola 1 — Acciones rápidas (I-01)
| Accion | Prioridad |
|--------|-----------|
| Flujo guiado completo | Alta |

### Ola 2 — Pantalla bienvenida (I-13)
| Accion | Prioridad |
|--------|-----------|
| Primer arranque guiado | Alta |

---

## BACKLOG UI V2 — Pendientes

| ID | Punto | Estado |
|----|-------|--------|
| B-08 | Anillo de focus visible | ⏳ |
| B-12 | Auditoría estética formal | ⏳ |
| B-14 | Modo delicado por dispositivo | ⏳ |
| B-19 | Botones edición/origen a la derecha | ⏳ |

---

## Próximos Pasos

1. **Fase 1.6.0 Ola 1** (Añadir origen):
   - Ejecutar `/gsd-plan-phase 1.6.0` 
   - Fijar primero los bugs de WiFi y selección

2. **Fase 1.6.0 Ola 2** (Reorganizador):
   - Continuar con reorganizador footage

3. **Fase 1.7.0** (Device registry):
   - Tabla conocidos + notificadores

4. **Fase 1.8.0** (WiFi + verificación):
   - Servidor FTP embebido
   - XPH64+ASC MHL