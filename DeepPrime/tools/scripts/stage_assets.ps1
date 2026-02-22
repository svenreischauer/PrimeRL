$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$py = "C:\Users\svenr\anaconda3\python.exe"
$script = Join-Path $PSScriptRoot "stage_assets.py"

if (-not (Test-Path $py)) {
    throw "Python interpreter not found at $py"
}

& $py $script @args
