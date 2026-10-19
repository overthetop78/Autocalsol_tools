param(
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

if (-not $SkipInstall) {
    python -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        throw "L'installation des dependances a echoue."
    }
}
$legacyExe = Join-Path $PSScriptRoot "dist\AutocalsolTools.exe"
if (Test-Path -LiteralPath $legacyExe) {
    Remove-Item -LiteralPath $legacyExe -Force
}
python -m PyInstaller --noconfirm --clean --onedir --windowed `
    --name AutocalsolTools `
    --contents-directory lib `
    --specpath build `
    --workpath build\work `
    --distpath dist `
    --exclude-module pytest `
    --exclude-module matplotlib `
    --exclude-module jinja2 `
    --exclude-module fsspec `
    --exclude-module IPython `
    --exclude-module scipy `
    --hidden-import xlrd `
    --hidden-import odf `
    main.py
if ($LASTEXITCODE -ne 0) {
    throw "La compilation PyInstaller a echoue."
}

Write-Host "Application creee dans dist\AutocalsolTools\"

