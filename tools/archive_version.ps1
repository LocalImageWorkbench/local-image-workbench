# -*- coding: utf-8 -*-
param(
    [Parameter(Mandatory=$true)][string]$Version,
    [Parameter(Mandatory=$true)][string]$Zip,
    [Parameter(Mandatory=$true)][string]$Exe,
    [switch]$Latest,
    [switch]$Previous
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$versions = Join-Path $root "versions"
$dest = Join-Path $versions $Version
New-Item -ItemType Directory -Force $dest | Out-Null
if (-not (Test-Path $Zip)) { throw "缺少包：$Zip" }
$name = Split-Path $Zip -Leaf
Copy-Item $Zip (Join-Path $dest $name) -Force
$hash = (Get-FileHash (Join-Path $dest $name) -Algorithm SHA256).Hash.ToLower()
"$hash  $name" | Set-Content (Join-Path $dest "SHA256SUMS.txt") -Encoding UTF8
$ws = New-Object -ComObject WScript.Shell
$shortcut = Join-Path $dest "启动 - $Version.lnk"
$s = $ws.CreateShortcut($shortcut)
$s.TargetPath = $Exe
$s.WorkingDirectory = Split-Path $Exe
$s.IconLocation = "$Exe,0"
$s.Save()
if ($Latest) {
    $s = $ws.CreateShortcut((Join-Path ([Environment]::GetFolderPath("Desktop")) "本地出图工作台 - 最新版.lnk"))
    $s.TargetPath = $Exe
    $s.WorkingDirectory = Split-Path $Exe
    $s.IconLocation = "$Exe,0"
    $s.Save()
}
if ($Previous) {
    $s = $ws.CreateShortcut((Join-Path ([Environment]::GetFolderPath("Desktop")) "本地出图工作台 - 次新版.lnk"))
    $s.TargetPath = $Exe
    $s.WorkingDirectory = Split-Path $Exe
    $s.IconLocation = "$Exe,0"
    $s.Save()
}
Write-Output "ARCHIVED=$Version"
Write-Output "ZIP=$dest\$name"
Write-Output "SHA256=$hash"
