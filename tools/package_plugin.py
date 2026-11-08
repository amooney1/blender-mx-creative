#!/usr/bin/env python3
# Blender MX Creative - GPL-3.0-or-later fork of xfanta/blender-mx-creative.
# Copyright (C) 2026 Michal Fanta and contributors.
#
# Packages the Options+ plugin and the Blender add-on. Does not copy
# PluginApi.dll. The plugin assembly is the upstream net10.0 IL build unless
# --dll points at a Windows rebuild.

import argparse
import hashlib
import pathlib
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "BlenderPlugin" / "src" / "package"
ADDON = ROOT / "blender-addon" / "blender_mx_bridge"
UPSTREAM = ROOT / "dist" / "Blender.lplug4"

FORBIDDEN = {
    "pluginapi.dll",
    "loupedeckservice.dll",
    "settings.db",
    "packagehash.bin",
}


def sha256(path):
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def dll_from_upstream():
    if not UPSTREAM.is_file():
        raise SystemExit(f"missing {UPSTREAM}; pass --dll")
    extracted = {}
    with zipfile.ZipFile(UPSTREAM) as archive:
        for name in ("bin/BlenderPlugin.dll", "bin/BlenderPlugin.deps.json", "bin/BlenderPlugin.pdb"):
            extracted[pathlib.PurePosixPath(name).name] = archive.read(name)
    return extracted


def dll_from_path(path):
    path = pathlib.Path(path)
    directory = path.parent
    files = {"BlenderPlugin.dll": path.read_bytes()}
    for extra in ("BlenderPlugin.deps.json", "BlenderPlugin.pdb"):
        candidate = directory / extra
        if candidate.is_file():
            files[extra] = candidate.read_bytes()
    return files


def write_zip(path, members):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(members):
            payload = members[name]
            lowered = pathlib.PurePosixPath(name).name.lower()
            if lowered in FORBIDDEN or name.lower().endswith("pluginapi.dll"):
                raise SystemExit(f"refusing to package {name}")
            info = zipfile.ZipInfo(name)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, payload)


def plugin_members(binaries):
    members = {}
    for source in PACKAGE.rglob("*"):
        if not source.is_file():
            continue
        relative = source.relative_to(PACKAGE).as_posix()
        members[relative] = source.read_bytes()
    for name, payload in binaries.items():
        members[f"bin/{name}"] = payload
    return members


def addon_members():
    return {
        "blender_manifest.toml": (ADDON / "blender_manifest.toml").read_bytes(),
        "__init__.py": (ADDON / "__init__.py").read_bytes(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dll", help="BlenderPlugin.dll from a Windows dotnet build")
    parser.add_argument("--lplug4", type=pathlib.Path, required=True)
    parser.add_argument("--addon-zip", type=pathlib.Path, required=True)
    args = parser.parse_args()

    binaries = dll_from_path(args.dll) if args.dll else dll_from_upstream()
    if "BlenderPlugin.dll" not in binaries:
        raise SystemExit("BlenderPlugin.dll is missing")
    write_zip(args.lplug4, plugin_members(binaries))
    write_zip(args.addon_zip, addon_members())
    print(f"{args.lplug4} {sha256(args.lplug4)}")
    print(f"{args.addon_zip} {sha256(args.addon_zip)}")


if __name__ == "__main__":
    main()
