# AquaBle

Current project state: in very active development, at a very early stage. Expect further functionality and refinement soon.

Maintained by **Caleb Venner**. This project builds on the open-source work published as [Chihiros LED Control](https://github.com/TheMicDiet/chihiros-led-control) by Michael Dietrich. The original project is licensed under MIT; all redistributions of this codebase continue to honour that license and retain the upstream attribution.

## Legal Disclaimer

**This project is not affiliated with, endorsed by, or approved by Chihiros Aquatic Studio or Shanghai Ogino Biotechnology Co.,Ltd.** This is an independent, open-source software project developed through reverse engineering and community contributions.

- We do not reproduce, distribute, or claim ownership of any proprietary Chihiros software code
- Device compatibility is based on publicly available Bluetooth Low Energy protocol analysis
- Use of this software with Chihiros devices is at your own risk
- "Chihiros" is a trademark of Chihiros Aquatic Studio (Shanghai Ogino Biotechnology Co.,Ltd) and is used here solely for device identification purposes
- This software is provided "as-is" without warranty of any kind

## Supported Devices

- Chihiros 4 Head Dosing Pump
- Chihiros LED A2
- Chihiros WRGB II
- Chihiros Tiny Terrarium Egg
- Chihiros C II (RGB, White)
- Chihiros Universal WRGB
- Chihiros Z Light TINY
- Chihiros WRGB II Pro
- other LED models might work as well but are not tested

## Future Deployment Options

This project will (shortly) support multiple deployment methods to fit different use cases:

### Home Assistant Add-on (Recommended)

Perfect integration with Home Assistant for smart home automation.

- **Easy installation** through HA add-on store
- **Bluetooth access** automatically configured
- **Data persistence** managed by HA supervisor
- **Web interface** accessible through HA dashboard

**[See Home Assistant setup guide](hassio/README.md)**

### Docker Container

Ideal for self-hosting, Unraid, or standalone deployment.

- **Multi-architecture** support (amd64, arm64, armv7)
- **Docker Compose** for easy setup
- **Health monitoring** and automatic restarts
- **Volume persistence** for device configurations

**[See Docker setup guide](docker/README.md)**

### Python Service

Direct installation for development or advanced users.

- **Native performance** on Raspberry Pi or Linux
- **Development environment** for contributing
- **Full control** over dependencies and configuration
- **System service** integration available

**[See local installation guide](#local-installation)**

## Requirements

- Device with Bluetooth LE support
- [Python 3.10+](https://www.python.org/downloads/) (for local installation)
- Compatible Chihiros devices within Bluetooth range

## Quick Start

### Home Assistant Add-on

```yaml
# Add-on configuration
log_level: INFO
auto_discover: false
auto_reconnect: true
```

### Docker

```bash
docker-compose -f docker/docker-compose.yml up -d
```

### Local Installation

Install the package and launch the bundled FastAPI/Uvicorn entrypoint:

```bash
python -m venv venv
source venv/bin/activate
pip install -e .

aqua-ble-service
```

Environment variables `AQUA_BLE_SERVICE_HOST` and `AQUA_BLE_SERVICE_PORT`
override the default listen address (`0.0.0.0:8000`). Once running, visit
`http://localhost:8000/` for the TypeScript dashboard. If the SPA has not yet
been built (or a Vite dev server is not running), the root route will return a
503 with instructions on how to start the frontend build. All capabilities
remain exposed under the `/api/*` endpoints.

### First run and device discovery

On a fresh start (no cached devices), the dashboard shows a simple onboarding panel with a "Scan for devices" button. Use it to discover nearby supported devices and click "Connect" to add them to the service cache.

Equivalent REST endpoints are available if you prefer scripts:

- `GET /api/scan` → returns a list of nearby supported devices: address, name, product, device_type
- `POST /api/devices/{address}/connect` → connects to the device and captures an initial status

Optional automation: set `AQUA_BLE_AUTO_DISCOVER=1` to perform a one-off scan at startup (only when there are no cached devices) and attempt to connect to supported devices automatically.

```bash
# Disable auto-discover when launching both servers
make dev AQUA_BLE_AUTO_DISCOVER=0

# Run just the backend with auto-discover disabled/enabled explicitly
make dev-back AQUA_BLE_AUTO_DISCOVER=0
make dev-back AQUA_BLE_AUTO_DISCOVER=1
```

### Service runtime tuning

The service performs a brief wait after issuing a BLE status request to
allow notification frames to arrive before reading the device's
`last_status`. This delay defaults to `1.5` seconds but can be tuned via
the environment variable:

```bash
export AQUA_BLE_STATUS_WAIT=0.8  # seconds
```

Lowering the value can make successive manual refreshes faster but risks
capturing an incomplete status frame on slower adapters or noisy RF
environments. Increasing it slightly may help if you observe intermittent
"No status received" errors when polling devices.

## Environment Variables

Centralized reference for runtime configuration knobs exposed by the service / SPA integration.

| Variable | Default | Type | Purpose | Example |
|----------|---------|------|---------|---------|
| `AQUA_BLE_SERVICE_HOST` | `0.0.0.0` | str | Listen interface for the FastAPI/Uvicorn server. | `127.0.0.1` |
| `AQUA_BLE_SERVICE_PORT` | `8000` | int | Listen port for the FastAPI/Uvicorn server. | `9000` |
| `AQUA_BLE_AUTO_RECONNECT` | `1` | int/bool | Attempt reconnect to previously cached devices on startup (`1` truthy, `0` disabled). | `0` |
| `AQUA_BLE_AUTO_DISCOVER` | `0` | int/bool | When no cached devices exist, perform a one-off scan at startup and try to connect to supported devices automatically. | `1` |
| `AQUA_BLE_STATUS_WAIT` | `1.5` | float (s) | Delay after requesting a status before reading cached frame (tune for adapter speed / RF conditions). | `0.8` |
| `AQUA_BLE_FRONTEND_DEV` | (unset) | str/URL | If set, root path proxies to a running Vite dev server instead of serving built assets. Set to `0` to force-disable proxy even if assets missing. | `http://localhost:5173` |
| `AQUA_BLE_FRONTEND_DIST` | `frontend/dist` | path | Absolute/relative path to built SPA assets (index.html + assets/). | `/opt/app/frontend-build` |
| `AQUA_BLE_LOG_LEVEL` | `INFO` | str | Logging verbosity for service logger (standard Python levels). | `DEBUG` |
| `AQUA_BLE_CONFIG_DIR` | `~/.aqua-ble` | path | Configuration directory for device state and profiles. | `~/.config/aqua-ble` |

Notes:

- Boolean style variables accept `0/1`, `true/false`, `yes/no`, or `on/off` (case-insensitive). Invalid or empty values fall back to the documented default.
- Auto-discover runs only when the cache is empty (first run) to avoid interrupting existing connections.
- `AQUA_BLE_STATUS_WAIT` invalid (non-float) values fall back to the default at import time.
- When both a dev server proxy and a local dist are unavailable the root route returns HTTP 503 with guidance.
- Changes to these variables require a service restart to take effect (they are read at module import or startup).
- Configuration directory migration: If `~/.chihiros/` exists and `~/.aqua-ble/` doesn't, configs are automatically migrated to the new location on first startup.

## Docker usage

Build and run the service inside a container:

```bash
docker build -t aquable .

docker run \
  --rm \
  --name aquable \
  --net=host \
  --cap-add=NET_ADMIN \
  --cap-add=SYS_ADMIN \
  --device /dev/bus/usb \
  aquable
```

Containerised BLE access often requires forwarding the host adapter or
running with elevated capabilities; adjust the `docker run` flags to suit
your environment.

## Protocol

The vendor app uses Bluetooth LE to communicate with the LED. The LED advertises a UART service with the UUID `6E400001-B5A3-F393-E0A9-E50E24DCCA9E`. This service contains a RX characteristic with the UUID `6E400002-B5A3-F393-E0A9-E50E24DCCA9E`. This characteristic can be used to send commands to the LED. The LED will respond to commands by sending a notification to the corresponding TX service with the UUID `6E400003-B5A3-F393-E0A9-E50E24DCCA9E`.

The commands are sent as a byte array with the following structure:

| Command ID | 1 | Command Length | Message ID High | Message ID Low | Mode | Parameters | Checksum |
| --- | --- | --- | --- | --- | --- | --- | --- |

The checksum is calculated by XORing all bytes of the command together. The checksum is then added to the command as the last byte.

The message id is a 16 bit number that is incremented with each command. It is split into two bytes. The first byte is the high byte and the second byte is the low byte.

The command length is the number of parameters + 5.

### Manual Mode

The LED can be set to a specific brightness by sending the following command with the following options:

- Command ID: **90**
- Mode: **7**
- Parameters: [ **Color** (0-2), **Brightness** (0 - 100)]

On non-RGB models, the color parameter should be set to 0 to indicate white. On RGB models, each color's brightness is sent as a separate command. Red is 0, green is 1, blue is 2.

### Auto Mode

To switch to auto mode, the following command can be used:

- Command ID: **90**
- Mode: **5**
- Parameters: [ **18**, **255**, **255** ]

With auto mode enabled, the LED can be set to automatically turn on and off at a specific time. The following command can be used to create a new setting:

- Command ID: **165**
- Mode: **25**
- Parameters: [ **sunrise hour**, **sunrise minutes**, **sunset hour**, **sunset minutes**, **ramp up minutes**, **weekdays**, **red brightness**, **green brightness**, **blue brightness**, 5x **255** ]

The weekdays are encoded as a sequence of 7 bits with the following structure: `Monday Thuesday Wednesday Thursday Friday Saturday Sunday`. A bit is set to 1 if the LED should be on on that day. It is only possible to set one setting per day i.e. no conflicting settings. There is also a maximum of 7 settings.

On non-RGB models, the desired brightness should be set as the red brightness while the other two colors should be set to **255**.

To deactivate a setting, the same command can be used but the brightness has to be set to **255**.

#### Set Time

The current time is required for auto mode and can be set by sending the following command:

- Command ID: **90**
- Mode: **9**
- Parameters: [ **year - 2000**, **month**, **weekday**, **hour**, **minute**, **second** ]

- Weekday is 1 - 7 for Monday - Sunday

#### Reset Auto Mode Settings

The auto mode and its settings can be reset by sending the following command:

- Command ID: **90**
- Mode: **5**
- Parameters: [ **5**, **255**, **255** ]
