#!/usr/bin/env python3
# Regression checks for the Windows Actions Ring packaging.
# These do not load Logi Plugin Service, Options+, or Blender.

import hashlib
import json
import os
import pathlib
import re
import sys
import tempfile
import unittest
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "blender-addon"))

import make_profiles  # noqa: E402

MAC_PROFILES = {
    "DefaultProfile70.lp5": "7efe6fc28f58930f5f20f53177cd216c07d3ef3ed5bef5be904de4aa29e749b0",
    "DefaultProfile71.lp5": "5cc047d84482d5fe9fe9633dc9f35fc022c5d0101ba13078966208976bd87dd2",
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_bridge():
    import types

    bpy = types.ModuleType("bpy")
    bpy.app = types.SimpleNamespace(
        timers=types.SimpleNamespace(
            is_registered=lambda *args, **kwargs: False,
            register=lambda *args, **kwargs: None,
            unregister=lambda *args, **kwargs: None,
        )
    )
    bpy.context = types.SimpleNamespace()

    class _Prop:
        def __init__(self, **kwargs):
            pass

    class _Type:
        pass

    bpy.types = types.SimpleNamespace(AddonPreferences=_Type, Operator=_Type)
    bpy.props = types.SimpleNamespace(IntProperty=_Prop, StringProperty=_Prop)
    bpy.utils = types.SimpleNamespace(
        register_class=lambda *args, **kwargs: None,
        unregister_class=lambda *args, **kwargs: None,
    )
    sys.modules["bpy"] = bpy
    import blender_mx_bridge  # noqa: WPS433

    return blender_mx_bridge


BRIDGE = load_bridge()


class ManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        text = (ROOT / "BlenderPlugin/src/package/metadata/LoupedeckPackage.yaml").read_text()
        cls.text = text

    def test_windows_folder_and_existing_mac_folder(self):
        self.assertIn("pluginFolderWin: bin", self.text)
        self.assertIn("pluginFolderMac: bin", self.text)

    def test_device_family_is_not_an_invented_mouse_id(self):
        self.assertIn("- LoupedeckExtendedFamily", self.text)
        self.assertIn("- LogitechCreativeFamily", self.text)
        self.assertNotIn("MXMaster4", self.text)
        self.assertNotIn("ActionsRing", self.text)

    def test_windows_process_pattern_matches_getprocessname(self):
        self.assertIn("processNamePattern: ^blender$", self.text)
        self.assertIn("executablePathPattern: (?i)blender\\.exe$", self.text)
        self.assertIn("bundleNamePattern: ^org\\.blenderfoundation\\.blender$", self.text)

    def test_license_stays_gpl_and_points_at_the_fork(self):
        self.assertIn("license: GPL-3.0-or-later", self.text)
        self.assertIn("https://github.com/amooney1/blender-mx-creative", self.text)
        self.assertIn("xfanta/blender-mx-creative", self.text)
        self.assertNotIn("license: MIT", self.text)
        self.assertIn("version: 1.1.1", self.text)


class ProfileTests(unittest.TestCase):
    def test_mac_profiles_are_byte_for_byte_unchanged(self):
        directory = ROOT / "BlenderPlugin/src/package/profiles"
        for name, digest in MAC_PROFILES.items():
            self.assertEqual(sha256(directory / name), digest)

    def test_ring_template_is_eight_windows_press_slots(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "DefaultProfile72win.lp5"
            make_profiles.write_actions_ring(path)
            committed = ROOT / "BlenderPlugin/src/package/profiles/DefaultProfile72win.lp5"
            self.assertEqual(path.read_bytes(), committed.read_bytes())
            with zipfile.ZipFile(path) as archive:
                names = set(archive.namelist())
                self.assertEqual(names, {"ApplicationInfo.json", "ProfileInfo.json", "ApplicationIcon.png"})
                info = json.loads(archive.read("ProfileInfo.json"))
                app = json.loads(archive.read("ApplicationInfo.json"))
        self.assertEqual(info["deviceType"], "Loupedeck72")
        self.assertEqual(app["processOrBundleName"], "blender")
        self.assertEqual(app["nativePluginName"], "Blender")
        self.assertNotIn("org.blenderfoundation.blender", json.dumps(app))
        pages = info["layout"]["layoutModes"][0]["workspaces"][0]["pressPages"]
        self.assertEqual(len(pages), 1)
        controls = pages[0]["controls"]
        self.assertEqual([item["controlId"] for item in controls], list(range(8)))
        joined = json.dumps(info)
        self.assertNotIn("/Users/", joined)
        self.assertNotIn("C:\\\\Users", joined)
        self.assertNotIn("@", joined.replace("@_blender", "").replace("$Blender", ""))
        for control in controls:
            self.assertIsNone(control["rotateAction"])
            self.assertTrue(control["pressAction"].startswith("$Blender___Loupedeck.BlenderPlugin."))

    def test_ring_only_regeneration_does_not_touch_mac_profiles(self):
        before = {
            name: (ROOT / "BlenderPlugin/src/package/profiles" / name).read_bytes()
            for name in MAC_PROFILES
        }
        make_profiles.main(["--ring"])
        for name, payload in before.items():
            self.assertEqual((ROOT / "BlenderPlugin/src/package/profiles" / name).read_bytes(), payload)


class BridgePolicyTests(unittest.TestCase):
    def test_shipped_operators_are_allowed_and_arbitrary_ones_are_not(self):
        names = set()
        for path in (ROOT / "BlenderPlugin/src/Actions").glob("*.cs"):
            names.update(re.findall(r'name = "([A-Za-z0-9_.]+)"', path.read_text()))
        self.assertTrue(names)
        self.assertTrue(names <= set(BRIDGE._OP_POLICY))
        for name in names:
            exec_name, rules = BRIDGE._OP_POLICY[name]
            props = {}
            if "action" in rules:
                props["action"] = "SELECT"
            elif "mode" in rules:
                props["mode"] = "OBJECT"
            elif rules.get("value") == "flatten-axis":
                props["value"] = [0, 1, 1]
            self.assertEqual(
                BRIDGE._validate_op({"name": name, "exec": exec_name, "props": props})[0],
                name,
            )

        for blocked in ("wm.quit", "script.python_file_run", "ed.undo", "importlib.reload"):
            with self.assertRaises(ValueError):
                BRIDGE._validate_op({"name": blocked, "exec": "EXEC"})

    def test_property_and_scale_bounds(self):
        with self.assertRaises(ValueError):
            BRIDGE._validate_op({
                "name": "mesh.select_all",
                "exec": "EXEC",
                "props": {"action": "SELECT", "extra": True},
            })
        with self.assertRaises(ValueError):
            BRIDGE._validate_op({
                "name": "transform.resize",
                "exec": "EXEC",
                "props": {"value": [2, 2, 2]},
            })
        checked = BRIDGE._validate_op({
            "name": "transform.resize",
            "exec": "EXEC",
            "props": {"value": [1, 1, 0]},
        })
        self.assertEqual(checked[2]["value"], [1.0, 1.0, 0.0])
        with self.assertRaises(ValueError):
            BRIDGE._validate_select_types(["OBJECT"])
        self.assertEqual(BRIDGE._validate_select_types(["VERT", "EDGE"]), ["VERT", "EDGE"])

    def test_failures_are_codes_without_paths_or_tracebacks(self):
        leaked = r"C:\Users\Alex\Documents\secret.blend"
        unknown = BRIDGE._handle({"cmd": leaked})
        failed = BRIDGE._failure_response(RuntimeError(leaked))
        rejected = BRIDGE._failure_response(ValueError("operator is not allowed: " + leaked))
        oversized = BRIDGE._client_error("request_too_large")
        for response in (unknown, failed, rejected, oversized):
            blob = json.dumps(response)
            self.assertNotIn("trace", response)
            self.assertNotIn("Users", blob)
            self.assertNotIn("secret.blend", blob)
            self.assertNotIn(leaked, blob)
            self.assertIn(response["error"], BRIDGE._CLIENT_ERRORS)
            self.assertEqual(response["message"], BRIDGE._CLIENT_ERRORS[response["error"]])
            self.assertFalse(response["ok"])
        self.assertEqual(unknown["error"], "unknown_command")
        self.assertEqual(failed["error"], "failed")
        self.assertEqual(rejected["error"], "rejected")
        source = (ROOT / "blender-addon/blender_mx_bridge/__init__.py").read_text()
        self.assertNotIn("format_exc", source)
        self.assertNotIn('"trace"', source)

    def test_pairing_stays_off_until_a_token_is_configured(self):
        self.assertTrue(BRIDGE._check_auth({"cmd": "state"}, ""))
        self.assertTrue(BRIDGE._check_auth({"cmd": "state", "auth": "ignored"}, ""))
        self.assertFalse(BRIDGE._check_auth({"cmd": "state"}, "local-secret"))
        self.assertFalse(BRIDGE._check_auth({"cmd": "state", "auth": "wrong"}, "local-secret"))
        self.assertTrue(BRIDGE._check_auth({"cmd": "state", "auth": "local-secret"}, "local-secret"))
        self.assertFalse(BRIDGE._check_auth({"cmd": "state"}, None))
        self.assertEqual(BRIDGE._configured_token(), "")
        denied = BRIDGE._client_error("unauthorized")
        self.assertNotIn("local-secret", json.dumps(denied))

    def test_line_cap_rejects_oversized_frames(self):
        kind, _, _ = BRIDGE._consume_line(b'{"cmd":"ping"}\n')
        self.assertEqual(kind, "line")
        kind, _, rest = BRIDGE._consume_line(b"x" * (BRIDGE.MAX_LINE_BYTES + 1))
        self.assertEqual(kind, "overflow")
        self.assertEqual(rest, b"")
        kind, _, _ = BRIDGE._consume_line(b"x" * 20)
        self.assertEqual(kind, "wait")


class PackageTests(unittest.TestCase):
    def test_package_exposes_ring_profile_without_host_dlls(self):
        import package_plugin

        with tempfile.TemporaryDirectory() as tmp:
            directory = pathlib.Path(tmp)
            lplug = directory / "Blender-windows-1.1.lplug4"
            addon = directory / "bridge.zip"
            package_plugin.main = None
            saved = sys.argv
            sys.argv = ["package_plugin.py", "--lplug4", str(lplug), "--addon-zip", str(addon)]
            try:
                package_plugin.main = __import__("package_plugin").main
                # Call the functions directly so argparse sees our paths.
                binaries = package_plugin.dll_from_upstream()
                package_plugin.write_zip(lplug, package_plugin.plugin_members(binaries))
                package_plugin.write_zip(addon, package_plugin.addon_members())
            finally:
                sys.argv = saved
            with zipfile.ZipFile(lplug) as archive:
                names = archive.namelist()
                lowered = [name.lower() for name in names]
                self.assertTrue(any(name.endswith("pluginapi.dll") for name in lowered) is False)
                self.assertIn("metadata/LoupedeckPackage.yaml", names)
                self.assertIn("profiles/DefaultProfile70.lp5", names)
                self.assertIn("profiles/DefaultProfile71.lp5", names)
                self.assertIn("profiles/DefaultProfile72win.lp5", names)
                self.assertIn("bin/BlenderPlugin.dll", names)
                self.assertNotIn("metadata/PackageHash.bin", names)
                yaml = archive.read("metadata/LoupedeckPackage.yaml").decode()
                self.assertIn("pluginFolderWin: bin", yaml)
                mac70 = archive.read("profiles/DefaultProfile70.lp5")
                mac71 = archive.read("profiles/DefaultProfile71.lp5")
            self.assertEqual(hashlib.sha256(mac70).hexdigest(), MAC_PROFILES["DefaultProfile70.lp5"])
            self.assertEqual(hashlib.sha256(mac71).hexdigest(), MAC_PROFILES["DefaultProfile71.lp5"])
            with zipfile.ZipFile(addon) as archive:
                manifest = archive.read("blender_manifest.toml").decode()
            self.assertIn('version = "1.1.1"', manifest)
            self.assertIn("127.0.0.1", manifest)

    def test_project_keeps_the_mac_pluginapi_path(self):
        text = (ROOT / "BlenderPlugin/src/BlenderPlugin.csproj").read_text()
        self.assertIn("/Applications/Utilities/LogiPluginService.app/Contents/MonoBundle/", text)
        self.assertIn("LOGI_PLUGIN_API_DIR", text)
        self.assertIn("<Private>false</Private>", text)
        self.assertIn("~/Library/Application\\ Support/Logi/LogiPluginService/Plugins/", text)
        post_build = text.split('<Target Name="PostBuild"', 1)[1].split("</Target>", 1)[0]
        self.assertIn("BlenderPluginDevLink)' == 'true'", post_build)
        self.assertIn("loupedeck:plugin/$(PluginShortName)/reload", post_build)
        package_only = text.split('<Target Name="PostBuildPackageOnly"', 1)[1].split("</Target>", 1)[0]
        self.assertIn("BlenderPluginDevLink)' != 'true'", package_only)
        self.assertNotIn("<Exec", package_only)
        self.assertNotIn("<Delete", package_only)
        script = (ROOT / "tools/windows_build.ps1").read_text()
        self.assertIn("-p:BlenderPluginDevLink=false", script)
        self.assertNotIn("$env:LOGI_PLUGIN_DIR", script)

    def test_devlink_property_defaults_on_and_package_build_turns_it_off(self):
        import shutil
        import subprocess

        dotnet = shutil.which("dotnet")
        if dotnet is None:
            self.skipTest("dotnet is not on PATH")
        project = ROOT / "BlenderPlugin/src/BlenderPlugin.csproj"
        env = dict(os.environ)
        default = subprocess.run(
            [dotnet, "msbuild", str(project), "-getProperty:BlenderPluginDevLink", "-nologo"],
            check=False, capture_output=True, text=True, env=env,
        )
        self.assertEqual(default.returncode, 0, default.stdout + default.stderr)
        self.assertEqual(default.stdout.strip(), "true")
        packaged = subprocess.run(
            [dotnet, "msbuild", str(project), "-getProperty:BlenderPluginDevLink",
             "-p:BlenderPluginDevLink=false", "-nologo"],
            check=False, capture_output=True, text=True, env=env,
        )
        self.assertEqual(packaged.returncode, 0, packaged.stdout + packaged.stderr)
        self.assertEqual(packaged.stdout.strip(), "false")


if __name__ == "__main__":
    unittest.main()
