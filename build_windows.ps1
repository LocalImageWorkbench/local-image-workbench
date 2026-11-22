# Build a portable Windows app with PyInstaller.
# Run from the repository root. Requires a working Python 3.10+ to build.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "找不到 python。构建需要 Python 3.10+。" -ForegroundColor Red
    exit 1
}

$venv = Join-Path $PSScriptRoot ".build-venv"
if (-not (Test-Path $venv)) {
    & $python.Source -m venv $venv
}
$buildPy = Join-Path $venv "Scripts\python.exe"
& $buildPy -m pip install --upgrade pip pyinstaller requests
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $buildPy -m PyInstaller `
  --noconfirm `
  --clean `
  --windowed `
  --name PromptWorkbench `
  --icon prompt-workbench.ico `
  --add-data "skills;skills" `
  --add-data "assets;assets" `
  --add-data "prompt-workbench.ico;." `
  --add-data "VERSION;." `
  app.pyw
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$dist = Join-Path $PSScriptRoot "dist\PromptWorkbench"
Copy-Item README.md, LICENSE, THIRD_PARTY_NOTICES.md -Destination $dist -Force
Write-Host "Built: $dist\PromptWorkbench.exe"
