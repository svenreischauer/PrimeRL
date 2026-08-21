param(
    [string]$Version = "1.2.0",
    [string]$Manufacturer = "Reischauer Lab",
    [switch]$BuildExe,
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
if ($BuildExe) {
    & (Join-Path $PSScriptRoot "build_exe.ps1") -Version "1.2" -Clean:$Clean
}

$exeRoot = Join-Path $repoRoot "release\PrimeRL_1.2_exe_win64_nodb\dist\PrimeRL"
if (-not (Test-Path (Join-Path $exeRoot "PrimeRL.exe"))) {
    throw "Executable payload missing. Build first: release/scripts/build_exe.ps1"
}

$wixPath = $null
$wixCommand = Get-Command wix.exe -ErrorAction SilentlyContinue
if ($wixCommand) {
    $wixPath = $wixCommand.Source
} else {
    $wixCandidates = @(
        "C:\Program Files\WiX Toolset v7.0\bin\wix.exe",
        "C:\Program Files\WiX Toolset v6.0\bin\wix.exe"
    )
    foreach ($candidate in $wixCandidates) {
        if (Test-Path -LiteralPath $candidate) {
            $wixPath = $candidate
            break
        }
    }
}
if (-not $wixPath) {
    throw "WiX CLI v7 or v6 not found. Install with: winget install --id WiXToolset.WiXCLI -e"
}

$outputRoot = Join-Path $repoRoot "release\PrimeRL_1.2_msi_win64"
$wixRoot = Join-Path $outputRoot "wix"
$productWxs = Join-Path $wixRoot "Product.wxs"
$licenseRtf = Join-Path $wixRoot "LICENSE.rtf"
$cleanupVbs = Join-Path $wixRoot "CleanupPrompt.vbs"
$msiPath = Join-Path $outputRoot "PrimeRL_1.2_win64.msi"

if ($Clean -and (Test-Path $outputRoot)) {
    Remove-Item -Recurse -Force $outputRoot
}
New-Item -ItemType Directory -Force -Path $outputRoot, $wixRoot | Out-Null

$licenseRtfContent = @'
{\rtf1\ansi\deff0
{\fonttbl{\f0 Calibri;}}
\fs22
PrimeRL License\par
\par
This software is released under the MIT License.\par
\par
Permission is hereby granted, free of charge, to any person obtaining a copy\par
of this software and associated documentation files (the "Software"), to deal\par
in the Software without restriction, including without limitation the rights\par
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\par
copies of the Software, and to permit persons to whom the Software is\par
furnished to do so, subject to the following conditions:\par
\par
The above copyright notice and this permission notice shall be included in\par
all copies or substantial portions of the Software.\par
\par
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\par
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\par
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\par
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\par
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\par
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\par
THE SOFTWARE.\par
\par
Copyright (c) 2026- Sven Reischauer/ReischauerLab\par
}
'@
$licenseRtfContent | Set-Content -Encoding ASCII $licenseRtf

$cleanupVbsContent = @'
On Error Resume Next
Dim shell, fso, answer, dataRoot
Set shell = CreateObject("WScript.Shell")
answer = MsgBox("Do you also want to remove downloaded transcriptome databases and index files from your user profile?" & vbCrLf & vbCrLf & "Path: " & shell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\PrimeRL\databases", vbYesNo + vbQuestion, "PrimeRL Uninstall")
If answer = vbYes Then
  dataRoot = shell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\PrimeRL\databases"
  Set fso = CreateObject("Scripting.FileSystemObject")
  If fso.FolderExists(dataRoot) Then
    fso.DeleteFolder dataRoot, True
  End If
End If
'@
$cleanupVbsContent | Set-Content -Encoding ASCII $cleanupVbs

$productXml = @'
<Wix xmlns="http://wixtoolset.org/schemas/v4/wxs" xmlns:ui="http://wixtoolset.org/schemas/v4/wxs/ui">
  <Package Name="PrimeRL"
           Manufacturer="$(var.ManufacturerName)"
           Version="$(var.ProductVersion)"
           UpgradeCode="A0B61EB5-B4FC-47BA-B653-92C5D0689DBE"
           Language="1033"
           Scope="perMachine">
    <MajorUpgrade DowngradeErrorMessage="A newer version of PrimeRL is already installed." />
    <MediaTemplate EmbedCab="yes" CompressionLevel="high" />
    <WixVariable Id="WixUILicenseRtf" Value="$(var.LicenseRtf)" />
    <Icon Id="PrimeRLIcon" SourceFile="$(var.SourceDir)\PrimeRL.exe" />
    <Property Id="ARPPRODUCTICON" Value="PrimeRLIcon" />
    <ui:WixUI Id="WixUI_FeatureTree" InstallDirectory="INSTALLFOLDER" />
    <Feature Id="MainApplication" Title="PrimeRL application files" Level="1">
      <ComponentGroupRef Id="MainApplicationComponents" />
    </Feature>
    <Feature Id="DesktopShortcutFeature" Title="Create desktop shortcut" Level="1">
      <ComponentRef Id="DesktopShortcutComponent" />
    </Feature>
    <Feature Id="UninstallCleanupSupport" Title="Uninstall cleanup support" Level="1" Display="hidden">
      <ComponentRef Id="CleanupPromptScriptComponent" />
    </Feature>

    <CustomAction Id="PromptCleanupUserData"
                  Directory="SystemFolder"
                  ExeCommand='wscript.exe //nologo &quot;[INSTALLFOLDER]CleanupPrompt.vbs&quot;'
                  Execute="immediate"
                  Return="ignore"
                  Impersonate="yes" />

    <InstallExecuteSequence>
      <Custom Action="PromptCleanupUserData" Before="RemoveFiles" Condition='REMOVE="ALL" AND NOT UPGRADINGPRODUCTCODE' />
    </InstallExecuteSequence>
  </Package>

  <Fragment>
    <StandardDirectory Id="ProgramFiles64Folder">
      <Directory Id="INSTALLFOLDER" Name="PrimeRL" />
    </StandardDirectory>
  </Fragment>

  <Fragment>
    <ComponentGroup Id="MainApplicationComponents" Directory="INSTALLFOLDER">
      <Files Include="$(var.SourceDir)\**" />
    </ComponentGroup>
  </Fragment>

  <Fragment>
    <DirectoryRef Id="INSTALLFOLDER">
      <Component Id="CleanupPromptScriptComponent" Guid="D4AFA3F2-141A-4C83-AC65-B7244F2E96FC">
        <File Id="CleanupPromptScriptFile" Source="$(var.CleanupVbs)" KeyPath="yes" Name="CleanupPrompt.vbs" />
      </Component>
    </DirectoryRef>
  </Fragment>

  <Fragment>
    <StandardDirectory Id="DesktopFolder">
      <Component Id="DesktopShortcutComponent" Guid="A9068250-8B24-4CE3-B5C5-F9C2A48B9A2F">
        <Shortcut Id="PrimeRLDesktopShortcut"
                  Name="PrimeRL"
                  Description="PrimeRL"
                  Target="[INSTALLFOLDER]PrimeRL.exe"
                  WorkingDirectory="INSTALLFOLDER" />
        <RegistryValue Root="HKCU" Key="Software\PrimeRL" Name="DesktopShortcut" Type="integer" Value="1" KeyPath="yes" />
      </Component>
    </StandardDirectory>
  </Fragment>
</Wix>
'@

$productXml | Set-Content -Encoding UTF8 $productWxs
$sourceDirAbs = (Resolve-Path $exeRoot).Path

& $wixPath build $productWxs -ext WixToolset.UI.wixext -d SourceDir="$sourceDirAbs" -d ProductVersion="$Version" -d ManufacturerName="$Manufacturer" -d LicenseRtf="$licenseRtf" -d CleanupVbs="$cleanupVbs" -arch x64 -out $msiPath
if ($LASTEXITCODE -ne 0) {
    throw "WiX build failed."
}

if (-not (Test-Path $msiPath)) {
    throw "MSI build finished but output not found: $msiPath"
}

Write-Host "Done: $msiPath"
