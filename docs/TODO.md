# Project TODO

## High Priority; do now

### Doser Devices

- Implement manual and one-time dosing commands.
- Add support for advanced schedule types (24 hourly, custom?, timer).
- Implement dosing pump calibration and priming functionality. Pumps must have a mL per second variable that can be written. Calibration logic and calculation performed server side.

### Light Devices

- Lock Doser and Light device cards to the same size, cap automode display to 3 schedules. If more than 3 are programmed --> have a small view-all button --> triggers a pop-up window.
- Allow disabling of light auto modes (deletes from device, saved in config data).
- Add validation to prevent overlapping auto mode schedules.
    (13:00 --> 21:00 && 21:00 --> 22:00 is supported though).
- Investigate and implement "Custom Mode" - most likely sent as a series of auto mode settings (need to test true device behaviour)
- 'Reset Auto Mode' button should be red and smaller, also ensure there is a confirmation.
- Fix "Turn On" / "Turn Off" functionality in device settings.

---- **Need to confirm through testing!!!** ----
*- When a setting/command is saved/set it should not automatically close the device modal/card/window; disruptive UX.*
*- Found devices (scan for devices) window is ugly, need to reformat and keep minimal/sleek.*

## Medium Priority; do soon

### **Light** devices

- Support 140% brightness for capable devices based on wattage calculations (WRGB II Pro; Vivid 2?).
- Define the Home Assistant entity model for lights.
- Implement single-payload manual brightness setting.
