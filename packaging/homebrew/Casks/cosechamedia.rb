cask "cosechamedia" do
  version "1.5.0.b3"

  # Sin hash fijado todavía: la release v1.5.0.b3 aún no está publicada en
  # GitHub Releases (comprobado vía API al crear este cask). En cuanto exista,
  # sustituir la línea de abajo por el hash real del asset:
  #   curl -LO https://github.com/MustangXPress7/CosechaMedia/releases/download/v<VERSIÓN>/CosechaMedia-macos.app.zip
  #   shasum -a 256 CosechaMedia-macos.app.zip
  # Checklist completa por release en docs/HOMEBREW.md.
  sha256 :no_check

  url "https://github.com/MustangXPress7/CosechaMedia/releases/download/v#{version}/CosechaMedia-macos.app.zip"
  name "CosechaMedia"
  desc "Verified video ingest tool for film production"
  homepage "https://github.com/MustangXPress7/CosechaMedia"

  # Temporal: CI genera los assets en macos-latest (Apple Silicon), así que hoy
  # solo hay builds arm64. Retirar esta línea cuando existan builds multi-arquitectura.
  depends_on arch: :arm64

  # La app invoca ffmpeg y ffprobe desde el PATH; la fórmula de Homebrew las deja disponibles ahí.
  depends_on formula: "ffmpeg"

  app "CosechaMedia.app"
end
