# FTP Mode Postponed

Fecha: 2026-09-07

## Decisión
El modo FTP queda aplazado hasta nuevo aviso.

## Motivo
- Inestabilidad con `QObject::setParent: Cannot set parent, new parent is in a different thread` al desconectar servidor.
- Aparición de dispositivos FTP en sección de dispositivos MTP desconectados.
- Re-aparición de perfiles en posiciones incorrectas tras re-registro.

## Alcance
- Se mantiene soporte de perfiles FTP en BBDD y en `AddSourceDialog` para selección inicial.
- Los dispositivos FTP no se renderizan en la sección de dispositivos desconectados/MTP.
- No se realizarán más cambios en el flujo FTP hasta que se revise la arquitectura de hilos y la gestión de backend.

## Tareas pendientes
- Revisar ciclo de vida de QThread en `_StageWorker` para FTP.
- Asegurar que `FtpBackend.is_reachable` no bloquee UI.
- Definir sección dedicada de FTP en AddSourceDialog.

## Estado
En espera.
