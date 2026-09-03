---
title: "Bug MTP: Cuelgues al añadir dispositivo después de usarlo"
date: 2026-09-02
status: needs_investigation
priority: critical
---

# Bug MTP - Análisis

## Síntomas

- Al borrar un proyecto, la aplicación funciona normalmente
- Al añadir un dispositivo MTP (el mismo), aparecen cuelgues
- El bug desaparece al borrar el proyecto y volver a añadir

## Estado actual del código

El fix del thread-local COM está implementado en `app/core/mtp.py`:
```python
_manager_local = threading.local()  # línea 157

def _manager():
    dm = getattr(_manager_local, "device_manager", None)
    if dm is None:
        dm = comtypes.client.CreateObject(...)
        _manager_local.device_manager = dm
    return dm
```

## Posibles causas

### 1. Estado de threading persistente

Cuando se añade un dispositivo MTP:
1. Se crea una sesión con `cache_dir = mtp.device_cache_dir(device_id, device_folder)`
2. Se llama a `_stage_device_in_background()` que crea un QThread worker
3. El worker llama a `WpdBackend().stage()` → `_stage_session()`

Cuando se **borra el proyecto**:
1. `self.current_project_id = None`
2. `self.current_session_id = None`
3. Se recarga la lista de proyectos

**Problema potencial:** El thread-local `_manager_local` persiste entre operaciones!

```python
# Código actual - thread-local NO se reinicia al borrar proyecto
_manager_local = threading.local()  # Módulo - persiste siempre
```

### 2. Ingestores vivos (Los que más parezco)

En `main_window.py`:
```python
self._ingestors = []  # línea 178
self._wifi_ingestors = {}  # línea 197

def _reset_wifi_ingestors():
    for ing in self._wifi_ingestors.values():
        # ...
    self._wifi_ingestors = {}
```

**Pregunta:** ¿Se reinician los ingestors al borrar el proyecto?

Cuando se borra un proyecto:
- No se llama explícitamente a `reset_ingestors()`
- Los ingestors pueden estar con referencias a sesiones borradas

### 3. Caché en disco no se limpia

La caché de `device_cache/` NO se borra al borrar el proyecto.

**Sin embargo**, si la caché persiste pero el bug desaparece al borrar el proyecto, entonces NO es el problema de la caché.

## Verificación necesaria

### Test 1: Verificar que thread-local se reinicia

```python
# En el borrado de proyecto, forzar reinicio:
mtp._manager_local = threading.local()
```

### Test 2: Verificar que ingestors se limpian

Revisar si `delete_project` o `delete_all_projects` reinician `_ingestors` y `_wifi_ingestors`.

### Test 3: Verificar que watchers se detienen

Hay `FileSystemWatcher` con threads daemon. ¿Se limpian al borrar proyecto?

## Archivos involucrados

1. `app/core/mtp.py` - Thread-local COM manager
2. `app/ui/main_window.py` - Borrado de proyecto, estado `_ingestors`
3. `app/core/ingestor.py` - Ingestores con threads

## Hipótesis principal

El borrado de proyecto **NO reinicia** el estado de:
1. Thread-local COM manager (`_manager_local`)
2. Los ingestors (`_ingestors`, `_wifi_ingestors`)
3. Los watchers (`watchers`)

Cuando se añade el mismo dispositivo, algo en este estado persistente causa el cuelgue.

## Próximos pasos

1. Verificar si `_manager_local` necesita reiniciarse explícitamente
2. Verificar si `_ingestors` se limpian al borrar proyecto
3. Agregar logging para ver qué thread está usando `_manager()`
4. Test: borrar proyecto → añadir MTP → verificar estado COM