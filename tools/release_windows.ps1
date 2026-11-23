param(
  [string]$Version = (Get-Content (Join-Path $PSScriptRoot '..\VERSION') -Raw).Trim(),
  [switch]$SkipBuild
)
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $root
$venv = Join-Path $root '.build-venv\Scripts\python.exe'
if (-not $SkipBuild) {
  & $venv -m PyInstaller --noconfirm --clean --windowed --name PromptWorkbench `
    --icon (Join-Path $root 'prompt-workbench.ico') `
    --add-data "skills;skills" --add-data "assets;assets" `
    --add-data "prompt-workbench.ico;." --add-data "VERSION;." `
    --distpath (Join-Path $root 'dist-release') --workpath (Join-Path $root 'build-release') `
    (Join-Path $root 'app.pyw')
  if ($LASTEXITCODE -ne 0) { throw "PyInstaller 失败" }
}
$dist = Join-Path $root 'dist-release\PromptWorkbench'
Copy-Item (Join-Path $root 'README.md'),(Join-Path $root 'LICENSE'),(Join-Path $root 'THIRD_PARTY_NOTICES.md'),(Join-Path $root 'CHANGELOG.md'),(Join-Path $root '使用说明.md'),(Join-Path $root 'VERSION') -Destination $dist -Force
& (Join-Path $PSScriptRoot 'sign_windows.ps1') -Exe (Join-Path $dist 'PromptWorkbench.exe')
$zip = Join-Path $root "dist-release\local-image-workbench-$Version-portable.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $dist -DestinationPath $zip -CompressionLevel Optimal
$hash = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLower()
"$hash  $(Split-Path $zip -Leaf)" | Set-Content (Join-Path $root 'dist-release\SHA256SUMS.txt') -Encoding UTF8
Write-Host "ZIP=$zip"
Write-Host "SHA256=$hash"

