param(
    [string]$Version = "1.2",
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$outputRoot = Join-Path $repoRoot ("release\PrimeRL_{0}_exe_win64_nodb" -f $Version)
$workRoot = Join-Path $outputRoot "build"
$distRoot = Join-Path $outputRoot "dist"
$specRoot = $outputRoot

$assetBundleRoot = Join-Path $repoRoot ("release\PrimeRL_{0}_portable_win64_nodb\PrimeRL {0}" -f $Version)
if (-not (Test-Path $assetBundleRoot)) {
    $fallbackAssetBundleRoot = Join-Path $repoRoot "release\PrimeRL_1.1_portable_win64_nodb\PrimeRL 1.1"
    if (Test-Path $fallbackAssetBundleRoot) {
        Write-Host "Version-matched portable asset bundle not found for $Version. Falling back to 1.1 portable assets."
        $assetBundleRoot = $fallbackAssetBundleRoot
    }
}
$assetRoot = Join-Path $assetBundleRoot "PrimeRL"
$thirdPartyRoot = Join-Path $assetBundleRoot "third_party"

if (-not (Test-Path $assetRoot)) {
    throw "Asset root missing: $assetRoot"
}
if (-not (Test-Path $thirdPartyRoot)) {
    throw "Third-party root missing: $thirdPartyRoot"
}

if ($Clean -and (Test-Path $outputRoot)) {
    Remove-Item -Recurse -Force $outputRoot
}

New-Item -ItemType Directory -Force -Path $outputRoot, $workRoot, $distRoot | Out-Null

& python -m PyInstaller --version | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller is not installed for this Python. Install with: python -m pip install pyinstaller"
}

$addDataArgs = @(
    "--add-data", "$assetRoot\config;PrimeRL\config",
    "--add-data", "$assetRoot\databases;PrimeRL\databases",
    "--add-data", "$assetRoot\docs;PrimeRL\docs",
    "--add-data", "$assetRoot\runtime;PrimeRL\runtime",
    "--add-data", "$assetRoot\tools;PrimeRL\tools",
    "--add-data", "$thirdPartyRoot;third_party"
)

$pyArgs = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--windowed",
    "--name", "PrimeRL",
    "--paths", (Join-Path $repoRoot "src"),
    "--hidden-import", "primerl.gui",
    "--workpath", $workRoot,
    "--distpath", $distRoot,
    "--specpath", $specRoot
) + $addDataArgs + @(
    (Join-Path $repoRoot "run_gui.py")
)

Write-Host "Building PrimeRL executable with PyInstaller ..."
& python @pyArgs
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed."
}

$exePath = Join-Path $distRoot "PrimeRL\PrimeRL.exe"
if (-not (Test-Path $exePath)) {
    throw "Build finished but executable not found: $exePath"
}

Write-Host "Done: $exePath"
