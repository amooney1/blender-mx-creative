# Build the Blender plugin against the local Logi Plugin Service PluginApi.dll
# and pack Blender-windows-1.1.lplug4. Does not install the plugin.
param(
    [string]$PluginApiDir = "",
    [switch]$Install
)

$ErrorActionPreference = "Stop"
if ($Install) {
    Write-Error "This script does not install anything. Follow docs/windows-11.md after reviewing the package."
    exit 2
}

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

if (-not $PluginApiDir) {
    $candidates = @(
        "C:\Program Files\Logi\LogiPluginService",
        "C:\Program Files\Logitech\LogiPluginService"
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath (Join-Path $candidate "PluginApi.dll")) {
            $PluginApiDir = $candidate
            break
        }
    }
}

$api = Join-Path $PluginApiDir "PluginApi.dll"
if (-not (Test-Path -LiteralPath $api)) {
    Write-Error "PluginApi.dll was not found. Run tools\windows_locate.ps1 and pass -PluginApiDir. Do not download that DLL from anywhere except the Logi Plugin Service installed with Options+."
    exit 1
}

$dotnet = Get-Command dotnet -ErrorAction SilentlyContinue
if (-not $dotnet) {
    Write-Error "dotnet was not found on PATH. Logi Plugin Service 6.4 loads net10.0 plugins. Install the .NET 10 SDK, then rerun this script. The SDK is only needed to compile."
    exit 1
}

$env:LOGI_PLUGIN_API_DIR = $PluginApiDir
Write-Output "Using PluginApi.dll from $PluginApiDir"
dotnet build (Join-Path $root "BlenderPlugin\src\BlenderPlugin.csproj") -c Release
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$built = Join-Path $root "BlenderPlugin\bin\Release\bin\BlenderPlugin.dll"
if (-not (Test-Path -LiteralPath $built)) {
    $built = Get-ChildItem -Path (Join-Path $root "BlenderPlugin") -Filter BlenderPlugin.dll -Recurse |
        Where-Object { $_.FullName -match "Release" } |
        Select-Object -First 1 -ExpandProperty FullName
}
if (-not $built -or -not (Test-Path -LiteralPath $built)) {
    Write-Error "The Release build did not produce BlenderPlugin.dll."
    exit 1
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command python3 -ErrorAction SilentlyContinue }
if (-not $python) {
    Write-Error "Python was not found. The assembly is at $built. Pack it with tools\package_plugin.py."
    exit 1
}

& $python.Source (Join-Path $root "tools\package_plugin.py") `
    --dll $built `
    --lplug4 (Join-Path $root "dist\Blender-windows-1.1.lplug4") `
    --addon-zip (Join-Path $root "dist\blender_mx_bridge-1.1.0.zip")
exit $LASTEXITCODE
