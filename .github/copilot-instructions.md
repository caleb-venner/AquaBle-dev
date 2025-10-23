# AquaBle - AI Coding Guidelines

IMPORTANT: This file contains instructions for automated coding assistants and contributors. Please read before making edits.

- Do NOT generate or add user-facing documentation files (guides, HOWTOs, tutorials) unless explicitly requested by the project owner. The project maintainers prefer documentation to be created intentionally and reviewed before inclusion.

## Architecture Overview

**FastAPI Backend + Vite TypeScript Frontend**: This project manages Chihiros aquarium devices (lights/dosers) over BLE. Backend uses `bleak` library for Bluetooth communication with a modular device class hierarchy. Frontend is a Vite-built SPA using Zustand for state management with command queue and optimistic updates.

**Key Components**:
- `BLEService` (`ble_service.py`): Main orchestration class managing device connections, status caching, and storage persistence to `~/.aquable/devices/`
- `BaseDeviceStorage` (`base_device_storage.py`): Abstract base class providing unified file I/O for device configurations, metadata, and status in single JSON files per device
- `DoserStorage`/`LightStorage` (`doser_storage.py`, `light_storage.py`): Type-safe facades extending BaseDeviceStorage for device-specific operations
- `GlobalSettings` (`global_settings.py`): Manages global settings like display timezone in `~/.aquable/global_settings.json`
- Device Classes (`device/`): `BaseDevice` with specific implementations (Doser, LightDevice, etc.) handling BLE connection lifecycle
- Command System (`commands/encoder.py`): Encodes BLE commands with message ID management (skipping 0x5A/90), checksums, and structured byte arrays
- REST API (`api/routes_*.py`): FastAPI endpoints for device control and status with consistent error responses
- Frontend Store (`frontend/src/stores/deviceStore.ts`): Zustand store managing device state, command queue with retry logic, and UI state

**Data Flow**: BLE Device → `bleak` → `BaseDevice` → `BLEService` → REST API → Frontend Store → UI

**BLE Protocol**: Reverse-engineered Chihiros UART service (`6E400001-B5A3-F393-E0A9-E50E24DCCA9E`) with RX/TX characteristics. Commands sent as notifications, responses received via notifications. Command structure: `[Command ID, Length, Message ID High/Low, Mode, Parameters..., Checksum]` with XOR checksum.

## Developer Workflows

**Local Development**:
- `make dev`: Run both frontend (Vite on :5173) and backend (uvicorn on :8000) servers concurrently
- `make dev-front`: Frontend only with hot reload
- `make dev-back`: Backend only with auto-reload and `PYTHONPATH=src`
- Environment variables prefixed `AQUA_BLE_*` control runtime behavior (auto-reconnect, auto-discover, status wait timing)

**Frontend Development**:
- `cd frontend && npm install && npm run dev`: Start Vite dev server with HMR
- `npm run build`: Create production build in `frontend/dist`
- Backend proxies to Vite dev server when `AQUA_BLE_FRONTEND_DEV` is set, otherwise serves built assets

**Quality Assurance**:
- `make test`: Run pytest suite with coverage
- `make lint`: Execute pre-commit hooks (black, isort, flake8, doc8)
- `pre-commit run --all-files`: Full quality check before commits

**Deployment**:
- **Home Assistant Add-on (Ingress Only)**: The project is deployed exclusively as a Home Assistant add-on using Ingress. Install from Home Assistant Community Add-ons repository for automatic Bluetooth access, data persistence, web interface, and timezone management via Home Assistant integration. No other deployment methods are supported.

## Project Conventions

**Device Command Encoding**:
- Commands use structured byte arrays: `[Command ID, Length, Message ID High/Low, Mode, Parameters..., Checksum]`
- Message IDs increment per session, skipping 0x5A (90) in both bytes via `commands.next_message_id()`
- Checksum is XOR of all command bytes starting from second byte
- Example manual brightness: `commands.encode_manual_brightness(msg_id, channel, brightness)` → `[0x5A, length, msg_id_high, msg_id_low, 0x07, channel, brightness, checksum]`

**Device Class Hierarchy**:
```python
class BaseDevice(ABC):
    device_kind: ClassVar[str] = "device"
    # BLE connection management, message ID tracking, operation locking
    # Subclasses implement device-specific commands

class Doser(BaseDevice):
    device_kind = "doser"
    # Dosing pump control with lifetime tracking

class LightDevice(BaseDevice):
    device_kind = "light"
    # LED lighting control with color channel management
```

