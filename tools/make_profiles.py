#!/usr/bin/env python3
# Blender MX Creative - drive Blender from a Logitech MX Creative Console
# Copyright (C) 2026 Michal Fanta
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>.

"""Generate the default .lp5 profiles shipped with the plugin.

A .lp5 is a zip holding ApplicationInfo.json and ProfileInfo.json. Action names
follow "$<plugin>___<action class>___<parameter>"; run

    logiplugintool xliff Blender <dir>

(or open loupedeck://plugin/Blender/xliff) against a loaded plugin to list them.

Writes BlenderPlugin/src/package/profiles/DefaultProfile70.lp5 (MX Creative
Keypad, 9 keys per page) and DefaultProfile71.lp5 (Dialpad, 4 buttons + 2 dials).

Also writes DefaultProfile72win.lp5, an eight-button Actions Ring template for
Windows. The macOS keypad and dialpad files are still produced by a full run,
which assigns them fresh ids. `python3 tools/make_profiles.py --ring` rewrites
only the ring file, with fixed ids, and leaves 70 and 71 untouched.
"""

import json
import pathlib
import sys
import uuid
import zipfile
from datetime import datetime, timezone

PLUGIN = "Blender"
APPLICATION = "@_blender"
NS = "Loupedeck.Service"

ROOT = pathlib.Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "BlenderPlugin" / "src" / "package"
OUT = PACKAGE / "profiles"
# Options+ copies this into the application's folder the first time the profile is
# created, and never refreshes it afterwards - so it has to be right up front.
APPLICATION_ICON = PACKAGE / "metadata" / "Icon256x256.png"


def guid():
    return uuid.uuid4().hex.upper()


def action(cls, parameter=None):
    name = f"${PLUGIN}___Loupedeck.BlenderPlugin.{cls}"
    return f"{name}___{parameter}" if parameter else name


# Keypad pages, nine keys each, read left to right and top to bottom.
KEYPAD_PAGES = [
    ("Select", [
        ("SelectModeCommand", "vert"),
        ("SelectModeCommand", "edge"),
        ("SelectModeCommand", "face"),
        ("ModeCommand", "toggle_edit"),
        ("OverlayToggleCommand", "xray"),
        ("SelectModeCommand", "all"),
        ("SelectionCommand", "all"),
        ("SelectionCommand", "none"),
        ("SelectionCommand", "invert"),
    ]),
    ("Tools", [
        ("MeshToolCommand", "extrude"),
        ("MeshToolCommand", "inset"),
        ("MeshToolCommand", "bevel"),
        ("MeshToolCommand", "loopcut"),
        ("MeshToolCommand", "knife"),
        ("MeshToolCommand", "subdivide"),
        ("MeshToolCommand", "merge"),
        ("MeshToolCommand", "duplicate"),
        ("MeshToolCommand", "delete"),
    ]),
    ("Transform", [
        ("OverlayToggleCommand", "proportional"),
        ("OverlayToggleCommand", "snap"),
        ("OverlayToggleCommand", "automerge"),
        ("PivotCommand", "median"),
        ("PivotCommand", "cursor"),
        ("PivotCommand", "individual"),
        ("OrientationCommand", "global"),
        ("OrientationCommand", "normal"),
        ("OrientationCommand", "local"),
    ]),
    ("Finish", [
        ("SelectionCommand", "more"),
        ("SelectionCommand", "less"),
        ("SelectionCommand", "linked"),
        ("MeshToolCommand", "normals"),
        ("MeshToolCommand", "shade_smooth"),
        ("ModeCommand", "object"),
        ("ModeCommand", "sculpt"),
        ("HistoryCommand", "undo"),
        ("HistoryCommand", "redo"),
    ]),
    # Michal's own modelling loop: inset, close a face, delete, cut, and the
    # S Z 0 flatten, kept together on one page.
    ("Custom", [
        ("MeshToolCommand", "inset"),
        ("MeshToolCommand", "make_face"),
        ("MeshToolCommand", "delete"),
        ("MeshToolCommand", "knife"),
        ("MeshToolCommand", "merge"),
        ("MeshToolCommand", "extrude"),
        ("MeshToolCommand", "flatten_x"),
        ("MeshToolCommand", "flatten_y"),
        ("MeshToolCommand", "flatten_z"),
    ]),
]

