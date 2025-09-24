# Chihiros Device Manager

Maintained by **Caleb Venner**. This project builds on the open-source work published as [Chihiros LED Control](https://github.com/TheMicDiet/chihiros-led-control) by Michael Dietrich. The original project is licensed under MIT; all redistributions of this codebase continue to honour that license and retain the upstream attribution.

Chihiros Device Manager currently contains the historically shipped python **CLI** tooling alongside a new FastAPI-based BLE service for managing Chihiros Bluetooth devices. The near-term roadmap focuses on a standalone service and accompanying Docker packaging.

## Supported Devices
- [Chihiros LED A2](https://www.chihirosaquaticstudio.com/products/chihiros-a-ii-built-in-bluetooth)
- [Chihiros WRGB II](https://www.chihirosaquaticstudio.com/products/chihiros-wrgb-ii-led-built-in-bluetooth) (Regular, Pro, Slim)
- Chihiros Tiny Terrarium Egg
- Chihiros C II (RGB, White)
- Chihiros Universal WRGB
- Chihiros Z Light TINY
- other LED models might work as well but are not tested


## Requirements
- a device with bluetooth LE support for sending the commands to the LED
- [Python 3](https://www.python.org/downloads/) with pip

## Using the CLI
```bash
# setup the environment
python -m venv venv
source venv/bin/activate
pip install -e .

# show help
chihirosctl --help

# discover devices and their address
chihirosctl list-devices

# turn on the device
chihirosctl turn-on <device-address>

# turn off the device
chihirosctl turn-off <device-address>

# manually set the brightness to 100
chihirosctl set-brightness <device-address> 100

# create an automatic timed setting that turns on the light from 8:00 to 18:00
chihirosctl add-setting <device-address> 8:00 18:00

# create a setting for specific weekdays with maximum brightness of 75 and ramp up time of 30 minutes
chihirosctl add-setting <device-address> 9:00 18:00 --weekdays monday --weekdays tuesday --ramp-up-in-minutes 30 --max-brightness 75

# on RGB models, use the RGB versions of the above commands

# manually set the brightness to 60 red, 80 green, 100 blue on RGB models
chihirosctl set-rgb-brightness <device-address> 60 80 100

# create an automatic timed setting that turns on the light from 8:00 to 18:00
chihirosctl add-rgb-setting <device-address> 8:00 18:00

# create a setting for specific weekdays with maximum brightness of 35, 55, 75 and ramp up time of 30 minutes
chihirosctl add-rgb-setting <device-address> 9:00 18:00 --weekdays monday --weekdays tuesday --ramp-up-in-minutes 30 --max-brightness 35 55 75

# enable auto mode to activate the created timed settings
chihirosctl enable-auto-mode <device-address>

# delete a created setting
chihirosctl delete-setting <device-address> 8:00 18:00

# reset all created settings
chihirosctl reset-settings <device-address>

```

## Running the BLE web service

Install the package and launch the bundled FastAPI/Uvicorn entrypoint:

```bash
python -m venv venv
source venv/bin/activate
pip install -e .

chihiros-service
```

Environment variables `CHIHIROS_SERVICE_HOST` and `CHIHIROS_SERVICE_PORT`
override the default listen address (`0.0.0.0:8000`). Once running, visit
`http://localhost:8000/` for the new TypeScript dashboard (if built) or
`http://localhost:8000/ui` to keep using the legacy HTMX interface. All
capabilities remain exposed under the `/api/*` endpoints.

## Frontend development (TypeScript SPA)

The project now ships with an experimental SPA scaffold under the
`frontend/` directory. It consumes the same REST endpoints exposed by the
FastAPI service and will ultimately replace the HTMX templates.

Install dependencies and launch the Vite dev server (proxying API requests to
the Python backend running on port 8000):

```bash
cd frontend
npm install
npm run dev
```

Create a production build before packaging or running inside Docker:

```bash
npm run build
```

By default the FastAPI app serves the compiled bundle from
`frontend/dist`. If the assets live elsewhere, point the service at the
correct directory via the `CHIHIROS_FRONTEND_DIST` environment variable.

## Docker usage

Build and run the service inside a container:

```bash
docker build -t chihiros-service .

docker run \
  --rm \
  --name chihiros-service \
  --net=host \
  --cap-add=NET_ADMIN \
  --cap-add=SYS_ADMIN \
  --device /dev/bus/usb \
  chihiros-service
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
