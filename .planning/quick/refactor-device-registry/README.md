# Inicio rápido – Refactor device registry

## Resumen
Separar gestión de dispositivos y nombres de cámara de `db.py` a `device_registry`.

## Comandos rápidos
```powershell
# Validar import del registry
python -c "from app.core.device_registry import upsert_known_device, list_known_devices; print('OK')"

# Listar consumidores a migrar
Select-String -Path "app\**\*.py" -Pattern "db\.upsert_known_device|db\.get_dispositivo_for_device|db\.save_dispositivo_config" | Select-Object FileName, LineNumber
```

## Próximo paso
Abrir `TASKS.md` y ejecutar tarea 4: migrar `app/ui/mixins/devices_mixin.py` a `device_registry`.

## Artefactos
- PLAN.md
- CONTEXT.md
- ACCEPTANCE.md
- TASKS.md
