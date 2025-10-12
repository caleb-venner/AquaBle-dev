# Project TODO

## Urgent

### Auto Mode Schedule Conflicts

- Add validation to prevent overlapping auto mode schedules (protocol limitation: "one setting per day (actually just no overlap)")
- Prevent users from creating conflicting auto settings that could cause undefined device behavior

## High Priority

### Doser Features

- Implement manual and one-time dosing commands.
- Add support for advanced schedule types (interval, countdown, conditional).
- Implement dosing pump calibration and priming functionality.
- Add full schedule management (Create, Read, Update, Delete).

### Light Features

- Investigate and implement "Custom Mode".
- 'Reset Auto Mode' button should be red and smaller. Also ensure there is a confirmation.
- Add auto, manual, and favorite settings to the device overview.
- Prevent overlapping auto mode schedules.
- Display real-time light values from saved configuration.
- Fix "Turn On" / "Turn Off" functionality in device settings.

### General & UI

- Found devices (scan for devices) window is ugly.
- Pressing 'Connect' from Overview dash on device card does not trigger an status information for user, don't know if it acheived anything.
- Overview page needs to dynamically reload when device connected (auto or otherwise)
- Disconnect/Reconnect/Connect button needs to change depending on device state/status
- Implement a first-time setup wizard for new devices.
- Redesign the device overview page for better clarity.
- Ensure device configuration supports partial updates.
- Create virtual devices for testing different hardware configurations.

## Medium Priority

**Light** devices:

- Support 140% brightness for capable devices based on wattage calculations.
- Define the Home Assistant entity model for lights.
- Implement single-payload manual brightness setting.

**General** functions:

- Improve connection status feedback in the UI.
- Remove the "Searching" notification when scanning for devices.
- Consider implementing versioning for device configurations.

**Nice to Haves**, optional:

- Track dosed volume against container size and expose to UI and Home Assistant.
- Expand device model names in the backend to include full specifications (e.g., size).
