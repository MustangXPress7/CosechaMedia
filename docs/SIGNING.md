# Firma de binarios

Este documento describe el estado de la firma e integridad de los binarios publicados en GitHub Releases y el camino previsto hacia una firma de autenticidad real por plataforma.

## Estado actual

- Cada asset publicado en una Release lleva un sidecar `.sha256` con su hash SHA-256.
- La propia aplicación (`app/core/updater.py`) verifica el SHA-256 de los assets que descarga el autoactualizador, así como la versión.
- **macOS**: las builds llevan firma ad-hoc desde CI (`codesign --force --deep -s -`, aplicada antes de comprimir y hashear). Sella el bundle y evita los falsos «aplicación dañada» típicos de apps sin sellar, pero no identifica a ningún desarrollador verificado ante Gatekeeper.
- **Windows / Linux**: sin firma de autenticidad; la integridad se garantiza mediante el sidecar SHA-256.

## macOS — primera apertura (usuarios)

La app no está firmada con un certificado de desarrollador de Apple, por lo que la primera vez que la abras Gatekeeper puede mostrar un aviso. Dos caminos:

1. **Clic derecho → Abrir**: haz clic derecho (o Ctrl+clic) sobre `CosechaMedia.app` y elige **Abrir**; en el diálogo, confirma con **Abrir** otra vez. Solo es necesario la primera vez.
2. Si aparece «aplicación dañada» (la cuarentena extendida del navegador llega a marcar apps correctas), ejecuta en Terminal:

   ```bash
   xattr -dr com.apple.quarantine /ruta/a/CosechaMedia.app
   ```

   Sustituye `/ruta/a/CosechaMedia.app` por la ruta real del bundle descargado.

> Nota técnica: la firma ad-hoc es gratuita pero no verificable ante terceros. Una firma Developer ID + notarización requeriría una cuenta de pago de Apple Developer, opción descartada por ahora.

## Windows — SignPath Foundation (mantenedores)

El objetivo para firmar el ejecutable de Windows es [SignPath Foundation](https://signpath.org/), el programa de firma gratuita para proyectos de código abierto con licencia aprobada por OSI — GPLv3 cualifica tras el cambio de licencia de este repositorio.

Pasos previstos, **pendientes de solicitud manual fuera de este repo** (no hay credenciales todavía):

1. Solicitar acceso al programa de SignPath Foundation vinculando este repositorio y su licencia.
2. Una vez aprobado, crear el proyecto y la política de firma en el panel de SignPath.
3. Configurar los secretos de GitHub: `SIGNPATH_API_TOKEN`, `SIGNPATH_ORGANIZATION_ID` y `SIGNPATH_PROJECT_SLUG`.
4. Añadir al job de Windows del workflow `.github/workflows/build.yml` un paso **entre «Prepare assets (Windows)» y «Upload release assets»** que firme `release/CosechaMedia-windows-x86_64.exe` con la acción oficial de SignPath consumiendo esos secretos.

Esqueleto ilustrativo — **NO añadir al workflow hasta tener credenciales válidas**:

```yaml
#       - name: Sign Windows binary (SignPath)
#         if: runner.os == 'Windows'
#         uses: signpath/github-action-submit-signing-request@v1
#         with:
#           api-token: '${{ secrets.SIGNPATH_API_TOKEN }}'
#           organization-id: '${{ secrets.SIGNPATH_ORGANIZATION_ID }}'
#           project-slug: cosechamedia
#           signing-policy-slug: release-signing
#           artifact-configuration-slug: windows-exe
#           input-artifact-path: release/CosechaMedia-windows-x86_64.exe
```

Mientras la solicitud no prospere, la integridad de los binarios de Windows sigue garantizada únicamente por el sidecar SHA-256.

## Linux

Sin cambios previstos: cada asset ya publica su `.sha256`. No hay paquetes nativos (AppImage/deb/rpm) en el roadmap.