**Status Caching Pattern**:
- `CachedStatus` dataclass stores device state with `raw_payload` (hex string) and `parsed` (dict)
- Status updates trigger cache refresh with configurable `AQUA_BLE_STATUS_WAIT` (default 1.5s)
- Device status persists to unified device files: `~/.aquable/devices/{address}.json` containing metadata, last_status, and device_data
- Each device file is self-contained with all device information in one place

**Error Handling**:
- BLE operations use `bleak_retry_connector` with exponential backoff
- Device-specific exceptions: `DeviceNotFound`, `CharacteristicMissingError`, `BleakConnectionError`
- API returns structured error responses with device context and timestamps

**Configuration Management**:
- Environment variables migrated from `CHIHIROS_*` to `AQUA_BLE_*` prefix with fallback support
- Unified device files in `~/.aquable/devices/` directory containing metadata, status, and configurations
- Global settings (timezone, etc.) stored in `~/.aquable/global_settings.json`
- Automatic migration from legacy `state.json` format on first startup
- Runtime config via `AQUA_BLE_CONFIG_DIR` (defaults to `~/.aqua-ble`)

**Frontend State Management**:
- Zustand store with `subscribeWithSelector` for efficient re-renders
- Command queue with optimistic updates, retry logic, and error recovery
- Device state Map with loading states, error handling, and command history

**UI and Documentation Guidelines**:
- No icons in documentation or coded UI elements - use plain text descriptions instead
- Keep interfaces clean and text-based for accessibility and simplicity

## Integration Points

**BLE Protocol Details**:
- UART service: `6E400001-B5A3-F393-E0A9-E50E24DCCA9E`
- RX characteristic: `6E400002-B5A3-F393-E0A9-E50E24DCCA9E` (send commands)
- TX characteristic: `6E400003-B5A3-F393-E0A9-E50E24DCCA9E` (receive notifications)
- Commands sent as BLE notifications, responses received via notifications

**Home Assistant (Ingress)**: Add-on provides automatic Bluetooth access and data persistence through Home Assistant Ingress. Exposes devices as entities with MQTT integration potential. All frontend communication goes through Home Assistant's Ingress proxy system.

**Frontend Communication**: REST API endpoints consumed by TypeScript frontend. Command queue managed client-side with retry logic and optimistic updates. Backend proxies frontend dev server during development.

## Common Patterns

**Device Connection**:
```python
async with device_session(address) as device:
    # Device automatically disconnected on context exit
    await device.send_command(command_bytes)
```

**Command Encoding**:
```python
from .commands import encoder as commands
msg_id = commands.next_message_id(current_id)
payload = commands.encode_manual_brightness(msg_id, channel, brightness)
```

**Status Updates**:
```python
# Request status, wait for notification, cache result
await device.request_status()
await asyncio.sleep(STATUS_CAPTURE_WAIT_SECONDS)
cached_status = device.last_status
```

**API Response Formatting**:
```python
# Use serializers.cached_status_to_dict() for consistent API responses
return cached_status_to_dict(service, cached_status)
```

**Frontend Command Queue**:
```typescript
// Queue command with optimistic update and retry logic
const commandId = await actions.queueCommand(address, request);
await actions.processCommandQueue(); // Processes queue sequentially
```

## Key Files to Reference

- `src/aquable/ble_service.py`: Main service orchestration and device management
- `src/aquable/base_device_storage.py`: Abstract base class for device storage with unified file I/O operations
- `src/aquable/doser_storage.py`: Doser-specific storage facade and models
- `src/aquable/light_storage.py`: Light-specific storage facade and models
- `src/aquable/global_settings.py`: Global settings management (timezone, etc.)
- `src/aquable/storage_migration.py`: Automatic migration from legacy state.json format
- `src/aquable/device/base_device.py`: BLE connection lifecycle and messaging
- `src/aquable/commands/encoder.py`: Command encoding logic and message ID management
- `frontend/src/stores/deviceStore.ts`: Frontend state management and command queue
- `pyproject.toml`: Dependencies (Python 3.10+, bleak, fastapi) and build configuration
- `Makefile`: Development workflow shortcuts (`make dev`, `make test`, `make lint`)
- `~/.aquable/`: Configuration directory (global_settings.json, devices/, auto-created)

## Guidelines for AI Assistant

**Do NOT create summary documentation or improvement reports** unless explicitly requested by the user. Focus only on:
- Fixing bugs or issues raised
- Implementing features requested
- Code quality improvements when asked
- Explanations of what was changed (inline, not as documents)

If changes are significant and deserve documentation, ask the user first before creating any files.
