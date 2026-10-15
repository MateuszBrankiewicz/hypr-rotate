#!/usr/bin/env python3
"""
hypr-rotate: Display orientation manager & auto-rotation controller for Hyprland (Wayland).
Optimized for 2-in-1 laptops & convertibles on Omarchy / Arch Linux.
"""

import sys
import os
import json
import subprocess
import time
import signal
from pathlib import Path

STATE_FILE = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / "hypr-rotate.state"

# Orientation definitions:
# Hyprland transform values:
# 0: normal (landscape)
# 1: 90° clockwise (portrait-right)
# 2: 180° inverted landscape
# 3: 270° clockwise (portrait-left)

ORIENTATIONS = {
    "landscape": 0,
    "portrait": 1,
    "inverted-landscape": 2,
    "inverted-portrait": 3,
}

TRANSFORM_NAMES = {
    0: "landscape",
    1: "portrait",
    2: "inverted-landscape",
    3: "inverted-portrait",
}

TRANSFORM_ICONS = {
    0: "󰣡",  # Landscape
    1: "󰹑",  # Portrait
    2: "󰢚",  # Inverted Landscape
    3: "󱎎",  # Inverted Portrait
}


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"transform": 0, "locked": False, "auto_rotate": False}


def save_state(state: dict):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        sys.stderr.write(f"Warning: could not save state: {e}\n")


def get_hyprland_monitors() -> list:
    try:
        out = subprocess.check_output(["hyprctl", "monitors", "-j"], stderr=subprocess.DEVNULL)
        return json.loads(out)
    except Exception as e:
        sys.stderr.write(f"Error querying monitors: {e}\n")
        return []


def get_internal_monitor() -> dict | None:
    monitors = get_hyprland_monitors()
    if not monitors:
        return None

    # Priority 1: eDP display (standard internal laptop panel)
    for m in monitors:
        name = m.get("name", "")
        if "eDP" in name:
            return m

    # Priority 2: ID 0 or primary display
    for m in monitors:
        if m.get("id") == 0:
            return m

    return monitors[0]


def set_monitor_transform(target_transform: int) -> bool:
    monitor = get_internal_monitor()
    if not monitor:
        sys.stderr.write("No internal monitor found.\n")
        return False

    name = monitor.get("name", "eDP-1")
    desc = monitor.get("description", "")
    width = monitor.get("width", 2880)
    height = monitor.get("height", 1800)
    rr = monitor.get("refreshRate", 120.0)
    x = monitor.get("x", 0)
    y = monitor.get("y", 0)
    scale = monitor.get("scale", 2.0)

    # In Hyprland Lua syntax:
    # hl.monitor({ output = "eDP-1", mode = "2880x1800@120.00", position = "3160x-90", scale = 2, transform = X })
    mode_str = f"{width}x{height}@{rr:.2f}"
    pos_str = f"{x}x{y}"

    # Use output name directly, rotating display, touchscreen, and stylus synchronously
    lua_cmd = (
        f'hl.monitor({{ '
        f'output = "{name}", '
        f'mode = "{mode_str}", '
        f'position = "{pos_str}", '
        f'scale = {scale}, '
        f'transform = {target_transform} '
        f'}}); '
        f'hl.config({{ '
        f'input = {{ '
        f'touchdevice = {{ transform = {target_transform}, output = "{name}" }}, '
        f'tablet = {{ transform = {target_transform}, output = "{name}" }} '
        f'}} '
        f'}})'
    )

    # 1. Prevent hyprmoncfgd daemon from reverting rotated displays
    try:
        if target_transform != 0:
            subprocess.run(["systemctl", "--user", "stop", "hyprmoncfgd.service"], capture_output=True, timeout=2.0)
        elif not is_tablet_mode():
            subprocess.run(["systemctl", "--user", "start", "hyprmoncfgd.service"], capture_output=True, timeout=2.0)
    except Exception:
        pass

    try:
        res = subprocess.run(
            ["hyprctl", "eval", lua_cmd],
            capture_output=True,
            text=True,
            timeout=2.0
        )
        if res.returncode == 0 and "ok" in res.stdout.lower():
            state = load_state()
            state["transform"] = target_transform
            save_state(state)

            # Also update hyprmoncfg-monitors.lua if present to prevent reload regressions
            hyprmon_lua = Path.home() / ".config/hypr/hyprmoncfg-monitors.lua"
            if hyprmon_lua.exists():
                try:
                    content = hyprmon_lua.read_text()
                    import re
                    # Add or update transform in Samsung Display block
                    if "transform = " in content:
                        new_content = re.sub(r'transform = \d', f'transform = {target_transform}', content)
                    else:
                        new_content = content.replace('scale = 2,', f'scale = 2,\n  transform = {target_transform},')
                    hyprmon_lua.write_text(new_content)
                except Exception:
                    pass

            return True
        else:
            sys.stderr.write(f"hyprctl eval failed: {res.stderr or res.stdout}\n")
            return False
    except Exception as e:
        sys.stderr.write(f"Error applying monitor rotation: {e}\n")
        return False


