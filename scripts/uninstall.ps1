$ErrorActionPreference = "Stop"
$AppName = "SYSU-Course-Grabber"
$DisplayName = "SYSU 抢课助手"
$InstallDir = Join-Path $env:LOCALAPPDATA (Join-Path "Programs" $AppName)
$DataDir = Join-Path $env:LOCALAPPDATA $AppName

if (-not (Test-Path -LiteralPath $InstallDir)) {
    Write-Host "The app is not installed in $InstallDir"
    exit 1
}

$answer = Read-Host "Uninstall $DisplayName? Type YES to continue"
if ($answer -ne "YES") { exit 1 }

try {
    Invoke-RestMethod -Uri "http://127.0.0.1:8124/api/shutdown" -Method Post -TimeoutSec 2 | Out-Null
    Start-Sleep -Seconds 1
} catch { }

$RunKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
Remove-ItemProperty -LiteralPath $RunKey -Name $AppName -ErrorAction SilentlyContinue

$Desktop = [Environment]::GetFolderPath("Desktop")
$StartMenu = Join-Path ([Environment]::GetFolderPath("StartMenu")) "Programs"
Remove-Item -LiteralPath (Join-Path $Desktop "$DisplayName.url") -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath (Join-Path $StartMenu "$DisplayName.url") -Force -ErrorAction SilentlyContinue

$localRoot = [System.IO.Path]::GetFullPath($env:LOCALAPPDATA).TrimEnd("\") + "\"
$installFull = [System.IO.Path]::GetFullPath($InstallDir)
if (-not $installFull.StartsWith($localRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to remove path outside LOCALAPPDATA: $installFull"
}
Remove-Item -LiteralPath $installFull -Recurse -Force

if (Test-Path -LiteralPath $DataDir) {
    $removeData = Read-Host "Remove saved cookies and target data too? Type YES to remove"
    if ($removeData -eq "YES") {
        $dataFull = [System.IO.Path]::GetFullPath($DataDir)
        if ($dataFull.StartsWith($localRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
            Remove-Item -LiteralPath $dataFull -Recurse -Force
        }
    }
}
Write-Host "Uninstalled."

