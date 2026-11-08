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

# MX Console Bridge
#
# Listens on a loopback TCP socket and executes Blender commands sent by the
# Logi Options+ "Blender" plugin. The same plugin actions are what Options+
# shows for the MX Creative Console and, when the plugin is loaded, the
# Actions Ring. The socket is not a shell and it does not accept arbitrary
# operators.
#
# Protocol: newline-delimited JSON, one request per line, one response per line.
#   -> {"id": 1, "cmd": "select_mode", "args": {"types": ["VERT"]}}
#   <- {"id": 1, "ok": true, "state": {...}}
#
# Everything that touches bpy runs on Blender's main thread via a timer; the
# socket threads only queue work and wait for the result.

import json
import queue
import socket
import threading
import traceback

import bpy

HOST = "127.0.0.1"
DEFAULT_PORT = 47800
PROTOCOL_VERSION = 1
MAX_LINE_BYTES = 8192

# Operators the Options+ plugin sends. A local process can connect to this
# port, so names outside this table are rejected instead of being looked up
# on bpy.ops. Keep the names aligned with BlenderPlugin/src/Actions.
_OP_POLICY = {
    "mesh.select_all": ("EXEC", {"action": frozenset({"SELECT", "DESELECT", "INVERT"})}),
    "mesh.select_linked": ("EXEC", {}),
    "mesh.select_more": ("EXEC", {}),
    "mesh.select_less": ("EXEC", {}),
    "mesh.extrude_region_move": ("INVOKE", {}),
    "mesh.inset": ("INVOKE", {}),
    "mesh.bevel": ("INVOKE", {}),
    "mesh.loopcut_slide": ("INVOKE", {}),
    "mesh.knife_tool": ("INVOKE", {}),
    "mesh.subdivide": ("EXEC", {}),
    "mesh.merge": ("INVOKE", {}),
    "mesh.edge_face_add": ("EXEC", {}),
    "mesh.delete": ("INVOKE", {}),
    "mesh.duplicate_move": ("INVOKE", {}),
    "mesh.normals_make_consistent": ("EXEC", {}),
    "object.shade_smooth": ("EXEC", {}),
    "object.editmode_toggle": ("EXEC", {}),
    "object.mode_set": ("EXEC", {"mode": frozenset({"OBJECT", "SCULPT"})}),
    "transform.resize": ("EXEC", {"value": "flatten-axis"}),
}

_FLATTEN_VECTORS = (
    (0.0, 1.0, 1.0),
    (1.0, 0.0, 1.0),
    (1.0, 1.0, 0.0),
)

_SELECT_TYPES = frozenset({"VERT", "EDGE", "FACE"})

# Main-thread work queue. Items are (request_dict, result_holder, done_event).
_work = queue.Queue()

_server = None  # _BridgeServer instance while the add-on is enabled


# ---------------------------------------------------------------------------
# Context helpers
# ---------------------------------------------------------------------------

def _find_view3d():
    """Return (window, area, region, space) of a 3D viewport, or four Nones."""
    wm = bpy.context.window_manager
    # Prefer the window the user is actually looking at.
    windows = list(wm.windows)
    active = getattr(bpy.context, "window", None)
    if active in windows:
        windows.insert(0, windows.pop(windows.index(active)))
    for window in windows:
        screen = window.screen
        if screen is None:
            continue
        for area in screen.areas:
            if area.type != 'VIEW_3D':
                continue
            region = next((r for r in area.regions if r.type == 'WINDOW'), None)
            if region is None:
                continue
            return window, area, region, area.spaces.active
    return None, None, None, None


def _active_object():
    view_layer = getattr(bpy.context, "view_layer", None)
    return view_layer.objects.active if view_layer else None


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

def _subsurf_levels(obj):
    if obj is None:
        return None
    for mod in reversed(list(getattr(obj, "modifiers", []))):
        if mod.type == 'SUBSURF':
            return mod.levels
    return None


def _collect_state():
    scene = bpy.context.scene
    ts = scene.tool_settings if scene else None
    obj = _active_object()
    _, _, _, space = _find_view3d()

    select_mode = list(ts.mesh_select_mode) if ts else [True, False, False]
    orientation = None
    if scene and scene.transform_orientation_slots:
        orientation = scene.transform_orientation_slots[0].type

    return {
        "protocol": PROTOCOL_VERSION,
        "mode": obj.mode if obj else 'OBJECT',
        "object": obj.name if obj else None,
        "object_type": obj.type if obj else None,
        "select_vert": bool(select_mode[0]),
        "select_edge": bool(select_mode[1]),
        "select_face": bool(select_mode[2]),
        "xray": bool(space.shading.show_xray) if space else False,
        "proportional": bool(ts.use_proportional_edit) if ts else False,
        "proportional_size": round(ts.proportional_size, 4) if ts else 1.0,
        "proportional_falloff": ts.proportional_edit_falloff if ts else None,
        "snap": bool(ts.use_snap) if ts else False,
        "snap_elements": sorted(ts.snap_elements) if ts else [],
        "automerge": bool(ts.use_mesh_automerge) if ts else False,
        "pivot": ts.transform_pivot_point if ts else None,
        "orientation": orientation,
        "subsurf": _subsurf_levels(obj),
    }


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def _cmd_ping(args):
    return {"version": PROTOCOL_VERSION, "blender": bpy.app.version_string}