def get_current_transform() -> int:
    monitor = get_internal_monitor()
    if monitor:
        return monitor.get("transform", 0)
    state = load_state()
    return state.get("transform", 0)


def cmd_toggle():
    state = load_state()
    cur = get_current_transform()
    # Toggle between Landscape (0) and Portrait (1)
    target = 1 if cur == 0 else 0
    set_monitor_transform(target)


def cmd_cycle():
    cur = get_current_transform()
    target = (cur + 1) % 4
    set_monitor_transform(target)


def cmd_lock_toggle():
    state = load_state()
    state["locked"] = not state.get("locked", False)
    save_state(state)


def cmd_status(json_output=False):
    state = load_state()
    cur_tf = get_current_transform()
    locked = state.get("locked", False)
    name = TRANSFORM_NAMES.get(cur_tf, "landscape")
    icon = TRANSFORM_ICONS.get(cur_tf, "󰣡")
    lock_badge = "󰌾" if locked else "󰌿"

    if json_output:
        print(json.dumps({
            "transform": cur_tf,
            "name": name,
            "icon": icon,
            "locked": locked,
            "lock_icon": lock_badge,
            "text": f"{icon} {lock_badge}" if locked else icon,
            "tooltip": f"Orientation: {name.title()} ({'Locked' if locked else 'Unlocked'})\nClick: Toggle Portrait/Landscape\nRight-Click: Toggle Lock\nScroll: Cycle Orientations"
        }))
    else:
        print(f"Transform: {cur_tf} ({name}) | Locked: {locked}")


def is_tablet_mode() -> bool:
    try:
        # Check omarchy-tablet-mode if available
        tablet_bin = Path.home() / ".local/bin/omarchy-tablet-mode"
        if tablet_bin.exists():
            res = subprocess.run([str(tablet_bin), "status"], capture_output=True, text=True)
            return "enabled" in res.stdout.lower() or "active" in res.stdout.lower()
    except Exception:
        pass
    return True


def run_daemon():
    """Background daemon listening to iio-sensor-proxy or accelerometer."""
    print("Starting hypr-rotate daemon...")
    state = load_state()
    state["auto_rotate"] = True
    save_state(state)

    # Check for D-Bus iio-sensor-proxy
    try:
        import gi
        gi.require_version("Gio", "2.0")
        from gi.repository import Gio, GLib

        bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        proxy = Gio.DBusProxy.new_sync(
            bus,
            Gio.DBusProxyFlags.NONE,
            None,
            "net.hadess.SensorProxy",
            "/net/hadess/SensorProxy",
            "net.hadess.SensorProxy",
            None
        )

        # Call ClaimAccelerometer
        try:
            proxy.call_sync("ClaimAccelerometer", None, Gio.DBusCallFlags.NONE, -1, None)
            print("Successfully claimed accelerometer via iio-sensor-proxy.")
        except Exception as e:
            print(f"ClaimAccelerometer notice: {e}")

        def on_properties_changed(proxy, changed_props, invalidated_props):
            state = load_state()
            if state.get("locked", False):
                return

            if not is_tablet_mode():
                # Don't auto-rotate when in normal clamshell laptop mode on desk
                return

            props_dict = changed_props.unpack()
            orientation = props_dict.get("AccelerometerOrientation")
            if orientation:
                mapping = {
                    "normal": 0,
                    "right-up": 1,
                    "bottom-up": 2,
                    "left-up": 3,
                }
                target = mapping.get(orientation)
                if target is not None and target != get_current_transform():
                    print(f"Auto-rotating to: {orientation} (transform={target})")
                    set_monitor_transform(target)

        proxy.connect("g-properties-changed", on_properties_changed)
        loop = GLib.MainLoop()
        loop.run()
        return
    except Exception as e:
        print(f"iio-sensor-proxy not available via D-Bus: {e}. Running polling mode.")

    # Polling fallback
    while True:
        time.sleep(1.0)


def main():
    if len(sys.argv) < 2:
        cmd_status()
        return

    arg = sys.argv[1].lower()
    if arg in ("toggle", "t"):
        cmd_toggle()
    elif arg in ("landscape", "0"):
        set_monitor_transform(0)
    elif arg in ("portrait", "1"):
        set_monitor_transform(1)
    elif arg in ("inverted", "180", "2"):
        set_monitor_transform(2)
    elif arg in ("portrait-left", "270", "3"):
        set_monitor_transform(3)
    elif arg in ("cycle", "c"):
        cmd_cycle()
    elif arg in ("lock", "l"):
        state = load_state()
        state["locked"] = True
        save_state(state)
    elif arg in ("unlock", "u"):
        state = load_state()
        state["locked"] = False
        save_state(state)
    elif arg in ("toggle-lock", "tl"):
        cmd_lock_toggle()
    elif arg in ("status", "s"):
        cmd_status(json_output="--json" in sys.argv or "-j" in sys.argv)
    elif arg in ("daemon", "d"):
        run_daemon()
    else:
        print("Usage: hypr-rotate [toggle|landscape|portrait|inverted|cycle|lock|unlock|toggle-lock|status|daemon]")
        sys.exit(1)


if __name__ == "__main__":
    main()
