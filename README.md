# 🔄 hypr-rotate

A modern, responsive screen rotation controller and auto-rotation daemon for **Hyprland** (Wayland) and **Omarchy**. Engineered specifically for 2-in-1 convertible laptops, flip devices, and tablets (e.g., HP OmniBook Ultra Flip, Lenovo Yoga, Dell XPS 2-in-1, ASUS ROG Flow).

---

## ✨ Features

* **Instant Dynamic Rotation:**
  * Uses Hyprland's native Lua interface (`hl.monitor`) for instant orientation changes without config reload flickering or window dislocation.
  * Supports all 4 orientations:
    * `0`: Landscape (Normal 0°)
    * `1`: Portrait (90° Clockwise)
    * `2`: Inverted Landscape (180°)
    * `3`: Inverted Portrait (270° Clockwise)
* **Touchscreen & Stylus Tracking:**
  * Coordinates for active stylus and multi-touch digitizers automatically track rotated monitor viewports.
* **Orientation Lock:**
  * Prevent unwanted rotations when using your device lying down or on uneven surfaces.
* **Omarchy Top Bar Widget (`mateusz.rotate`):**
  * **Left Click:** Instant 1-tap toggle between Landscape and Portrait.
  * **Right Click:** Toggle Auto-Rotation Lock on/off.
  * **Scroll Wheel:** Seamlessly cycle through all 4 orientations.
  * Dynamic Nerd Font indicators: `󰣡` (Landscape), `󰹑` (Portrait), `󰌾` (Locked).
* **Auto-Rotation Daemon:**
  * Connects to `iio-sensor-proxy` D-Bus interface (`net.hadess.SensorProxy`).
  * Only rotates when tablet mode is active, avoiding rotation quirks when stationary on a desk.

---

## 🚀 Quick Start

### 1. Requirements
* Hyprland 0.45+ (Lua config support)
* Python 3.10+
* `python-gobject` (for optional D-Bus sensor integration)
* `iio-sensor-proxy` (optional, for automatic hardware sensor rotation)

### 2. Manual Commands
```bash
# Toggle between Landscape and Portrait
hypr-rotate toggle

# Specific orientations
hypr-rotate landscape    # 0°
hypr-rotate portrait     # 90°
hypr-rotate inverted     # 180°
hypr-rotate cycle        # 0° -> 90° -> 180° -> 270°

# Lock / Unlock orientation
hypr-rotate toggle-lock
hypr-rotate status --json
```

### 3. Hyprland Keybinding
Add to your `~/.config/hypr/bindings.lua`:
```lua
o.bind("SUPER + O", "Toggle Screen Orientation", "hypr-rotate toggle")
```

### 4. Background Auto-Rotation Daemon
Run in background or enable at Hyprland startup:
```bash
hypr-rotate daemon &
```

---

## 🧩 Architecture

```
Physical Device Turning (Sensor) / User Action (Bar Widget or Super+O)
                             │
                             ▼
                        hypr-rotate
                             │
                             ├──► Checks Lock State & Tablet Mode Status
                             │
                             ▼
       hyprctl eval 'hl.monitor({ output = ..., transform = ... })'
                             │
                             ▼
                Hyprland Wayland Compositor
                             │
             ┌───────────────┴───────────────┐
             ▼                               ▼
   Rotated Display Viewport        Automatic Touch & Stylus Matrix Alignment
```

---

## 📄 License
MIT License. Created by [Mateusz Brankiewicz](https://github.com/MateuszBrankiewicz).
