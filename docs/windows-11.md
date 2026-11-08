# Windows 11 — Actions Ring package

This is a packaging and application-detection change for the existing Blender
plugin. It is not a new plugin and it has not been loaded in Logi Options+ or
on an MX Master 4. Linux checks in this repository do not stand in for that.

The plugin is already a Logi Actions SDK `plugin4` package. Its buttons are
`PluginDynamicCommand` actions and its dials are `PluginDynamicAdjustment`
actions. The C# introduction tells you to open Actions Ring, MX Creative
Keypad, or MX Creative Dialpad and look under **All Actions → Installed
Plugins**. A missing keypad does not mean the actions are console-only. What
this tree could not check is whether Options+ on this PC actually lists them,
whether a default ring profile is applied, and whether a press reaches Blender
while the ring overlay has focus.

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
  macOS `/Applications/Blender.app` check is unchanged. That install probe is
  in source and is **not** in the prebuilt DLL until the project is rebuilt
  against the PC's `PluginApi.dll`.
* `profiles/DefaultProfile72win.lp5` is an eight-button template for device
  type `Loupedeck72`: Vertex, Edge, Face, Edit Mode, Extrude, Inset, Undo,
  Redo. `DefaultProfile70.lp5` and `DefaultProfile71.lp5` are byte-for-byte
  the previous files. Undo and Redo are still keystrokes, because Blender
  refuses `ed.undo` / `ed.redo` from the add-on. The other ring slots use the
  bridge first.
* The add-on still listens on `127.0.0.1:47800`. It now refuses operators that
  the plugin does not send, and it refuses a request line over 8192 bytes.
  There is no shell, no new port, and no pairing secret. A pairing secret
  would have broken the existing Mac plugin.

Marketplace approval guidelines exclude GPL-2.0 and GPL-3.0. This package
stays GPL-3.0-or-later and is not claimed to be Marketplace-eligible.

## Files to copy to the PC

From `dist/` after the pack step, or from the artifact bundle:

* `Blender-windows-1.1.lplug4`
* `blender_mx_bridge-1.1.0.zip`

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

The prebuilt `.lplug4` can be installed without the .NET SDK. The SDK is only
needed for the rebuild below. Upstream required Logi Plugin Service 6.4
because that host was .NET 10, and this assembly targets `net10.0`. Record the
host version you actually have. An older host may refuse the DLL.

## Optional rebuild, so Windows install detection is in the DLL

Skip this if `PluginApi.dll` or the .NET 10 SDK is missing. The prebuilt
package still contains the upstream assembly, which already exposes the
actions. It reports Blender as installed only when `/Applications/Blender.app`
exists, so on Windows the application can stay "unknown" until you rebuild.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\windows_build.ps1
```

If the DLL is not in a default directory:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\windows_build.ps1 -PluginApiDir "D:\path\to\the\directory"
```

The script refuses `-Install`. It writes `dist\Blender-windows-1.1.lplug4`
from the new build. `tools\windows_build.ps1` does not copy `PluginApi.dll`
into that package.

## Install the add-on

1. Use a disposable `.blend`. Do not point this at a real production file.
2. Blender → Edit → Preferences → Add-ons → the menu → **Install from Disk…**
   → `blender_mx_bridge-1.1.0.zip`.
3. Enable **MX Console Bridge** if it did not enable itself.
4. **Save Preferences**.
5. In the Blender system console, or Window → Toggle System Console, look for
   `listening on 127.0.0.1:47800`.
6. Restart Blender after any later replacement of the add-on. Installing over
   the files does not unload the old module.

The add-on does not need an internet connection. It binds `127.0.0.1` only.

## Install the plugin

`logiplugintool install` from a terminal failed on the Mac this project was
built on. Unpack by hand. Quit is not required for the copy, but restart the
plugin service afterwards.

```powershell
$plugins = Join-Path $env:LOCALAPPDATA "Logi\LogiPluginService\Plugins\Blender"
if (Test-Path $plugins) { Remove-Item -LiteralPath $plugins -Recurse -Force }
New-Item -ItemType Directory -Force -Path $plugins | Out-Null
Expand-Archive -LiteralPath .\dist\Blender-windows-1.1.lplug4 -DestinationPath $plugins -Force
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

## Checks that have to happen on this PC

Do these with the MX Master 4 and with no requirement that an MX Creative
Console be attached. Stop and write down the first one that fails. Do not
describe a failed check as a pass.

1. Open Options+ customization for the **Actions Ring**. Open **All Actions →
   Installed Plugins**. Record whether **Blender** is listed.
2. Record the action names you see. They should be the existing groups
   (Select Mode, Mode, Selection, Mesh Tools, Toggles, Pivot Point,
   Orientation, History, and the two dials), not a new ring-only plugin.
3. Create a new Blender application profile for the Actions Ring, or use the
   one Options+ created. Record whether the eight default slots are filled.
   An empty profile is still a useful result: the SDK creates an empty profile
   when it does not accept a default, and the actions can be dragged on from
   Installed Plugins. The hand-written `DefaultProfile72win.lp5` was not
   exported by Options+, so rejection is possible.
4. With a disposable mesh in Blender and the add-on listening, focus Blender
   and press **Edit Mode** on the ring using both ring gestures you normally
   use (press/release then a bubble, and hold/hover/release if that is how
   this mouse opens the ring). Record whether Blender toggled Edit Mode, and
   whether the ring overlay stole focus so the command did nothing.
5. Press **Vertex** in Edit Mode. Record whether the select mode changed and
   whether `Blender.log` shows the bridge connected.
6. Press **Undo**. This one is a Ctrl+Z keystroke. Record whether it undid the
   select-mode change or whether the keystroke went to the ring overlay.
7. Alt-Tab to another application and open the ring again. Record whether the
   Blender profile stays up. It should leave with Blender.
8. Disable the add-on, restart Blender, and press **Edit Mode** again. The
   plugin should fall back to the Tab key only when the bridge is unreachable.
   Record which of those happened.

Also record the Blender version. The add-on manifest allows 4.2.0 and later.
That is not a claim that every 4.2+ build was tried. The Mac install that
exists today was Blender 5.2.3.

Leave mouse-button mappings, keyboard shortcuts outside this plugin, and every
other application's profile alone.

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

* Ring focus, live redraw while the ring stays open, and whether the default
  profile is accepted are untested.
* Haptics were not added.
* A portable Blender, or a Store install outside the probed directories, stays
  "not detected" until the process name `blender` is seen, and until the
  probe is actually compiled into the DLL.
* The prebuilt DLL was produced on macOS for .NET 10. It is IL, with no native
  image in the package. Loading it on Windows is the first PC check, not a
  completed one.
