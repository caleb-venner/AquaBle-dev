# Docker Deployment Guide

## Quick Start

### Using Docker Compose (Recommended)

1. **Clone the repository:**
```bash
git clone https://github.com/caleb-venner/aquable.git
cd aquable
```

2. **Create data directory:**
```bash
mkdir -p docker/data
```

3. **Start the service:**
```bash
docker-compose -f docker/docker-compose.yml up -d
```

4. **Access the web interface:**
   - Open http://localhost:8000

### Using Docker Run

```bash
# Create data volume
docker volume create aquable-data

# Run container
docker run -d \
  --name aquable \
  --restart unless-stopped \
  --privileged \
  --network host \
  -v aquable-data:/data \
  -v /var/run/dbus:/var/run/dbus:ro \
  -e AQUA_BLE_LOG_LEVEL=INFO \
  -e AQUA_BLE_AUTO_RECONNECT=true \
  ghcr.io/caleb-venner/aquable:latest
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AQUA_BLE_LOG_LEVEL` | `INFO` | Logging level |
| `AQUA_BLE_AUTO_DISCOVER` | `false` | Auto-discover devices on startup |
| `AQUA_BLE_AUTO_RECONNECT` | `true` | Auto-reconnect to cached devices |
| `AQUA_BLE_SERVICE_HOST` | `0.0.0.0` | Service bind address |
| `AQUA_BLE_SERVICE_PORT` | `8000` | Service port |

### Bluetooth Access

The container requires Bluetooth access:

**Option 1: Privileged mode (easiest)**
```yaml
privileged: true
network_mode: host
```

**Option 2: Specific permissions (more secure)**
```yaml
cap_add:
  - NET_ADMIN
  - SYS_ADMIN
devices:
  - /dev/bus/usb:/dev/bus/usb
volumes:
  - /var/run/dbus:/var/run/dbus:ro
```

## Data Persistence

Device configurations and status are stored in `/data` within the container.

**Docker Compose:** Mapped to `./docker/data` on host
**Docker Run:** Use a named volume or bind mount

## Unraid Setup

1. **Community Applications:** Search for "AquaBle"
2. **Manual Template:**
   - Repository: `ghcr.io/caleb-venner/aquable:latest`
   - Network Type: `Host`
   - Privileged: `Yes`
   - Path: `/data` → `/mnt/user/appdata/aquable/`

## Troubleshooting

### Bluetooth Issues
```bash
# Check if container can see Bluetooth
docker exec -it aquable bluetoothctl list

# Check logs
docker logs aquable
```

### Permission Issues
```bash
# Ensure DBus access
ls -la /var/run/dbus
# Should be accessible to container user
```

### Network Access
- Use `--network host` for best Bluetooth compatibility
- Port 8000 must be available on host
