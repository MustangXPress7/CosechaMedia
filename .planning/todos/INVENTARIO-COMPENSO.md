# Inventario Consolidado — Acciones para Fases y Olas

**Estado**: Revisión completada — estructurado para planificación  
**Obs**: Reasignaciones 2026-09-10: DeviceRegistry → 1.6.0 (implementado, 01.6.0-07); notificadores → 1.8.0; verificación XXH64+ASC MHL → 1.7.0; bienvenida → 1.7.0; modo guiado + ideas sueltas → 2.0

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

## FASE 1.7.0 — Pulido visual + Configuración de proyecto + Verificación avanzada

### Ola 1 — Verificación XXH64+ASC MHL (R-05, reubicado desde 1.8.0)
| Accion | Archivo | Prioridad |
|--------|---------|-----------|
| Crear `app/core/integrity.py` | NUEVO | Alta |
| Añadir columna `hash_policy` | db.py | Alta |
| Usar paquete `ascmhl` | deps | Media |
| Modificar `copy_verified` | ingestor.py | Alta |

### Ola 2 — Registro Dispositivos (REQ-09) ✅ Implementado en 1.6.0 (01.6.0-07)
| Accion | Archivo | Prioridad |
|--------|---------|-----------|
| Tabla `known_devices` | db.py | ✅ |
| Crear `device_registry.py` | NUEVO | ✅ |

> Nota: los **notificadores (REQ-07)** pasaron a la Fase 1.8.0 (01.8.0-01).

---

## FASE 1.8.0 — Notificadores + Volcado por orden + Reorganizador avanzado + WiFi SSID

### Ola 1 — Notificadores (REQ-07, reubicado desde 1.7.0)
| Accion | Archivo | Prioridad |
|--------|---------|-----------|
| Interfaz notificadores | notifications.py | Alta |
| Backend SMTP | notifications.py | Alta |
| Backend Telegram | notifications.py | Media |

### Ola 2 — WiFi SSID (REQ-08)
| Accion | Archivo | Prioridad |
|--------|---------|-----------|
| Servidor FTP embebido | shoot_inbox.py | Alta |
| Conectar a red OS | utils.py | Alta |

### Ola 3 — Volcado por orden de dispositivo + Reorganizador (reubicados desde 1.7.0)
| Accion | Prioridad |
|--------|-----------|
| Volcado por orden de dispositivo (un lector rotando tarjetas) | Alta |
| Reorganizador con filtros ffprobe (resolución, códec, fps, duración) | Media |
| Mejora de interfaz y funciones de ReorganizeDialog (selección/previsualización) | Media |

---

## FASE 2.0 — Modo guiado con plantillas + ideas sin conexión

### Ola 1 — Modo guiado (I-01)
| Accion | Prioridad |
|--------|-----------|
| Flujo guiado completo | Alta |

### Ola 2 — Ideas incorporadas a 2.0 (2026-09-10)
| Idea | Prioridad |
|------|-----------|
| I-24 scripts/webhooks post-ingesta (desde 1.9.0) | Media |
| I-02 destinos "fallback"/servidor | Media |
| I-04 contenedores por tipo de archivo | Media |
| I-21 menú contextual "Copiar a CosechaMedia…" | Media |
| I-25 health check del soporte | Media |

> Nota: la **pantalla de bienvenida (I-13)** ya no está en 2.0 — se implementa en la Fase 1.7.0 (01.7.0-04).

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

1. **Fase 1.7.0** (siguiente roadmap):
   - Ejecutar `/gsd-plan-phase 1.7.0`
   - Pulido visual UI, configuración de proyecto (plantillas/bienvenida/orígenes), verificación XXH64+ASC MHL, volcado selectivo global (ID-01/ID-02)

2. **Fase 1.8.0** (después):
   - Notificadores, volcado por orden, reorganizador avanzado, WiFi SSID

3. **Fase 1.9.0**:
   - Velocidad de copia, resume robusto, reportes con marca