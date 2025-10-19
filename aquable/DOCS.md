# AquaBle Home Assistant Add-on

AquaBle allows you to control Chihiros aquarium lights and dosing pumps over Bluetooth Low Energy directly from Home Assistant.

## Features

- Control LED lighting schedules and manual brightness
- Manage dosing pump operations and lifetime tracking
- Automatic device discovery and connection management
- Web interface for configuration and monitoring
- REST API for integration with other systems

## Installation

1. In Home Assistant, go to **Settings > Add-ons > Add-on Store**
2. Click the menu (⋮) in the top right corner and select **Repositories**
3. Add the repository URL: `https://github.com/caleb-venner/aquable`
4. Find and install the "AquaBle" add-on
5. Configure the options (see Configuration section)
6. Start the add-on

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

The data is stored in the add-on's persistent storage directory, which is mapped to `/data` inside the container. This storage persists across add-on restarts, updates, and Home Assistant updates.

## API

The add-on provides a REST API for device control and monitoring.

### Endpoints

- `GET /api/health` - Health check
- `GET /api/status` - Get all device statuses
- `GET /api/devices` - List discovered devices
- `GET /api/devices/{address}` - Get specific device status
- `POST /api/devices/{address}/commands` - Send command to device
- `GET /api/configurations/lights` - Get light configurations
- `GET /api/configurations/lights/metadata` - Get light configuration metadata
- `GET /api/configurations/dosers` - Get doser configurations
- `GET /api/configurations/dosers/metadata` - Get doser configuration metadata
- `PUT /api/configurations/lights/{id}` - Update light configuration
- `PUT /api/configurations/dosers/{id}` - Update doser configuration

### Web Interface

Access the web interface at `http://your_home_assistant_ip:8000` to configure devices and view status. Replace `your_home_assistant_ip` with your Home Assistant's IP address.

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