DIALPAD_BUTTONS = [
    ("HistoryCommand", "undo"),
    ("HistoryCommand", "redo"),
    ("ModeCommand", "toggle_edit"),
    ("OverlayToggleCommand", "xray"),
]

DIALPAD_DIALS = [
    ("ProportionalSizeAdjustment", None),
    ("SubsurfLevelAdjustment", None),
]

# Eight press slots, the Actions Ring's controlId range 0-7. Adjustments stay
# in the action picker: scroll-on-a-bubble was not given a default here.
RING_SLOTS = [
    ("SelectModeCommand", "vert"),
    ("SelectModeCommand", "edge"),
    ("SelectModeCommand", "face"),
    ("ModeCommand", "toggle_edit"),
    ("MeshToolCommand", "extrude"),
    ("MeshToolCommand", "inset"),
    ("HistoryCommand", "undo"),
    ("HistoryCommand", "redo"),
]

# Stable identity so the Windows template does not change on every regeneration.
RING_PROFILE_ID = "B1E0D072A1114E0A9C0E478000000072"
RING_PAGE_ID = "B1E0D072A1114E0A9C0E478000000001"
RING_WORKSPACE_ID = "B1E0D072A1114E0A9C0E478000000002"
RING_MODIFIED = "2026-11-08T00:00:00Z"


def control(index, press=None, rotate=None):
    return {
        "$type": f"{NS}.Devices.Loupedeck7Devices.ProfileLayoutControl7, LoupedeckService",
        "controlId": index,
        "pressAction": press,
        "rotateAction": rotate,
    }


def page(display_name, controls, name=None):
    return {
        "$type": f"{NS}.Devices.Loupedeck7Devices.ProfileLayoutPage7, LoupedeckService",
        "name": name or guid(),
        "displayName": display_name,
        "description": None,
        "controls": controls,
    }


def layout(device, press_pages, rotate_pages, workspace_name=None):
    return {
        "$type": f"{NS}.Devices.Loupedeck7Devices.ProfileLayout7, LoupedeckService",
        "deviceType": device,
        "profileFlags": "None",
        "layoutModes": [{
            "$type": f"{NS}.Devices.Loupedeck7Devices.ProfileLayoutMode7, LoupedeckService",
            "deviceType": device,
            "modeName": "Main",
            "parentModeName": None,
            "actions": None,
            "dynamicButtonPages": None,
            "dynamicEncoderPages": None,
            "workspaces": [{
                "$type": f"{NS}.Devices.Loupedeck7Devices.ProfileLayoutWorkspace7, LoupedeckService",
                "name": workspace_name or guid(),
                "displayName": "Workspace 1",
                "description": None,
                "pressPages": press_pages,
                "rotatePages": rotate_pages,
            }],
            "folderPages": [],
        }],
        "folderPages": [],
    }


