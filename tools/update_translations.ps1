$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$scripts = Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\Scripts"
$lupdate = Join-Path $scripts "pyside6-lupdate.exe"
$lrelease = Join-Path $scripts "pyside6-lrelease.exe"
$i18n = Join-Path $root "app\i18n"

$sources = @(
    (Join-Path $root "main.py"),
    (Join-Path $root "app\ui\main_window.py"),
    (Join-Path $root "app\ui\about_dialog.py"),
    (Join-Path $root "app\ui\device_picker.py"),
    (Join-Path $root "app\ui\ftp_picker.py"),
    (Join-Path $root "app\ui\project_wizard.py"),
    (Join-Path $root "app\ui\selective_dump.py"),
    (Join-Path $root "app\core\notifications.py"),
    (Join-Path $root "app\core\updater.py")
)

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
