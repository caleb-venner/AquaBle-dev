# Project TODO

## High Priority; do now

### Doser Devices

- Implement manual and one-time dosing commands.
- Add support for advanced schedule types (24 hourly, custom?, timer).
- Implement dosing pump calibration and priming functionality.

### Light Devices

- Add validation to prevent overlapping auto mode schedules.
    (13:00 --> 21:00 && 21:00 --> 22:00 is supported though).
- Investigate and implement "Custom Mode" - most likely sent as a series of auto mode settings (need to test true device behaviour)
- 'Reset Auto Mode' button should be red and smaller. Also ensure there is a confirmation.
- Fix "Turn On" / "Turn Off" functionality in device settings.

---- **Need to confirm through testing!!!** ----
*- When a setting/command is saved/set it should not automatically close the device modal/card/window; disruptive UX.*
*- Found devices (scan for devices) window is ugly, need to reformat and keep minimal/sleek.*

## Medium Priority; do soon

### **Light** devices

- Support 140% brightness for capable devices based on wattage calculations.
- Define the Home Assistant entity model for lights.
- Implement single-payload manual brightness setting.

### **Nice to Haves**, optional

- Add favorite settings or 'Scenes' for light devices.
- Track dosed volume against container size and expose to UI and Home Assistant.
- Expand device model names in the backend to include full specifications (e.g., size).
- Implement a first-time setup wizard for new devices?? Need to warn user that device will have all of its settings 'reset'.
- Create virtual devices for testing different hardware configurations?
- Consider implementing versioning for device configurations.
