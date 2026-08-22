cask "cosechamedia" do
  version "1.5.0.b3"
  sha256 "563680fd9af262ecc878372e792a52e5cb91f2bcfa650e97f9dac913b0875ec3"

  # Fijado del asset CosechaMedia-macos.app.zip de v1.5.0.b3 (verificado
  # contra el digest de GitHub). Para cada release nueva: descargar el zip,
  # calcular shasum -a 256 y actualizar ambas copias del cask (esta y la del
  # tap homebrew-tap). Checklist completa por release en docs/HOMEBREW.md.

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