def profile(device, display_name, press_pages, rotate_pages,
             name=None, process_or_bundle=None, native_plugins=None,
             modified=None, workspace_name=None):
    name = name or guid()
    info = {
        "$type": f"{NS}.ApplicationProfile, LoupedeckService",
        "name": name,
        "profileFlags": "None",
        "displayName": display_name,
        "description": "",
        "deviceType": device,
        "applicationName": APPLICATION,
        "nativePluginName": PLUGIN,
        "hasNativePlugin": True,
        "additionalNativePluginNames": ["DefaultMac"] if native_plugins is None else native_plugins,
        "lastModifiedTimeUtc": modified or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "profileSettings": {
            "$type": "Loupedeck.DictionaryNoCase`1[[System.String, System.Private.CoreLib]], PluginApi"
        },
        "actionImages90": None,
        "actionImages60": None,
        "wheelImages": None,
        "actionColors": None,
        "layout": layout(device, press_pages, rotate_pages, workspace_name),
        "macroCommands": [],
        "macroAdjustments": [],
        "profileCommands": [],
        "profileAdjustments": [],
        "conversionHistory": None,
        "profileActions": [],
    }
    application = {
        "$type": f"{NS}.SupportedApplicationInfo, LoupedeckService",
        "name": APPLICATION,
        "displayName": "Blender",
        "description": None,
        "deviceType": device,
        "nativePluginName": PLUGIN,
        "hasNativePlugin": True,
        "processOrBundleName": process_or_bundle or "org.blenderfoundation.blender",
        "modes": [{
            "$type": f"{NS}.ApplicationMode, LoupedeckService",
            "name": "Main",
            "parentModeName": None,
            "displayName": "Main",
        }],
        "defaultProfileName": name,
        "isEnabled": True,
    }
    return info, application


def write(path, info, application):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("ApplicationInfo.json", json.dumps(application, indent=2))
        zf.writestr("ProfileInfo.json", json.dumps(info, indent=2))
        zf.write(APPLICATION_ICON, "ApplicationIcon.png")
    print(f"wrote {path.name}")


def write_fixed(path, info, application):
    """Zip with a fixed timestamp so the ring template is reproducible."""
    path.parent.mkdir(parents=True, exist_ok=True)
    members = {
        "ApplicationInfo.json": json.dumps(application, indent=2).encode("utf-8"),
        "ProfileInfo.json": json.dumps(info, indent=2).encode("utf-8"),
        "ApplicationIcon.png": APPLICATION_ICON.read_bytes(),
    }
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, payload in members.items():
            item = zipfile.ZipInfo(name, date_time=(2026, 11, 8, 0, 0, 0))
            item.compress_type = zipfile.ZIP_DEFLATED
            item.external_attr = 0o644 << 16
            zf.writestr(item, payload)
    print(f"wrote {path.name}")


def ring_profile():
    controls = [
        control(slot, press=action(cls, param))
        for slot, (cls, param) in enumerate(RING_SLOTS)
    ]
    pages = [page("Actions Ring", controls, name=RING_PAGE_ID)]
    return profile(
        "Loupedeck72",
        "Blender",
        pages,
        [],
        name=RING_PROFILE_ID,
        process_or_bundle="blender",
        native_plugins=["DefaultWin"],
        modified=RING_MODIFIED,
        workspace_name=RING_WORKSPACE_ID,
    )


def write_actions_ring(path=None):
    path = pathlib.Path(path) if path else OUT / "DefaultProfile72win.lp5"
    write_fixed(path, *ring_profile())
    return path


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv == ["--ring"]:
        write_actions_ring()
        return

    keypad_pages = [
        page(f"Page ({i + 1}) {title}",
             [control(slot, press=action(cls, param)) for slot, (cls, param) in enumerate(items)])
        for i, (title, items) in enumerate(KEYPAD_PAGES)
    ]
    write(OUT / "DefaultProfile70.lp5",
          *profile("Loupedeck70", "Blender", keypad_pages, []))

    buttons = [page("Page (1)", [control(slot, press=action(cls, param))
                                 for slot, (cls, param) in enumerate(DIALPAD_BUTTONS)])]
    dials = [page("Dial Page", [control(slot, rotate=action(cls, param))
                                for slot, (cls, param) in enumerate(DIALPAD_DIALS)])]
    write(OUT / "DefaultProfile71.lp5",
          *profile("Loupedeck71", "Blender", buttons, dials))
    write_actions_ring()


if __name__ == "__main__":
    main()