def _cmd_state(args):
    return {}


def _unit_component(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("scale component is not allowed")
    number = float(value)
    if number not in (0.0, 1.0):
        raise ValueError("scale component is not allowed")
    return number


def _validate_op(args):
    """Return (name, exec context, props) or raise ValueError."""
    if not isinstance(args, dict):
        raise ValueError("op args must be an object")
    name = args.get("name")
    policy = _OP_POLICY.get(name)
    if policy is None:
        raise ValueError("operator is not allowed")
    exec_name, prop_rules = policy
    if args.get("exec", "INVOKE") != exec_name:
        raise ValueError("operator execution context is not allowed")
    props = args.get("props") or {}
    if not isinstance(props, dict):
        raise ValueError("op props must be an object")
    if set(props) - set(prop_rules):
        raise ValueError("operator property is not allowed")
    if set(prop_rules) - set(props):
        raise ValueError("operator property is missing")
    checked = {}
    for key, rule in prop_rules.items():
        value = props[key]
        if rule == "flatten-axis":
            if not isinstance(value, list) or len(value) != 3:
                raise ValueError("scale value is not allowed")
            vector = tuple(_unit_component(part) for part in value)
            if vector not in _FLATTEN_VECTORS:
                raise ValueError("scale value is not allowed")
            checked[key] = [vector[0], vector[1], vector[2]]
        elif value not in rule:
            raise ValueError("operator property value is not allowed")
        else:
            checked[key] = value
    return name, exec_name, checked


def _validate_select_types(types):
    if not isinstance(types, list) or not 1 <= len(types) <= 3:
        raise ValueError("select_mode types must be 1 to 3 of VERT, EDGE, FACE")
    if any(item not in _SELECT_TYPES for item in types):
        raise ValueError("select_mode type is not allowed")
    return types


def _consume_line(buffer):
    """Split one request off a TCP buffer.

    Returns ("line", line, rest), ("wait", b"", buffer) or
    ("overflow", b"", rest). A line longer than MAX_LINE_BYTES is refused.
    """
    if b"\n" in buffer:
        line, _, rest = buffer.partition(b"\n")
        if len(line) > MAX_LINE_BYTES:
            return "overflow", b"", rest
        return "line", line, rest
    if len(buffer) > MAX_LINE_BYTES:
        return "overflow", b"", b""
    return "wait", b"", buffer


def _cmd_select_mode(args):
    """Set the mesh select mode. types is any of VERT / EDGE / FACE.

    In edit mode this goes through the same operator Blender's own 1/2/3 keys
    call. Writing tool_settings.mesh_select_mode directly does change the value,
    but it skips the selection flush between modes and leaves the viewport
    showing the old one - which looks exactly like the button doing nothing.
    """
    types = _validate_select_types(args.get("types") or ["VERT"])
    obj = _active_object()

    if obj is not None and obj.mode == 'EDIT':
        window, area, region, _ = _find_view3d()
        if area is not None:
            with bpy.context.temp_override(window=window, area=area, region=region):
                for index, select_type in enumerate(types):
                    bpy.ops.mesh.select_mode(type=select_type, use_extend=index > 0)
            return {}

    # Outside edit mode there is nothing to flush; just remember the choice.
    bpy.context.scene.tool_settings.mesh_select_mode = (
        'VERT' in types,
        'EDGE' in types,
        'FACE' in types,
    )
    return {}


def _cmd_op(args):
    """Run one allowlisted Blender operator.

    args: {"name": "mesh.extrude_region_move", "exec": "INVOKE"|"EXEC",
           "props": {...}}

    Note that ed.undo / ed.redo cannot be driven from here - Blender rejects
    them outside its own event loop - so the plugin sends those as keystrokes.
    """
    name, exec_name, props = _validate_op(args)
    module, _, func = name.partition(".")
    op = getattr(getattr(bpy.ops, module), func)

    exec_ctx = 'INVOKE_DEFAULT' if exec_name == "INVOKE" else 'EXEC_DEFAULT'

    window, area, region, _ = _find_view3d()
    if area is None:
        raise RuntimeError("no 3D viewport open")

    with bpy.context.temp_override(window=window, area=area, region=region):
        result = op(exec_ctx, **props)
    return {"result": list(result)}


_TOGGLES = {
    "xray": ("space", "shading.show_xray"),
    "proportional": ("tool_settings", "use_proportional_edit"),
    "proportional_connected": ("tool_settings", "use_proportional_connected"),
    "snap": ("tool_settings", "use_snap"),
    "automerge": ("tool_settings", "use_mesh_automerge"),
}


def _resolve(root, path):
    """Return (owner, attribute_name) for a dotted path."""
    parts = path.split(".")
    for part in parts[:-1]:
        root = getattr(root, part)
    return root, parts[-1]


def _toggle_target(what):
    if what not in _TOGGLES:
        raise ValueError("unknown toggle: %s" % what)
    scope, path = _TOGGLES[what]
    if scope == "space":
        _, _, _, space = _find_view3d()
        if space is None:
            raise RuntimeError("no 3D viewport open")
        root = space
    else:
        root = bpy.context.scene.tool_settings
    return _resolve(root, path)


def _cmd_toggle(args):
    owner, attr = _toggle_target(args.get("what"))
    value = args.get("value")
    setattr(owner, attr, (not getattr(owner, attr)) if value is None else bool(value))
    return {}


def _set_subsurf(value):
    obj = _active_object()
    if obj is None:
        raise RuntimeError("no active object")
    mod = next((m for m in reversed(list(obj.modifiers)) if m.type == 'SUBSURF'), None)
    if mod is None:
        mod = obj.modifiers.new(name="Subdivision", type='SUBSURF')
    mod.levels = max(0, min(int(value), 6))


_SETTERS = {
    "pivot": lambda v: setattr(bpy.context.scene.tool_settings, "transform_pivot_point", v),
    "orientation": lambda v: setattr(bpy.context.scene.transform_orientation_slots[0], "type", v),
    "proportional_falloff": lambda v: setattr(
        bpy.context.scene.tool_settings, "proportional_edit_falloff", v),
    "proportional_size": lambda v: setattr(
        bpy.context.scene.tool_settings, "proportional_size", max(0.0001, float(v))),
    "subsurf": _set_subsurf,
}


def _cmd_set(args):
    what = args.get("what")
    if what not in _SETTERS:
        raise ValueError("unknown setting: %s" % what)
    _SETTERS[what](args.get("value"))
    return {}


def _cmd_snap_elements(args):
    """Replace the active snap elements, e.g. ["VERTEX"] or ["EDGE","FACE"]."""
    elements = args.get("elements") or ["INCREMENT"]
    bpy.context.scene.tool_settings.snap_elements = set(elements)
    return {}


def _cmd_adjust(args):
    """Relative adjustment driven by a dial. delta is in detents."""
    what = args.get("what")
    delta = int(args.get("delta", 0))
    ts = bpy.context.scene.tool_settings

    if what == "proportional_size":
        # Geometric so the dial feels the same at every scale.
        factor = 1.1 ** delta
        ts.proportional_size = max(0.0001, min(ts.proportional_size * factor, 10000.0))
        return {}

    if what == "subsurf":
        obj = _active_object()
        if obj is None:
            raise RuntimeError("no active object")
        mod = next((m for m in reversed(list(obj.modifiers)) if m.type == 'SUBSURF'), None)
        if mod is None:
            mod = obj.modifiers.new(name="Subdivision", type='SUBSURF')
            mod.levels = 0
        mod.levels = max(0, min(mod.levels + delta, 6))
        return {}

    raise ValueError("unknown adjustment: %s" % what)


_HANDLERS = {
    "ping": _cmd_ping,
    "state": _cmd_state,
    "select_mode": _cmd_select_mode,
    "op": _cmd_op,
    "toggle": _cmd_toggle,
    "set": _cmd_set,
    "snap_elements": _cmd_snap_elements,
    "adjust": _cmd_adjust,
}


def _tag_redraw():
    """Ask every area to redraw.

    Commands that write to bpy.data rather than going through an operator leave
    the interface showing stale values until something else happens to trigger a
    redraw. Toggles and pivot/orientation changes are all in that category.
    """
    for window in bpy.context.window_manager.windows:
        screen = window.screen
        if screen is None:
            continue
        for area in screen.areas:
            area.tag_redraw()


def _handle(request):
    cmd = request.get("cmd")
    handler = _HANDLERS.get(cmd)
    if handler is None:
        return {"ok": False, "error": "unknown command: %s" % cmd}
    payload = handler(request.get("args") or {}) or {}
    _tag_redraw()
    response = {"ok": True}
    response.update(payload)
    response["state"] = _collect_state()
    return response


# ---------------------------------------------------------------------------
# Main-thread pump
# ---------------------------------------------------------------------------

def _pump():
    while True:
        try:
            request, holder, done = _work.get_nowait()
        except queue.Empty:
            break
        try:
            holder["response"] = _handle(request)
        except Exception as exc:  # noqa: BLE001 - report anything back to the console
            holder["response"] = {
                "ok": False,
                "error": "%s: %s" % (type(exc).__name__, exc),
                "trace": traceback.format_exc(),
            }
        finally:
            done.set()
    return 0.02


def _dispatch(request, timeout=5.0):
    """Called from a socket thread; blocks until the main thread is done."""
    holder = {}
    done = threading.Event()
    _work.put((request, holder, done))
    if not done.wait(timeout):
        return {"ok": False, "error": "timed out waiting for Blender's main thread"}
    return holder.get("response", {"ok": False, "error": "no response"})


# ---------------------------------------------------------------------------
# Socket server
# ---------------------------------------------------------------------------

class _BridgeServer:
    def __init__(self, port):
        self.port = port
        self._socket = None
        self._thread = None
        self._stop = threading.Event()

    def start(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind((HOST, self.port))
        self._socket.listen(4)
        self._socket.settimeout(0.5)
        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()
        print("[MX Bridge] listening on %s:%d" % (HOST, self.port))

    def stop(self):
        self._stop.set()
        if self._socket is not None:
            try:
                self._socket.close()
            except OSError:
                pass
            self._socket = None
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        print("[MX Bridge] stopped")

    def _accept_loop(self):
        while not self._stop.is_set():
            try:
                conn, _ = self._socket.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(target=self._serve, args=(conn,), daemon=True).start()

    def _serve(self, conn):
        conn.settimeout(None)
        buffer = b""
        with conn:
            while not self._stop.is_set():
                try:
                    chunk = conn.recv(4096)
                except OSError:
                    break
                if not chunk:
                    break
                buffer += chunk
                while True:
                    kind, line, buffer = _consume_line(buffer)
                    if kind == "wait":
                        break
                    if kind == "overflow":
                        try:
                            conn.sendall(b'{"ok": false, "error": "request too large"}\n')
                        except OSError:
                            return
                        return
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        request = json.loads(line.decode("utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                        response = {"ok": False, "error": "bad request: %s" % exc}
                    else:
                        if not isinstance(request, dict):
                            response = {"ok": False, "error": "bad request"}
                        else:
                            response = _dispatch(request)
                            response["id"] = request.get("id")
                    try:
                        conn.sendall((json.dumps(response) + "\n").encode("utf-8"))
                    except OSError:
                        return


# ---------------------------------------------------------------------------
# Preferences
# ---------------------------------------------------------------------------

class MXBridgePreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    port: bpy.props.IntProperty(
        name="Port",
        description="Loopback port the Logi Options+ plugin connects to",
        default=DEFAULT_PORT,
        min=1024,
        max=65535,
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "port")
        running = _server is not None
        layout.label(
            text="Listening on %s:%d" % (HOST, self.port) if running else "Not running",
            icon='CHECKMARK' if running else 'ERROR',
        )
        layout.operator("mx_bridge.restart", icon='FILE_REFRESH')


class MXBridgeRestart(bpy.types.Operator):
    bl_idname = "mx_bridge.restart"
    bl_label = "Restart Bridge"
    bl_description = "Stop and start the bridge server, picking up a changed port"

    def execute(self, context):
        _stop_server()
        _start_server()
        self.report({'INFO'}, "MX Console Bridge restarted")
        return {'FINISHED'}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

_classes = (MXBridgePreferences, MXBridgeRestart)


def _port():
    prefs = bpy.context.preferences.addons.get(__package__)
    return prefs.preferences.port if prefs else DEFAULT_PORT


def _start_server():
    global _server
    if _server is not None:
        return
    try:
        _server = _BridgeServer(_port())
        _server.start()
    except OSError as exc:
        _server = None
        print("[MX Bridge] could not listen: %s" % exc)
    if not bpy.app.timers.is_registered(_pump):
        bpy.app.timers.register(_pump, persistent=True)


def _stop_server():
    global _server
    if bpy.app.timers.is_registered(_pump):
        bpy.app.timers.unregister(_pump)
    if _server is not None:
        _server.stop()
        _server = None


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    _start_server()


def unregister():
    _stop_server()
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
