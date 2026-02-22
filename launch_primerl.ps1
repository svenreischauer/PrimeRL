$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$runGui = Join-Path $root "run_gui.py"
$bundledPyw = Join-Path $root "python\pythonw.exe"

if (Test-Path $bundledPyw) {
    Start-Process -FilePath $bundledPyw -ArgumentList @($runGui) -WindowStyle Hidden -WorkingDirectory $root
    exit 0
}

$pywCmd = Get-Command pythonw -ErrorAction SilentlyContinue
if ($pywCmd) {
    Start-Process -FilePath $pywCmd.Source -ArgumentList @($runGui) -WindowStyle Hidden -WorkingDirectory $root
    exit 0
}

Write-Host "pythonw not found. Falling back to python (console may appear briefly)." -ForegroundColor Yellow
Start-Process -FilePath "python" -ArgumentList @($runGui) -WindowStyle Hidden -WorkingDirectory $root
