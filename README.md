![CosechaMedia logo](https://i.imgur.com/tir6i57.png)

# CosechaMedia

SD card ingestion tool for audiovisual production. Verified copies (MD5), organization by camera and date, proxy generation, and a workflow designed for fast shoot dumps.

## Features

- **Verified ingest**: SD card copies with MD5 checks and removal of corrupted destinations.
- **Automatic organization**: `Footage/<Camera>/<Date>` with several modes (camera first, date first, camera only, no subfolders).
- **(WIP) Camera detection**: source scanning and manual renaming of unknown cameras.
- **Multiple dump destinations**: automatic distribution across drives (when one fills up, it moves to the next).
- **Proxies**: 720p/1080p proxy generation for video clips.
- **Post-ingest**: source formatting (Windows) and scheduled shutdown.
- **Themes and accents**: dark/light theme with color accents and animated wheat background.
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

**PolyForm Noncommercial License 1.0.0** (SPDX: `PolyForm-Noncommercial-1.0.0`).

You may use, copy and modify the code **for noncommercial purposes only**. Selling the program, charging for it, or using it for commercial gain is not allowed. See [LICENSE](LICENSE).

## Credits

**Developed by JMW Studio / Joan Ramon Viñas.**

This project was developed with AI assistance (language models) under the supervision of its author. The main stack is PySide6 (Qt), SQLite and FFmpeg.
