# Device Card Architecture

## General (Both)

Need a small cog/configuration icon in the top right hand side of each device card.
This will contain general device settings:
    - Text Field for Device 'Nickname'; if set this replaces the Device Name used in the webUI
    - Toggle for 'Auto Connect'; if set when the service starts it will try to connect to this device, as it is 'known'.

*Doser Specific* - Text Fields for 'Head Names'; if set this will replace the generic headnames in the web UI; i.e., Head 1 --> Calcium ...

## Device 'Settings' Modal/window

### Light Devices

**Channel Values** Per light device channel values should be obtained from the backend device model data. This will cause the channels to be dynamically loaded depending on each device.

#### Settings

**Manual Mode**: Contains the frame responsible for taking user input and constructing a manual device setting.
Data fields:

- Channel brightness value sliders. (Default to 50% for all channels)
- 'Send Command' button; this triggers sending 'set manual mode' command (if not yet set), then sending the manual setting command(s) to the device.

**Auto Mode**: Contains the frame resonsible for taking user input and constructing an auto device setting.
Data fields:

- 24hr Time field (hours and minutes) - 'Sunrise'
- 24hr Time field (hours and minutes) - 'Sunset'
- Time field (minutes) - 'Ramp Time'
- Channel brightness value sliders. (Default to 50% for all channels).
- 'Send Command' button; this triggers sending 'set auto mode' command (if not yet set), then sending the auto setting command to the device.

### Doser Devices

This section is mostly in place and ready for testing. We just need to check that it is linked into the backend api for command execution.
