$AppName = "SYSU-Course-Grabber"
$InstallDir = Join-Path $env:LOCALAPPDATA (Join-Path "Programs" $AppName)
$MainPy = Join-Path $InstallDir "main.py"
$SourceMain = Join-Path $PSScriptRoot "..\main.py"
if (-not (Test-Path -LiteralPath $MainPy)) { $MainPy = (Resolve-Path $SourceMain).Path }
if (Test-Path -LiteralPath $MainPy) {
    $PythonExe = (Get-Command python -ErrorAction Stop).Source
    $PythonDir = Split-Path -Parent $PythonExe
    $PythonW = Join-Path $PythonDir "pythonw.exe"
    if (-not (Test-Path -LiteralPath $PythonW)) { $PythonW = $PythonExe }
    $WorkDir = Split-Path -Parent $MainPy
    Start-Process -FilePath $PythonW -ArgumentList ('"' + $MainPy + '"', "--port", "8124") -WorkingDirectory $WorkDir -WindowStyle Hidden
    Start-Sleep -Seconds 2
}
Start-Process "http://127.0.0.1:8124"
