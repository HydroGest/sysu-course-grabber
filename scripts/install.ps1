$ErrorActionPreference = "Stop"

$AppName = "SYSU-Course-Grabber"
$DisplayName = "SYSU 抢课助手"
$Source = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$InstallDir = Join-Path $env:LOCALAPPDATA (Join-Path "Programs" $AppName)
$DataDir = Join-Path $env:LOCALAPPDATA $AppName
$Port = 8124

Write-Host "Installing $DisplayName ..."

function Find-Python {
    $commands = @()
    $py = Get-Command python -ErrorAction SilentlyContinue
    $pyw = Get-Command py -ErrorAction SilentlyContinue
    if ($py) { $commands += $py }
    if ($pyw) { $commands += $pyw }
    foreach ($cmd in $commands) {
        $exe = $cmd.Source
        if (-not $exe -or -not (Test-Path -LiteralPath $exe)) { continue }
        try {
            & $exe -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)" 2>$null
            if ($LASTEXITCODE -eq 0) { return $exe }
        } catch { }
    }
    return $null
}

$Python = Find-Python
if (-not $Python) {
    $Winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($Winget) {
        Write-Host "Python not found. Installing Python 3.12 through winget..."
        & winget install --id Python.Python.3.12 -e --silent --accept-package-agreements --accept-source-agreements
        $env:Path = [Environment]::GetEnvironmentVariable("Path", "User") + ";" + [Environment]::GetEnvironmentVariable("Path", "Machine")
        $Python = Find-Python
    }
}
if (-not $Python) {
    Write-Host "ERROR: Python 3.9+ is required. Install Python from https://www.python.org/downloads/ then run install.bat again."
    Start-Process "https://www.python.org/downloads/"
    exit 1
}
$PythonExe = Split-Path -Parent $Python
$PythonW = Join-Path $PythonExe "pythonw.exe"
if (-not (Test-Path -LiteralPath $PythonW)) { $PythonW = $Python }

Write-Host "Stopping an existing instance..."
try {
    Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/shutdown" -Method Post -TimeoutSec 2 | Out-Null
    Start-Sleep -Seconds 1
} catch { }

if (Test-Path -LiteralPath $InstallDir) {
    $localRoot = [System.IO.Path]::GetFullPath($env:LOCALAPPDATA).TrimEnd("\") + "\"
    $installFull = [System.IO.Path]::GetFullPath($InstallDir)
    if (-not $installFull.StartsWith($localRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to write outside LOCALAPPDATA: $installFull"
    }
    Remove-Item -LiteralPath $installFull -Recurse -Force
}
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
Copy-Item -Path (Join-Path $Source "*") -Destination $InstallDir -Recurse -Force
New-Item -ItemType Directory -Path $DataDir -Force | Out-Null

Write-Host "Installing tray support..."
& $Python -m pip install --user --index-url https://pypi.org/simple --disable-pip-version-check -q -r (Join-Path $InstallDir "requirements.txt") 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Warning: pystray/Pillow could not be installed. The app will run without a tray icon."
}

$MainPy = Join-Path $InstallDir "main.py"
$QuotedMain = '"' + $MainPy + '"'
$QuotedPythonW = '"' + $PythonW + '"'
$RunValue = "$QuotedPythonW $QuotedMain --port $Port --no-open"

$RunKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
Set-ItemProperty -LiteralPath $RunKey -Name $AppName -Value $RunValue -Force

$Shell = New-Object -ComObject WScript.Shell
$Desktop = [Environment]::GetFolderPath("Desktop")
$StartMenu = Join-Path ([Environment]::GetFolderPath("StartMenu")) "Programs"
$UrlText = "[InternetShortcut]`r`nURL=http://127.0.0.1:$Port`r`n"
[System.IO.File]::WriteAllText((Join-Path $Desktop "$DisplayName.url"), $UrlText, [System.Text.Encoding]::Unicode)
[System.IO.File]::WriteAllText((Join-Path $StartMenu "$DisplayName.url"), $UrlText, [System.Text.Encoding]::Unicode)

Write-Host "Starting $DisplayName ..."
Start-Process -FilePath $PythonW -ArgumentList @($QuotedMain, "--port", "$Port", "--no-open") -WorkingDirectory $InstallDir -WindowStyle Hidden
Start-Sleep -Seconds 2
Start-Process "http://127.0.0.1:$Port"

Write-Host ""
Write-Host "Installed to: $InstallDir"
Write-Host "Extension folder: $(Join-Path $InstallDir 'extension')"
Write-Host "Control panel: http://127.0.0.1:$Port"
Write-Host "Next: open the control panel and use '用浏览器登录'."
Write-Host "The browser extension is optional."
