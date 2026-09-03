---
title: "Bug Fix Checklist - MTP Thread-local State Cleanup"
date: 2026-09-02
status: in_progress
---

# Checklist de fix para bug MTP

## Estado actual
- BUG IDENTIFICADO: Thread-local COM y estado de ingestors persiste al borrar proyecto
- RAÍZ: `app/core/mtp.py` thread-local no se reinicia, ingestors no se limpian

## Archivos a modificar

### 1. app/core/mtp.py
```python
# LÍNEA 153-157
_load_lock = threading.Lock()
_types_loaded = False
_manager_local = threading.local()  # <-- PERSISTE ENTRE OPERACIONES

# Necesario: Función para reiniciar el thread-local
def reset_thread_local():
    global _manager_local
    _manager_local = threading.local()
```

### 2. app/ui/main_window.py

#### Buscar `delete_current_project` (aprox línea 4355)
```python
def delete_current_project(self):
    # ... código existente ...
    
    # AGREGAR al final, antes de _create_default_project():
    self._reset_mtp_thread_local()
    self._reset_ingestors()
    self._stop_watchers()
```

#### NUEVO MÉTODO
```python
def _reset_mtp_thread_local(self):
    """Reinicia el thread-local COM del MTP para evitar referencias corruptas."""
    from app.core import mtp
    if hasattr(mtp, '_manager_local'):
        import threading
        mtp._manager_local = threading.local()

def _reset_ingestors(self):
    """Limpia los ingestors vivos."""
    for ing in self._ingestors[:]:
        ing.stop()
    self._ingestors = []
    self._wifi_ingestors = {}

def _stop_watchers(self):
    """Detiene los watchers de directorios."""
    for watcher in self.watchers:
        watcher.stop()
    self.watchers.clear()
```

### 3. Tests a actualizar

#### tests/test_mtp.py
- [ ] Agregar test `test_thread_local_reset`
- [ ] Verificar que el thread-local se reinicia correctamente

#### tests/test_main_window.py
- [ ] Agregar test para `delete_current_project` reiniciando estado

## Preguntas pendientes

1. ¿El `CoUninitialize` debe llamarse antes de reiniciar thread-local?
2. ¿Los ingestors deben llamarse `.stop()` explícitamente?
3. ¿Los watchers tienen método `.stop()`?

## Verificación

1. Borrar proyecto
2. Añadir dispositivo MTP → verificar que NO cuelga
3. Verificar que los tests pasan