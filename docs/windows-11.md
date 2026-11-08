# Windows 11 — Actions Ring package

This is a packaging and application-detection change for the existing Blender
plugin. The shareable Windows files are in
[release/1.1.1](../release/1.1.1/README.md).

## Checked on one PC

Windows 11 Enterprise, build 26200, x64. Logi Options+ 2.9.1013853. Logi
Plugin Service 6.4.2.3414. Blender 5.2.3. .NET SDK 10.0.403.

The 1.1.1 source built against the installed `PluginApi.dll` with 0 warnings
and 0 errors. `tools/windows_build.ps1` did not write a live `.link` and did
not reload the service. Fifteen Python tests and the install-probe program
passed. Set `PYTHONUTF8=1` and `DOTNET_ROLL_FORWARD=Major` in that PowerShell
session before repeating those commands.

The installed assembly is 1.1.1.0, SHA-256
`c2a31284962a2e586bcf7a890e2919322574cd4bb22d8c4cd1325bebce73ff06`. The
package is `Blender-windows-1.1.1.lplug4`, SHA-256
`d02375b5ac2ee63a5a5d86843e7175681d15fdf0dc6875a1f5550dad98b5433d`. The add-on
zip SHA-256 is
`62fb7bfaff1586b6e4bee91814619efe6a95904b9f3cb3ac1779cfe52e58d658`. After a
restart that the user approved, 1.1.1 loaded and the bridge reconnected.

Thirteen loopback checks passed on `127.0.0.1:47800`: ping, state, mode,
edge, vertex, and deselect, plus generic refusals for a wrong context, an
unknown command, an unknown operator, a bad property, an oversized line, and
bad JSON. Those refusals had no traceback and no path. Pairing was off.

On 1.1.0, the MX Master 4 Actions Ring was used manually for Edit Mode and
Vertex. 1.1.1 repeated the loopback regression and did not get a new mouse
press. Focus while the ring stays open, Undo through the ring, haptics, and
switching away from Blender were not part of that check.

The plugin is already a Logi Actions SDK `plugin4` package. Its buttons are
`PluginDynamicCommand` actions and its dials are `PluginDynamicAdjustment`
actions. The C# introduction tells you to open Actions Ring, MX Creative
Keypad, or MX Creative Dialpad and look under **All Actions → Installed
Plugins**. A missing keypad does not mean the actions are console-only.

## What changed

* `LoupedeckPackage.yaml` sets `pluginFolderWin: bin` next to the existing
  `pluginFolderMac: bin`. Both point at the same `net10.0` assembly.
  `PluginApi.dll` is not in the package.
* `supportedDevices` keeps `LogitechCreativeFamily` and adds
  `LoupedeckExtendedFamily`. That second token is the family name in the
  official Actions SDK demo and the `DeviceType` name reported from a
  PluginApi.dll dump as covering Loupedeck70, Loupedeck71, and Loupedeck72
  (Actions Ring). No `MXMaster4` value was added.
* Windows application matching stays on `ClientApplication.GetProcessName()`,
  which returns `blender`. The manifest also has `executablePathPattern` for
  `blender.exe`. A Windows install under `Program Files\Blender Foundation` or
  the Steam `common\Blender\blender.exe` path is reported as installed. The
  macOS `/Applications/Blender.app` check is unchanged. The published 1.1.1
  DLL includes the Windows install probe.
* `profiles/DefaultProfile72win.lp5` is an eight-button template for device
  type `Loupedeck72`: Vertex, Edge, Face, Edit Mode, Extrude, Inset, Undo,
  Redo. `DefaultProfile70.lp5` and `DefaultProfile71.lp5` are byte-for-byte
  the previous files. Undo and Redo are still keystrokes, because Blender
  refuses `ed.undo` / `ed.redo` from the add-on. The other ring slots use the
  bridge first.
* The add-on still listens on `127.0.0.1:47800`. It refuses operators that the
  plugin does not send, and it refuses a request line over 8192 bytes. Failed
  replies are a fixed error code and a fixed phrase. They do not include a
  Python traceback or the exception text.
