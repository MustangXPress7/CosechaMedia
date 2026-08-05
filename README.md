![Logo de CosechaMedia](https://i.imgur.com/tir6i57.png)

# CosechaMedia

Herramienta de ingesta de tarjetas SD para producción audiovisual. Copia verificada (MD5), organización por cámara y fecha, generación de proxies y flujo de trabajo diseñado para volcados rápidos de rodaje.

## Características

- **Ingesta verificada**: copia de tarjetas SD con comprobación MD5 y eliminación de destinos corruptos.
- **Organización automática**: `Footage/<Cámara>/<Fecha>` con varios modos (cámara primero, fecha primero, solo cámara, sin subcarpetas).
- **(WIP) Detección de cámaras**: escaneo de orígenes y renombrado manual de cámaras desconocidas.
- **Destinos de volcado múltiples**: reparto automático entre discos (cuando uno se llena, pasa al siguiente).
- **Proxies**: generación de proxies 720p/1080p de los clips de vídeo.
- **Post-ingesta**: formateo de orígenes (Windows) y apagado programado.
- **Temas y acentos**: tema oscuro/claro con acentos de color y fondo de trigo animado.
- **Internacionalización**: español e inglés (se cambia en el menú *Idioma*).
- **Actualizaciones automáticas**: comprobación vía GitHub Releases con verificación SHA-256.
- **Ingesta desde móviles y cámaras**: importa por USB (MTP), por WiFi con recepción por código QR (PairDrop, sin instalar nada en el móvil) o por servidor FTP en el dispositivo, con sincronización incremental y reescaneo automático.

![UI de CosechaMedia](https://i.imgur.com/wn2ZprQ.png)

## Requisitos

- **Windows / macOS / Linux**
- FFmpeg (`ffprobe` y `ffmpeg` en el `PATH`) para extraer metadatos de vídeo y generar proxies.
- Python 3.11 (solo para compilar desde el código; los usuarios solo necesitan el ejecutable).

## Descarga

Las versiones compiladas se publican en **GitHub Releases**:

<https://github.com/MustangXPress7/CosechaMedia/releases>

- Windows → `CosechaMedia-windows-x86_64.exe`
- macOS → `CosechaMedia-macos.app.zip` (contiene la aplicación `.app`)
- Linux → `CosechaMedia-linux-x86_64`

La aplicación comprueba actualizaciones al inicio (ajustable en *Ayuda → Búsqueda de actualizaciones…*) y, cuando hay una versión nueva, la descarga, verifica su SHA-256 y se instala sola al reiniciar.

## Ingesta desde móviles y cámaras

Puedes importar archivos (p. ej. la carpeta `DCIM`) directamente desde un móvil o cámara, además de desde tarjetas SD.

- **Por USB (MTP)**: conecta el dispositivo por cable y usa el menú *Detección → Importar desde dispositivo (MTP)…*. Elige la carpeta a importar y CosechaMedia la copia a la caché local de forma incremental (solo archivos nuevos o cambiados).
- **Por WiFi**: pulsa el botón *WiFi…* y elige entre *PairDrop* (recomendado) o *FTP Clásico*.

Una vez registrado el origen, la app reescanea el dispositivo automáticamente (cada minuto si está disponible) y actualiza la copia local. La ingesta posterior hacia el proyecto funciona igual que con una tarjeta.

### Recepción por QR (PairDrop, sin instalar nada en el móvil)

1. En CosechaMedia pulsa *WiFi…* → *PairDrop*. Se abre el panel con el servidor y un código QR por persona.
2. Añade una persona (p. ej. el nombre del actor) y escanea su QR con el móvil.
3. El móvil se conecta al ordenador (misma red WiFi) y muestra una página para elegir los archivos a enviar.
4. Los archivos caen en la carpeta *inbox* (una subcarpeta por persona y fecha) y CosechaMedia los registra al momento. Usa *Iniciar Ingesta* para volcarlos al proyecto.

> El móvil y el ordenador deben estar en la misma red WiFi; la primera vez Windows puede pedir permiso de red para el servidor.

### Aplicaciones FTP recomendadas

- **Android → [Primitive FTPd](https://github.com/wolpi/prim-ftpd)** (gratis, código abierto; F-Droid o GitHub — ya no está en Google Play). Puerto por defecto `2221`, usuario por defecto `user` (sin contraseña). Mantiene la pantalla encendida mientras el servidor está activo.
- **iOS → GoFTP Server** (gratis, App Store).

### Pasos (WiFi/FTP)

1. En CosechaMedia pulsa *WiFi…* → *FTP Clásico*.
2. En el móvil, instala Primitive FTPd (Android) o GoFTP Server (iOS) y pulsa *Iniciar*. Anota la dirección (`ftp://IP:puerto`), el usuario y la contraseña que muestra la app.
3. En CosechaMedia usa *Detectar en la red…* para encontrar el servidor automáticamente (o introduce la IP a mano).
4. Rellena usuario y contraseña y pulsa *Conectar*.
5. Elige la carpeta (p. ej. `DCIM`) y pulsa *Aceptar*.

> La transferencia por FTP es en texto plano (red local de rodaje). Mantén la pantalla del dispositivo encendida durante la transferencia. Si aparece *425 Can't open passive connection*, la app cambia sola al modo activo (también puedes desmarcar *Modo pasivo*).

## Compilación

### Windows (local)

```
Compilar.bat
```

Genera `dist\CosechaMedia.exe`.

### Windows / macOS / Linux (GitHub Actions)

El workflow [`.github/workflows/build.yml`](.github/workflows/build.yml) compila las tres plataformas y publica los binarios en una Release automáticamente. Solo hay que empujar un tag con prefijo `v`:

```
git tag v1.0.0
git push origin v1.0.0
```

## Estructura del proyecto

```
app/
  core/          Lógica de negocio (ingesta, metadatos, watcher, updater, DB...)
  ui/            Interfaz (ventana principal, asistente, diálogo "Acerca de", temas)
  i18n/          Catálogos de traducción (.ts / .qm)
  sounds/        Sonidos de notificación
tools/           Scripts de internacionalización
tests/           Pruebas unitarias y end-to-end (offscreen)
main.spec        Configuración de PyInstaller
```

## Licencia

**PolyForm Noncommercial License 1.0.0** (SPDX: `PolyForm-Noncommercial-1.0.0`).

Puedes usar, copiar y modificar el código **solo con fines no comerciales**. No está permitido vender el programa, cobrar por él ni usarlo para obtener beneficio económico. Ver [LICENSE](LICENSE).

## Créditos

**Desarrollado por JMW Studio / Joan Ramon Viñas.**

Este proyecto fue desarrollado con asistencia de IA (modelos de lenguaje) bajo la supervisión de su autor. El stack principal es PySide6 (Qt), SQLite y FFmpeg.
