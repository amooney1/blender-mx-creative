# Windows 1.1.1 packages

These are the packages checked on one Windows 11 PC. They are part of this
GPL-3.0-or-later tree. See [LICENSE](../../LICENSE) and [NOTICE.md](../../NOTICE.md).

Upstream project: [xfanta/blender-mx-creative](https://github.com/xfanta/blender-mx-creative).
This fork is not a Logitech Marketplace listing and it does not include
`PluginApi.dll`.

| File | SHA-256 |
| --- | --- |
| `Blender-windows-1.1.1.lplug4` | `d02375b5ac2ee63a5a5d86843e7175681d15fdf0dc6875a1f5550dad98b5433d` |
| `blender_mx_bridge-1.1.1.zip` | `62fb7bfaff1586b6e4bee91814619efe6a95904b9f3cb3ac1779cfe52e58d658` |

The plugin DLL inside the `.lplug4` is `bin/BlenderPlugin.dll`, SHA-256
`c2a31284962a2e586bcf7a890e2919322574cd4bb22d8c4cd1325bebce73ff06`,
assembly version 1.1.1.0.

`dist/Blender-windows-1.1.lplug4` is an earlier pack of the upstream assembly.
It is not this tested Windows build.

Install and rollback: [docs/windows-11.md](../../docs/windows-11.md).

Pairing ships off. The bridge listens on `127.0.0.1:47800` only, and any
local program can invoke an allowlisted action until a token is set on both
sides. Leave the add-on token blank and do not create `bridge.token`.
