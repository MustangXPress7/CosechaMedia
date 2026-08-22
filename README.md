![CosechaMedia logo](https://i.imgur.com/tir6i57.png)

<p align="center">
  <a href="#english"><b>English</b></a> ·
  <a href="#espanol">Español</a>
</p>

---

<a name="english"></a>
# CosechaMedia

SD card ingestion tool for audiovisual production. Verified copies (MD5), organization by camera and date, proxy generation, and a workflow designed for fast shoot dumps.

## Features

- **Verified ingest**: SD card copies with MD5 checks and removal of corrupted destinations.
- **Automatic organization**: `Footage/<Camera>/<Date>` with several modes (camera first, date first, camera only, no subfolders).
- **Device detection**: automatic source scanning with persistent device names (set when registering the source).
- **Selective dump per session**: dump all content, a date interval, or only the days since the last dump (configurable window, 1 day by default), session by session — with an assistant that scans the card, groups files by shooting day, and copies verified.
- **Flexible shoot dates**: taken automatically from video metadata or set manually per project, with per-device overrides for cards without reliable metadata.
- **One-step projects**: the creation wizard collects every project setting up front (advanced options collapsed by default).
- **Multiple dump destinations**: automatic distribution across drives (when one fills up, it moves to the next).
- **Proxies**: 720p/1080p proxy generation for video clips.
- **Post-ingest**: CSV reports (card contents before dumping, integrity after ingest), source formatting (Windows), and scheduled shutdown.
- **Themes and accents**: dark/light theme with color accents, tintable SVG icons that follow the accent, and animated wheat background.
- **Internationalization**: Spanish and English (switchable from the *Language* menu).
- **Automatic updates**: checks via GitHub Releases with SHA-256 verification.
- **Ingest from phones and cameras**: import over USB (MTP), over WiFi with QR-code reception (PairDrop, nothing to install on the phone), or via an FTP server on the device, with incremental sync and automatic rescanning.

![CosechaMedia UI](https://i.imgur.com/wn2ZprQ.png)

## Requirements

- **Windows / macOS / Linux**
- FFmpeg (`ffprobe` and `ffmpeg` in your `PATH`) to extract video metadata and generate proxies.
- Python 3.11 (only to build from source; end users only need the executable).

## Download

Compiled releases are published on **GitHub Releases**:

<https://github.com/MustangXPress7/CosechaMedia/releases>

- Windows → `CosechaMedia-windows-x86_64.exe`
- macOS → `CosechaMedia-macos.app.zip` (contains the `.app` bundle)
- Linux → `CosechaMedia-linux-x86_64`

The app checks for updates on startup (adjustable under *Help → Check for updates…*) and, when a new version is available, downloads it, verifies its SHA-256, and installs itself on restart.

Binaries carry no developer-certificate signature (macOS builds get an ad-hoc signature); see [SIGNING](docs/SIGNING.md) for what that means and how to open the app on macOS the first time.

### Install via Homebrew (macOS, Apple Silicon)

```
brew tap MustangXPress7/tap
brew install --cask --no-quarantine MustangXPress7/tap/cosechamedia
```

Details, updates and current limitations (Apple Silicon only): see [HOMEBREW](docs/HOMEBREW.md).

## Ingest from phones and cameras

You can import files (e.g. the `DCIM` folder) straight from a phone or camera, in addition to SD cards.

- **Over USB (MTP)**: connect the device with a cable and use the *Detection → Import from device (MTP)…* menu. Pick the folder to import and CosechaMedia copies it to the local cache incrementally (only new or changed files).
- **Over WiFi**: press the *WiFi…* button and choose between *PairDrop* (recommended) or *Classic FTP*.

Once the source is registered, the app automatically rescans the device (every minute if available) and updates the local copy. Subsequent ingestion into the project works the same as with a card.

### QR reception (PairDrop, nothing to install on the phone)

1. In CosechaMedia press *WiFi…* → *PairDrop*. The panel opens with the server and one QR code per person.
2. Add a person (e.g. the actor's name or "Joan's phone"). Scan their QR with the phone.
3. The phone connects to the computer (same WiFi network) and shows a page to pick the files to send. If you check *Send a whole folder*, the phone can select a whole folder (on Android/Chrome).
4. Each person is registered as their own ingest source (a session). Files land in their local cache (`data/inbox/<person>`) and CosechaMedia dumps them to the project on the fly, with verified copies and the configured organization. When the ingest finishes, the cache is cleaned automatically.

> The phone and the computer must be on the same WiFi network; the first time, Windows may ask for network permission for the server.

### Recommended FTP apps

- **Android → [Primitive FTPd](https://github.com/wolpi/prim-ftpd)** (free, open source; F-Droid or GitHub — no longer on Google Play). Default port `2221`, default user `user` (no password). Keeps the screen on while the server is active.
- **iOS → GoFTP Server** (free, App Store).

### Steps (WiFi/FTP)

1. In CosechaMedia press *WiFi…* → *Classic FTP*.
2. On the phone, install Primitive FTPd (Android) or GoFTP Server (iOS) and press *Start*. Note the address (`ftp://IP:port`), the user and the password shown by the app.
3. In CosechaMedia use *Detect on network…* to find the server automatically (or enter the IP manually).
4. Fill in the user and password and press *Connect*.
5. Pick the folder (e.g. `DCIM`) and press *OK*.

> FTP transfers are plain text (local shoot network). Keep the device screen on during the transfer. If *425 Can't open passive connection* appears, the app automatically switches to active mode (you can also uncheck *Passive mode*).

## Building

### Windows (local)

```
Compilar.bat
```

Produces `dist\CosechaMedia.exe`.

### Windows / macOS / Linux (GitHub Actions)

The [`.github/workflows/build.yml`](.github/workflows/build.yml) workflow builds all three platforms and publishes the binaries to a Release automatically. Just push a tag with a `v` prefix:

```
git tag v1.0.0
git push origin v1.0.0
```

## Project structure

```
app/
  core/          Business logic (ingest, metadata, watcher, updater, DB...)
  ui/            Interface (main window, wizard, "About" dialog, themes)
  i18n/          Translation catalogs (.ts / .qm)
  sounds/        Notification sounds
tools/           Internationalization scripts
tests/           Unit and end-to-end tests (offscreen)
main.spec        PyInstaller configuration
```

## License

**GNU General Public License v3.0 or later** (SPDX: `GPL-3.0-or-later`).

Free software: you can use, study, modify and redistribute it under the terms of the [GNU GPLv3](https://www.gnu.org/licenses/gpl-3.0.html), either version 3 or (at your option) any later version. Contributions are welcome under the same terms. See [LICENSE](LICENSE).

## Credits

**Developed by JMW Studio / Joan Ramon Viñas.**

This project was developed with AI assistance (language models) under the supervision of its author. The main stack is PySide6 (Qt), SQLite and FFmpeg.

---

<a name="espanol"></a>
# CosechaMedia

Herramienta de ingesta de tarjetas SD para producción audiovisual. Copia verificada (MD5), organización por cámara y fecha, generación de proxies y flujo de trabajo diseñado para volcados rápidos de rodaje.

## Características

- **Ingesta verificada**: copia de tarjetas SD con comprobación MD5 y eliminación de destinos corruptos.
- **Organización automática**: `Footage/<Cámara>/<Fecha>` con varios modos (cámara primero, fecha primero, solo cámara, sin subcarpetas).
- **Detección de dispositivos**: escaneo automático de orígenes con nombres de dispositivo persistentes (se fijan al registrar el origen).
- **Volcado selectivo por sesión**: vuelca todo el contenido, un intervalo de días o solo los días transcurridos desde el último volcado (ventana configurable, 1 día por defecto), sesión a sesión, con un asistente que escanea la tarjeta, agrupa por día de rodaje y copia verificado.
- **Fechas de rodaje flexibles**: tomadas automáticamente de los metadatos de vídeo o fijadas a mano por proyecto, con excepciones por dispositivo para tarjetas sin metadatos fiables.
- **Proyectos en un solo paso**: el asistente de creación recoge todos los ajustes del proyecto desde el principio (opciones avanzadas plegadas por defecto).
- **Destinos de volcado múltiples**: reparto automático entre discos (cuando uno se llena, pasa al siguiente).
- **Proxies**: generación de proxies 720p/1080p de los clips de vídeo.
- **Post-ingesta**: informes CSV (contenido de la tarjeta antes de volcar, integridad tras la ingesta), formateo de orígenes (Windows) y apagado programado.
- **Temas y acentos**: tema oscuro/claro con acentos de color, iconos SVG tintables que siguen al acento y fondo de trigo animado.
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

Los binarios no llevan firma de certificado de desarrollador (las builds de macOS reciben una firma ad-hoc); consulta [SIGNING](docs/SIGNING.md) para saber qué implica y cómo abrir la app en macOS la primera vez.

### Instalar con Homebrew (macOS, Apple Silicon)

```
brew tap MustangXPress7/tap
brew install --cask --no-quarantine MustangXPress7/tap/cosechamedia
```

Detalles, actualizaciones y limitaciones actuales (solo Apple Silicon): consulta [HOMEBREW](docs/HOMEBREW.md).

## Ingesta desde móviles y cámaras

Puedes importar archivos (p. ej. la carpeta `DCIM`) directamente desde un móvil o cámara, además de desde tarjetas SD.

- **Por USB (MTP)**: conecta el dispositivo por cable y usa el menú *Detección → Importar desde dispositivo (MTP)…*. Elige la carpeta a importar y CosechaMedia la copia a la caché local de forma incremental (solo archivos nuevos o cambiados).
- **Por WiFi**: pulsa el botón *WiFi…* y elige entre *PairDrop* (recomendado) o *FTP Clásico*.

Una vez registrado el origen, la app reescanea el dispositivo automáticamente (cada minuto si está disponible) y actualiza la copia local. La ingesta posterior hacia el proyecto funciona igual que con una tarjeta.

### Recepción por QR (PairDrop, sin instalar nada en el móvil)

1. En CosechaMedia pulsa *WiFi…* → *PairDrop*. Se abre el panel con el servidor y un código QR por persona.
2. Añade una persona (p. ej. el nombre del actor o "Móvil de Joan"). Escanea su QR con el móvil.
3. El móvil se conecta al ordenador (misma red WiFi) y muestra una página para elegir los archivos a enviar. Si marcas *Enviar una carpeta entera*, el móvil podrá seleccionar una carpeta completa (en Android/Chrome).
4. Cada persona se registra como un origen de ingesta propio (una sesión). Los archivos caen en su caché local (`data/inbox/<persona>`) y CosechaMedia los vuelca al proyecto al momento, con copia verificada y la organización configurada. Cuando la ingesta termina, la caché se limpia sola.

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

**GNU General Public License v3.0 o posterior** (SPDX: `GPL-3.0-or-later`).

Software libre: puedes usarlo, estudiarlo, modificarlo y redistribuirlo bajo los términos de la [GNU GPLv3](https://www.gnu.org/licenses/gpl-3.0.html), en su versión 3 o (a tu elección) cualquier versión posterior. Las contribuciones son bienvenidas bajo la misma licencia. Consulta [LICENSE](LICENSE).

## Créditos

**Desarrollado por JMW Studio / Joan Ramon Viñas.**

Este proyecto fue desarrollado con asistencia de IA (modelos de lenguaje) bajo la supervisión de su autor. El stack principal es PySide6 (Qt), SQLite y FFmpeg.
