# AquaBle

**Home Assistant integration for Chihiros aquarium devices (LED lights and dosing pumps) via Bluetooth Low Energy.**

AquaBle is built on a robust, **stateless functional architecture**. Rather than trying to force complex, autonomous aquarium ecosystems into standard Home Assistant "on/off" switches, AquaBle treats your equipment as "set and forget" configuration targets. You can monitor their state via read-only sensors and push complex schedules (like dosing routines or sunrise/sunset profiles) directly to the hardware using Home Assistant Automations and Scripts.

## Features

- **Native HA Bluetooth**: Integrates with Home Assistant's native Bluetooth stack, utilises ESPHome proxies and local Bluetooth adapters with auto-reconnects.
- **Autonomous Doser Scheduling**: Push exact volumes, specific times, and active weekdays to the pump hardware so it runs independently.
- **Natural Light Fading**: Push auto-schedules to your LED lights with built-in "ramp up" durations for dawn/dusk simulation.
- **Zero Polling Loops**: Uses Home Assistant's central `DataUpdateCoordinator` for performant, single-connection Bluetooth polling.

## Supported Devices

### Dosing Pumps
- Chihiros Doser series (4-head)

### LED Lights
- **WRGB Series**: WRGB, WRGB II, WRGB II Pro, WRGB II Slim
- **Commander Series**: Commander 1, Commander 4
- **Other Models**: A2, C2, C2 RGB, Z-Light Tiny, Universal WRGB, Tiny Terrarium Egg

## Installation

### Via HACS (Recommended)

1. Open **HACS** in your Home Assistant instance.
2. Go to **Integrations**.
3. Click the **⋮** menu in the top-right corner and select **Custom repositories**.
4. Add this repository URL: `https://github.com/caleb-venner/AquaBle`
5. Select category: **Integration** and click **Add**.
6. Find **AquaBle** in the integration list and click **Download**.
7. Restart Home Assistant.

### Manual Installation

1. Download the latest release.
2. Copy the `custom_components/aquable` folder to your Home Assistant `config/custom_components/` directory.
3. Restart Home Assistant.

## Configuration

1. Go to **Settings** → **Devices & Services**.
2. Home Assistant will automatically discover your Chihiros devices if they are in range of your hub or an ESPHome proxy. 
3. Alternatively, click **+ Add Integration**, search for **AquaBle**, and select your device from the dropdown.

---

## Dashboard Sensors (Visibility)

AquaBle exposes read-only sensors to monitor the autonomous operation of your devices.

### Doser Sensors
- **Pump 1-4 Daily Total (mL)**: Tracks the exact volume of liquid dosed for the current day across each individual pump head.

### Light Sensors
- **Current Mode**: Tracks if the light is in Auto or Manual mode *(Note: Currently in active development)*.

---

## Actions / Services (Control)

To control your devices, use Home Assistant Automations or Scripts to call these custom Actions (Services). 

### Doser Actions
- **`aquable.doser_set_daily_dose_sequence`**: Push a complete daily schedule to a single doser head. Define the exact `volume_ml`, `hour`, `minute`, and specific `weekdays` for it to run.
- **`aquable.doser_manual_dose`**: Override the schedule and trigger a pump head to instantly dose a specific volume.

### Light Actions
- **`aquable.light_set_auto_schedule`**: Add an automatic lighting schedule. Set the `sunrise` and `sunset` times, the target RGBW channel brightness, and the `ramp_up_minutes` (to slowly fade the light on/off).
- **`aquable.light_set_manual_mode`**: Override schedules and instantly set a static brightness for white, red, green, and blue channels.
- **`aquable.light_set_mode`**: Switch the hardware between `auto`, `manual`, and `off` modes.
- **`aquable.light_clear_schedules`**: Wipe all tracked auto-mode schedules from the device's memory.

---

## Support

For issues, questions, or feature requests, please visit:
- [GitHub Issues](https://github.com/caleb-venner/AquaBle/issues)
- [Discussion/Wiki](https://github.com/caleb-venner/AquaBle)

## Legal Notice

This project is not affiliated with, endorsed by, or approved by Chihiros Aquatic Studio or Shanghai Ogino Biotechnology Co., Ltd. This is an independent, open-source software project developed through reverse engineering and community contributions.

## License

MIT License - see [LICENSE](LICENSE) file for details.

*Based on [Chihiros LED Control](https://github.com/TheMicDiet/chihiros-led-control) by Michael Dietrich.*
