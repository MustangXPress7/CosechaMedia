# Distribución vía Homebrew (macOS)

CosechaMedia se puede instalar y actualizar en macOS con dos comandos de Homebrew: el cask descarga la app desde GitHub Releases, la deja en `/Applications` y resuelve `ffmpeg`/`ffprobe` automáticamente como dependencia declarada. Este documento describe el estado del soporte, cómo instalarlo como usuario, cómo publicar el tap del proyecto y qué tocar en cada release.

Aviso honesto de estado beta: de momento **solo Apple Silicon**, sin notarización de Apple y con el hash del asset aún sin fijar. Detalles abajo.

## Estado actual y limitaciones

- **Solo Apple Silicon, temporalmente.** Los assets actuales de CI se generan en `macos-latest` (Apple Silicon); no hay builds para Intel ni multi-arquitectura. El cask lo refleja con `depends_on arch: :arm64`; retira esa línea cuando existan builds multi-arquitectura (fuera de alcance hoy).
- **Sin Developer ID ni notarización.** Las builds de macOS llevan firma ad-hoc, así que la instalación recomendada usa `--no-quarantine` para evitar la fricción de Gatekeeper en la primera apertura. Los detalles técnicos de firma e integridad están en [SIGNING](SIGNING.md).
- **Hash sin fijar mientras no exista una release estable.** El cask lleva `sha256 :no_check` con un comentario que explica cómo fijarlo. Desde la primera release estable hay que calcular el SHA-256 real del asset y actualizarlo siguiendo la sección «Actualizar el cask en cada release»; mientras tanto, la integridad descansa en TLS y en la procedencia de GitHub Releases.

## Instalación (usuarios)

Requisito previo: tener [Homebrew](https://brew.sh) instalado. Después:

```
brew tap MustangXPress7/tap
brew install --cask --no-quarantine MustangXPress7/tap/cosechamedia
```

- El primer comando registra el tap. El formato corto `usuario/tap` funciona SOLO si el repositorio se llama exactamente `homebrew-tap`: Homebrew lo resuelve siempre como `github.com/MustangXPress7/homebrew-tap`.
- El segundo comando descarga el zip de la release que corresponde a la versión del cask, descomprime el bundle y mueve `CosechaMedia.app` a `/Applications`. Si faltaban, instala también `ffmpeg` y `ffprobe` como fórmula de Homebrew (dependencia declarada del cask), dejándolos disponibles en el `PATH`, que es exactamente donde la app espera encontrarlos.
- `--no-quarantine` evita que brew marque la app con el atributo de cuarentena que Gatekeeper exigiría desbloquear en la primera apertura, dado que la app no está notarizada. Si prefieres instalar sin esa opción y aceptar el aviso de Gatekeeper una vez, el procedimiento manual está en [SIGNING](SIGNING.md).
- La app incluye su propio autoactualizador, pero en instalaciones vía brew conviene actualizar con `brew upgrade --cask cosechamedia` para que brew no se desincronice de lo instalado en `/Applications`.

## Publicar el tap (propietario, una sola vez)

Estos pasos son **MANUALES** y se hacen fuera de este repositorio (el repo del tap es propiedad de la cuenta de GitHub del proyecto):

1. Crea en GitHub un repositorio **PÚBLICO** llamado exactamente `homebrew-tap` bajo tu cuenta (en <https://github.com/new>). El nombre es obligatorio para que funcione el formato corto del tap.
2. Copia `packaging/homebrew/Casks/cosechamedia.rb` de este repositorio a `Casks/cosechamedia.rb` dentro del repo del tap (creando la carpeta `Casks/` si no existe).
3. Haz commit y push al repo del tap.
4. Verifícalo desde cualquier Mac ejecutando los dos comandos de la sección «Instalación (usuarios)» de arriba: deben instalar la app sin errores.

A partir de aquí, cualquier cambio de versión del cask se mantiene en ambos sitios (ver abajo).

## Actualizar el cask en cada release

1. Actualiza `__version__` en `app/__init__.py` y crea el tag `v<versión>` EXACTO (la CI valida que coincidan).
2. Espera a que el workflow publique `CosechaMedia-macos.app.zip` (+ su sidecar `.sha256`) en la Release.
3. Descarga el zip y calcula su SHA-256: `shasum -a 256 CosechaMedia-macos.app.zip` en macOS/Linux, o `Get-FileHash -Algorithm SHA256` / `certutil -hashfile <archivo> SHA256` en Windows.
4. Actualiza en el cask AMBAS copias — la de este repo (`packaging/homebrew/Casks/cosechamedia.rb`) y la del repo del tap — los campos `version` y `sha256`, sustituyendo `:no_check` por el hash real entrecomillado.
5. Haz push al repo del tap.
6. Comprueba que todo cuadra con `brew info --cask MustangXPress7/tap/cosechamedia`: debe mostrar la versión nueva.

## Ver también

- [SIGNING](SIGNING.md): firma de binarios, integridad (sidecars `.sha256`) y primera apertura en macOS.