* Pairing is implemented and left off. An empty add-on token and a missing
  plugin token file keep the Mac install and the tested Windows install on
  the same protocol. Turning the token on is a migration and needs approval
  before anyone sets it on a live machine. See below.

Marketplace approval guidelines exclude GPL-2.0 and GPL-3.0. This package
stays GPL-3.0-or-later and is not claimed to be Marketplace-eligible.

## Files to copy to the PC

From `dist/` after the pack step, or from the artifact bundle:

* [release/1.1.1/Blender-windows-1.1.1.lplug4](../release/1.1.1/Blender-windows-1.1.1.lplug4)
* [release/1.1.1/blender_mx_bridge-1.1.1.zip](../release/1.1.1/blender_mx_bridge-1.1.1.zip)

Do not copy `PluginApi.dll` from another machine. Do not copy Options+
`settings.db`, logs, or profile backups off the PC.

## Before installing

Run this in PowerShell. It only prints paths. It does not install or edit
anything.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\windows_locate.ps1
```

Record, locally:

* Windows version (expected: Windows 11 Enterprise, build 26200, x64)
* whether `PluginApi.dll`, `LogiPluginService.exe`, `blender.exe`, and `dotnet`
  were found, and their paths
* Logi Options+ and Logi Plugin Service versions, from the programs list or
  the executable properties

A previous look did not find Blender, the default Plugin Service path, or
`dotnet` on `PATH`. They may live somewhere else. If `windows_locate.ps1`
misses a directory you know about, rerun it with `-ExtraRoot`.

Stop here if Options+ or Logi Plugin Service is not installed. Do not install
the plugin into an empty plugins folder and expect the ring to appear.

The files in `release/1.1.1` install without the .NET SDK. The SDK is only
needed to rebuild. This assembly targets `net10.0`. Logi Plugin Service
6.4.2.3414 loaded it. An older host may refuse the DLL.

## Rebuild

The published package is already the PC build of 1.1.1. Rebuild only when you
mean to replace it. Do not set `LOGI_PLUGIN_DIR`. The script passes
`-p:BlenderPluginDevLink=false`, so this build does not write
`BlenderPlugin.link` and does not reload Logi Plugin Service. In the same
session, set `PYTHONUTF8=1` and `DOTNET_ROLL_FORWARD=Major`.

A plain `dotnet build` without that property still writes the link and
reloads. That is the developer loop, and it is what 1.1.0 did until
`LOGI_PLUGIN_DIR` was pointed at a scratch directory.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\windows_build.ps1
```

