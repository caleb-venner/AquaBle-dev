# AquaBle Home Assistant Add-on

AquaBle allows you to control Chihiros aquarium lights and dosing pumps over Bluetooth Low Energy directly from Home Assistant.

## Features

- Control LED lighting schedules and manual brightness
- Manage dosing pump operations and lifetime tracking
- Automatic device discovery and connection management
- Web interface for configuration and monitoring
- REST API for integration with other systems

## Installation

1. Add this repository to your Home Assistant add-on store
2. Install the "AquaBle" add-on
3. Configure the options (see Configuration section)
4. Start the add-on

## Configuration

### Options

| Option | Description | Default | Required |
|--------|-------------|---------|----------|
| `auto_reconnect` | Automatically reconnect to devices on startup | `true` | No |
| `auto_discover` | Automatically discover new devices | `true` | No |
| `status_wait_seconds` | Time to wait for device status updates | `1.5` | No |
| `timezone` | Timezone for schedules ("auto" uses HA timezone) | `"auto"` | No |

### Network

The add-on runs on port 8000 and provides both a web interface and REST API.

## Data Storage

Device configurations, schedules, and status information are stored in `/data` inside the container, which is automatically mapped to Home Assistant's persistent add-on storage.

### Storage Structure

```bash
/data/
├── global_settings.json    # Global settings (timezone, etc.)
└── devices/                # Per-device configuration files
    ├── AA:BB:CC:DD:EE:FF.json
    ├── AA:BB:CC:DD:EE:GG.json
    └── ...
```

### Data Persistence

Your settings will survive:

- Add-on restarts
- Add-on updates
- System reboots
- Home Assistant updates

The data is stored in Home Assistant's `/config` directory under `addons/data/[addon-slug]`.

## API

The add-on provides a REST API for device control and monitoring.

### Endpoints

- `GET /health` - Health check
- `GET /devices` - List discovered devices
- `GET /devices/{address}` - Get device status
- `POST /devices/{address}/command` - Send command to device

### Web Interface

Access the web interface at `http://homeassistant:8000` to configure devices and view status.

## Bluetooth Requirements

This add-on requires Bluetooth access. Ensure your Home Assistant installation has Bluetooth capabilities.

### Hardware Requirements

- Bluetooth 4.0+ adapter
- Compatible Chihiros devices within Bluetooth range

## Troubleshooting

### Device Connection Issues

1. Ensure devices are powered on and in pairing mode
2. Check Bluetooth signal strength
3. Verify device addresses in logs

### Logs

View add-on logs in Home Assistant under Settings > Add-ons > AquaBle > Log.

## Support

For issues and feature requests, please create an issue on the [GitHub repository](https://github.com/caleb-venner/aquable).