# Criterios de aceptación

## Funcionales
- [ ] `device_registry.upsert_known_device` funciona igual que `db.upsert_known_device`.
- [ ] `device_registry.get_dispositivo_for_device` retorna nombre correcto priorizando known_devices > device_settings.
- [ ] `device_registry.save_dispositivo_config` sanitiza nombre y persiste en device_settings.
- [ ] Añadir dispositivo MTP crea entrada en known_devices y se muestra en UI de dispositivos.
- [ ] Quitar dispositivo elimina entrada en known_devices y sesiones quedan consistentes.
- [ ] Renombrar nombre de cámara actualiza known_devices.last_camera, device_settings.nombre_dispositivo y sesiones.nombre_dispositivo.

## No funcionales
- [ ] No regresiones en ingesta.
- [ ] Imports de consumidores actualizados a device_registry.
- [ ] db.py mantiene compatibilidad retroactiva.

## Pruebas de verificación
- Reproducir flujo: AddSourceDialog → seleccionar dispositivo MTP → cambiar nombre → verificar persistencia.
- Reproducir flujo: Devices panel → eliminar dispositivo → verificar eliminación.