If `PluginApi.dll` is not in a default directory:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\windows_build.ps1 -PluginApiDir "D:\path\to\the\directory"
```

The script refuses `-Install`. It writes `dist\Blender-windows-1.1.1.lplug4`
and `dist\blender_mx_bridge-1.1.1.zip`. It does not copy `PluginApi.dll` into
the package. After it finishes, confirm no new `BlenderPlugin.link` appeared
under `%LOCALAPPDATA%\Logi\LogiPluginService\Plugins`. Install the new package
only when you mean to, using the unpack steps below.

## Install the add-on

1. Use a disposable `.blend`. Do not point this at a real production file.
2. Blender → Edit → Preferences → Add-ons → the menu → **Install from Disk…**
   → `release\1.1.1\blender_mx_bridge-1.1.1.zip`. Leave the Bridge token blank.
3. Enable **MX Console Bridge** if it did not enable itself.
4. **Save Preferences**.
5. In the Blender system console, or Window → Toggle System Console, look for
   `listening on 127.0.0.1:47800`.
6. Restart Blender after any later replacement of the add-on. Installing over
   the files does not unload the old module.

The add-on does not need an internet connection. It binds `127.0.0.1` only.

## Pairing

Leave this off for the machine that already passed the loopback checks, and
for the existing Mac install. The add-on token ships empty. The plugin sends
an `auth` field only when this file exists and contains one line of at most
256 characters:

```text
%LOCALAPPDATA%\Logi\LogiPluginService\PluginData\Blender\bridge.token
```

On macOS the same relative path is under `~/Library/Application Support/`.
Do not create that file, and do not type a token into the add-on, until a
rebuild that contains this source is installed on both sides and that
migration has been approved. If only the add-on token is set, every command
is refused with `unauthorized` and the tested plugin stops driving Blender.

With both sides empty, which is the tested default, there is no authenticator.
Any local program can connect to `127.0.0.1:47800` and invoke an allowlisted
action. The allowlist is unchanged. That is the compatible limit of this
release, not a private channel.

## Install the plugin

`logiplugintool install` from a terminal failed on the Mac this project was
built on. Unpack by hand. Quit is not required for the copy, but restart the
plugin service afterwards.

```powershell
$plugins = Join-Path $env:LOCALAPPDATA "Logi\LogiPluginService\Plugins\Blender"
if (Test-Path $plugins) { Remove-Item -LiteralPath $plugins -Recurse -Force }
New-Item -ItemType Directory -Force -Path $plugins | Out-Null
Expand-Archive -LiteralPath .\release\1.1.1\Blender-windows-1.1.1.lplug4 -DestinationPath $plugins -Force
```

`.lplug4` is a zip with a different extension. If `Expand-Archive` refuses it,
copy it to a temporary `.zip` and expand that copy. Do not expand it over a
different plugin's folder.

Also delete a development link if one is present. A `.link` file wins over
the unpacked package:

```powershell
Remove-Item -LiteralPath (Join-Path $env:LOCALAPPDATA "Logi\LogiPluginService\Plugins\BlenderPlugin.link") -ErrorAction SilentlyContinue
```

In Options+, restart Logi Plugin Service from settings. If a previous load
crashed, the service can disable the plugin. The marker, when present, is:

```text
%LOCALAPPDATA%\Logi\LogiPluginService\Logs\plugin_crashes\BlenderPlugin.dll
```

Delete that marker only after you have read the log, then restart the service
again.

Confirm the log, and keep the log on the PC:

```text
%LOCALAPPDATA%\Logi\LogiPluginService\Logs\plugin_logs\Blender.log
```

A useful line is `Connected to the Blender bridge` once Blender is running
with the add-on enabled. `loaded from` says whether the `.link` or the
unpacked folder won.

## Still open

These were not in the PC check. Do not treat them as passed.

* Whether the ring overlay keeps or steals Blender's focus.
* Undo and Redo through the ring. Those actions are still keystrokes.
* Haptics. None were added.
* The profile changing when another application comes to the front.
* Whether `DefaultProfile72win.lp5` was the layout Options+ applied. The
  1.1.0 ring check was Edit Mode and Vertex, which can also be assigned from
  Installed Plugins onto an empty profile.

## Rollback

1. In Options+, remove the Blender plugin if the UI offers removal. Otherwise
   delete only this directory:

   ```text
   %LOCALAPPDATA%\Logi\LogiPluginService\Plugins\Blender
   ```

   Also delete `Plugins\BlenderPlugin.link` if it exists.
2. Restart Logi Plugin Service.
3. If a Blender ring profile was created and you want it gone, delete that
   profile from the profile menu in Options+. Deleting
   `%LOCALAPPDATA%\Logi\LogiPluginService\Applications\Loupedeck72\@_blender`
   removes the on-disk Blender ring application for device type Loupedeck72.
   Stop Logi Plugin Service first, and do not delete sibling application
   folders. Do not delete or edit `settings.db`.
4. In Blender, disable and remove **MX Console Bridge**, then restart Blender.
5. The macOS keypad and dialpad profiles in this repository were not modified.
   Nothing in this rollback touches a Mac.

## Known limits

* Pairing off means any local program can call an allowlisted action on
  `127.0.0.1:47800`.
* A portable Blender, or a Store install outside the probed directories, can
  stay unreported until the process name `blender` is seen.
* The published DLL is the Windows build from this PC, not the earlier
  `dist/Blender-windows-1.1.lplug4` pack.
