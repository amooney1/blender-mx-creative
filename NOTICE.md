# Attribution

This project is licensed under **GPL-3.0-or-later** (see `LICENSE`). That is not
an arbitrary choice — it follows from what it is built on.

## Why GPL

Two things force it:

* **Blender's UI icons.** `BlenderPlugin/src/Icons/Blender/` holds 39 SVGs taken
  from Blender's source tree (`release/datafiles/icons_svg/`). Blender is GNU GPL
  v3 or later, so these files carry that licence, and so must anything that
  redistributes them — including `dist/Blender.lplug4`.
* **The add-on.** `blender-addon/blender_mx_bridge/` imports `bpy`. Blender's
  licensing page is explicit that the Python API is an integral part of the
  software and that published scripts must be shared under a GPL compliant
  licence.

Only the icons' `viewBox` has been rewritten, by `tools/normalize_icons.py`; the
drawings themselves are unchanged.

## Original artwork

`BlenderPlugin/src/Icons/Tools/` — extrude, inset, subdivide, loop cut, knife and
merge — are drawn from scratch to match Blender's icon style, because Blender ships
those tool icons only in its internal `VCO` binary format. They are original work,
released under the same GPL-3.0-or-later as the rest of the project.

## Trademark

`BlenderPlugin/src/package/metadata/Icon256x256.png` is Blender's own application
icon, extracted from `Blender.app` and cropped to fill its canvas. The Blender logo
is a trademark of the Blender Foundation and is used here only to identify which
application this plugin drives.

This project is not affiliated with, endorsed by, or supported by the Blender
Foundation or Logitech.

## Fork

The Windows packaging in this repository is a derivative of Michal Fanta's
[xfanta/blender-mx-creative](https://github.com/xfanta/blender-mx-creative),
under the same GPL-3.0-or-later terms. The icon attribution above is unchanged.
Logitech's Marketplace approval guidelines exclude GPL-2.0 and GPL-3.0, so this
package is not Marketplace-eligible and it does not ship Logi Plugin Service's
`PluginApi.dll`. The tested Windows files in `release/1.1.1/` are the same
GPL-3.0-or-later work.
