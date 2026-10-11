# Technical Specification: hypr-rotate

## 1. Overview
`hypr-rotate` is a lightweight, responsive display orientation manager and auto-rotation daemon designed specifically for Wayland (Hyprland / Omarchy) on 2-in-1 convertible laptops and tablets (such as HP OmniBook Ultra Flip, Lenovo Yoga, Dell XPS 2-in-1, ASUS ROG Flow).

It provides:
1. Dynamic screen orientation control via Hyprland's native Lua interface (`hl.monitor`).
2. An Omarchy top bar status widget (`mateusz.rotate`) with one-touch portrait/landscape toggle and orientation lock.
3. An accelerometer sensor monitoring daemon (via `iio-sensor-proxy` D-Bus or direct IIO sysfs) that automatically rotates the screen in tablet mode.
4. Automatic input alignment (touchscreen & stylus mapping) ensuring stylus coordinates track display orientation seamlessly.

---

## 2. Architecture & Tech Stack

### 2.1 Display Management
* **Compositor:** Hyprland 0.47+ (Wayland).
* **Communication Interface:** `hyprctl eval` executing `hl.monitor({ output = ..., transform = ... })` dynamically without reloading the entire config or disrupting workspaces.
* **Orientation Transforms:**
  * `0`: Normal / Landscape (0°)
  * `1`: Portrait / 90° clockwise
  * `2`: Inverted Landscape / 180°
  * `3`: Inverted Portrait / 270° clockwise

### 2.2 Daemon & Sensor Pipeline
* **Sensor Backends:**
  1. Primary: D-Bus listener on `net.hadess.SensorProxy` (`AccelerometerOrientation` property changes).
  2. Fallback: Polling `/sys/bus/iio/devices/iio:device*/` raw acceleration channels with hysteresis filtering.
* **Debounce & Filtering:**
  * 300ms orientation debounce to prevent accidental rotation during hand repositioning.
  * Integration with tablet mode status (`~/.local/bin/omarchy-tablet-mode status`): auto-rotation can be configured to only trigger when in tablet mode, preventing unwanted rotations when on a desk.
* **Lock State:**
  * State persisted in `/run/user/$UID/hypr-rotate.state` or `~/.cache/hypr-rotate/state.json`.
  * When locked (`locked: true`), automated sensor rotation is paused while manual toggles remain active.

### 2.3 User Interface
* **CLI Utility:** `hypr-rotate [toggle | landscape | portrait | inverted | lock | unlock | status | daemon]`
* **Omarchy Bar Widget (`mateusz.rotate`):**
  * Displays intuitive nerd font icons:
    * `󰣡` Landscape (normal)
    * `󰹑` Portrait (vertical)
    * `󰢚` Inverted Landscape
    * `󱎎` Inverted Portrait
    * `󰌾` / `󰌿` Orientation lock badge / toggle
  * Click: Quick toggle between Landscape (0°) and Portrait (1°).
  * Right-click / Middle-click: Toggle auto-rotation lock on/off.
  * Scroll wheel: Cycle through orientations (0° -> 90° -> 180° -> 270°).

---

## 3. Definition of Done (DoD)
1. **Core Executable (`hypr_rotate.py` / `hypr-rotate`):**
   * Can query active internal display (`eDP-1` / `desc:...`).
   * Can rotate display instantaneously between transforms 0, 1, 2, 3 without errors.
2. **State Management:**
   * Tracks current orientation, lock status, and tablet-only mode.
3. **Omarchy Top Bar Widget:**
   * Widget `mateusz.rotate` added to `~/.config/omarchy/plugins/`.
   * Real-time icon reflecting orientation and lock state.
4. **Hyprland Keybinding:**
   * Shortcut bound in `~/.config/hypr/bindings.lua` (e.g. `SUPER + O`).
5. **Git Repository & Documentation:**
   * Git repo initialized with English `README.md`, `SPEC.md`, `LICENSE` (MIT), and `.gitignore`.
   * Published to GitHub under `MateuszBrankiewicz/hypr-rotate`.

---

## 4. Acceptance Criteria (AC)
* **AC1:** Running `hypr-rotate toggle` cleanly flips the internal screen between landscape (0) and portrait (1/3).
* **AC2:** Touchscreen and stylus accurately follow the rotated viewport without offset or invert bugs.
* **AC3:** Clicking the status bar widget rotates the screen immediately; right-clicking toggles rotation lock.
* **AC4:** The daemon respects the lock state and does not rotate the screen when locked.
* **AC5:** All code, commit history, and documentation are clean, idiomatic, and in English.
