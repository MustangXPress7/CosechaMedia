# CosechaMedia

Herramienta de ingesta de tarjetas SD para producción audiovisual. Copia verificada (MD5), organización por cámara y fecha, generación de proxies y flujo de trabajo diseñado para volcados rápidos de rodaje.

## Características

- **Ingesta verificada**: copia de tarjetas SD con comprobación MD5 y eliminación de destinos corruptos.
- **Organización automática**: `Footage/<Cámara>/<Fecha>` con varios modos (cámara primero, fecha primero, solo cámara, sin subcarpetas).
- **Detección de cámaras**: escaneo de orígenes y renombrado manual de cámaras desconocidas.
- **Destinos de volcado múltiples**: reparto automático entre discos (cuando uno se llena, pasa al siguiente).
- **Proxies**: generación de proxies 720p/1080p de los clips de vídeo.
- **Post-ingesta**: formateo de orígenes (Windows) y apagado programado.
- **Temas y acentos**: tema oscuro/claro con acentos de color y fondo de trigo animado.
- **Internacionalización**: español e inglés (se cambia en el menú *Idioma*).
- **Actualizaciones automáticas**: comprobación vía GitHub Releases con verificación SHA-256.

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
