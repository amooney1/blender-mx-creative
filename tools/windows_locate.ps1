# Read-only inventory for the Windows 11 test machine.
# Prints whether Blender, Logi Plugin Service, PluginApi.dll and dotnet were
# found. Does not install software, does not read settings.db, logs, or
# account files, and does not change Options+ profiles.
param(
    [string[]]$ExtraRoot = @()
)

$ErrorActionPreference = "Continue"

function Say([string]$Status, [string]$Message) {
    Write-Output ("{0}`t{1}" -f $Status, $Message)
}

Say "INFO" ("OS={0}" -f [Environment]::OSVersion.VersionString)

$dotnet = Get-Command dotnet -ErrorAction SilentlyContinue
if ($dotnet) { Say "FOUND" ("dotnet {0}" -f $dotnet.Source) } else { Say "MISSING" "dotnet on PATH" }

foreach ($name in @("LogiPluginService.exe", "LogiPluginServiceExt.exe", "logioptionsplus.exe", "blender.exe")) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue
    if ($cmd) { Say "FOUND" ("{0} {1}" -f $name, $cmd.Source) } else { Say "MISSING" ("{0} on PATH" -f $name) }
}

$roots = @(
    $env:ProgramFiles,
    ${env:ProgramFiles(x86)},
    (Join-Path $env:LOCALAPPDATA "Logi"),
    (Join-Path $env:ProgramData "Logishrd"),
    "C:\Program Files\Logi",
    "C:\Program Files\Logitech",
    "C:\Program Files\LogiOptionsPlus"
) + $ExtraRoot

$seen = @{}
foreach ($root in $roots) {
    if (-not $root -or -not (Test-Path -LiteralPath $root)) { continue }
    $full = (Resolve-Path -LiteralPath $root).Path
    if ($seen.ContainsKey($full)) { continue }
    $seen[$full] = $true
    Say "ROOT" $full
    foreach ($filter in @("PluginApi.dll", "LogiPluginService.exe", "blender.exe")) {
        Get-ChildItem -LiteralPath $full -Filter $filter -Recurse -Depth 6 -ErrorAction SilentlyContinue |
            ForEach-Object { Say "FOUND" ("{0} {1}" -f $filter, $_.FullName) }
    }
}

$pluginDir = Join-Path $env:LOCALAPPDATA "Logi\LogiPluginService\Plugins"
if (Test-Path -LiteralPath $pluginDir) {
    Say "FOUND" ("Plugins {0}" -f $pluginDir)
    Get-ChildItem -LiteralPath $pluginDir -ErrorAction SilentlyContinue |
        ForEach-Object { Say "ENTRY" $_.Name }
} else {
    Say "MISSING" ("Plugins {0}" -f $pluginDir)
}

$link = Join-Path $pluginDir "BlenderPlugin.link"
if (Test-Path -LiteralPath $link) { Say "FOUND" ("link {0}" -f $link) } else { Say "MISSING" ("link {0}" -f $link) }

Say "INFO" "No files were modified. Portable Blender and a Plugin Service installed outside these roots will not appear; pass -ExtraRoot for another directory."
