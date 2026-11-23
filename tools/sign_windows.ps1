param(
  [Parameter(Mandatory=$true)][string]$Exe,
  [string]$CertSha1 = $env:PW_SIGN_CERT_SHA1,
  [string]$Timestamp = "http://timestamp.digicert.com"
)
$ErrorActionPreference = "Stop"
if (-not $CertSha1) { Write-Host "未设置 PW_SIGN_CERT_SHA1；跳过签名。"; exit 0 }
$signtool = (Get-Command signtool.exe -ErrorAction SilentlyContinue).Source
if (-not $signtool) {
  $candidates = @("C:\Program Files (x86)\Windows Kits\10\bin\*\x64\signtool.exe")
  $signtool = Get-ChildItem $candidates -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | Select-Object -First 1 -ExpandProperty FullName
}
if (-not $signtool) { throw "找不到 signtool.exe；请安装 Windows SDK。" }
& $signtool sign /sha1 $CertSha1 /fd SHA256 /tr $Timestamp /td SHA256 $Exe
if ($LASTEXITCODE -ne 0) { throw "签名失败，退出码 $LASTEXITCODE" }
Write-Host "已签名：$Exe"
