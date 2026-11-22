# Prompt Workbench one-click setup (Windows)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "本地出图工作台 · 一键配置" -ForegroundColor Cyan
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "没有找到 Python。请先安装 Python 3.10+ 并勾选 Add Python to PATH。" -ForegroundColor Red
    Read-Host "按回车退出"
    exit 1
}
Write-Host "Python: $($python.Source)"
Write-Host "安装/检查依赖…"
& $python.Source -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "依赖安装失败。" -ForegroundColor Red
    Read-Host "按回车退出"
    exit 1
}
Write-Host "运行环境自检…"
& $python.Source tools\selfcheck.py
Write-Host ""
Write-Host "启动工作台；首次启动会打开环境设置。" -ForegroundColor Green
$pythonw = Get-Command pythonw -ErrorAction SilentlyContinue
if ($pythonw) {
    Start-Process $pythonw.Source -ArgumentList "`"$PSScriptRoot\app.pyw`""
} else {
    Start-Process $python.Source -ArgumentList "`"$PSScriptRoot\app.pyw`""
}
Read-Host "已启动，按回车关闭此窗口"
