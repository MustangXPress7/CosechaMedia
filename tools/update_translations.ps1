$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$scripts = Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\Scripts"
$lupdate = Join-Path $scripts "pyside6-lupdate.exe"
$lrelease = Join-Path $scripts "pyside6-lrelease.exe"
$i18n = Join-Path $root "app\i18n"

$sources = @(
    (Join-Path $root "main.py")
)
# Escaneo recursivo de todo app/ (mixins, diálogos, core) sin archivos basura/stale.
$sources += Get-ChildItem -Path (Join-Path $root "app") -Recurse -Filter "*.py" |
    Where-Object { $_.FullName -notmatch "__pycache__" -and $_.Name -ne "sources_mixin_pre.py" } |
    ForEach-Object { $_.FullName }

New-Item -ItemType Directory -Force -Path $i18n | Out-Null

foreach ($ts in @("cosechamedia_en.ts")) {
    & $lupdate $sources -ts (Join-Path $i18n $ts)
    if ($LASTEXITCODE -ne 0) { throw "lupdate failed for $ts" }
    & python (Join-Path $root "tools\translate_en.py")
    if ($LASTEXITCODE -ne 0) { throw "translate_en.py failed" }
    & $lrelease (Join-Path $i18n $ts)
    if ($LASTEXITCODE -ne 0) { throw "lrelease failed for $ts" }
}

Write-Host "Translations updated: $i18n"
