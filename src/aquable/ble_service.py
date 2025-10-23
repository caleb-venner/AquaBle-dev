"""BLE service module extracted from service.py.

Contains the BLEService orchestration class and supporting CachedStatus dataclass.
This is a mechanical extract so tests and callers can continue to import
from aquable.service while the implementation lives here.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, is_dataclass
from datetime import time as _time
from typing import Any, AsyncIterator, Dict, Iterable, Optional, Sequence, Tuple, Type

from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak_retry_connector import BleakConnectionError, BleakNotFoundError
from fastapi import HTTPException

from . import utils as _utils
from .commands import encoder as commands
from .commands import ops as device_commands
from .constants import BLE_STATUS_CAPTURE_WAIT
from .device import get_device_from_address, get_model_class_from_name
from .device.base_device import BaseDevice
from .errors import DeviceNotFoundError
from .utils import get_config_dir, get_env_bool, get_env_float

# Re-implement lightweight internal API functions (previously in core_api)
SupportedDeviceInfo = Tuple[BLEDevice, Type[BaseDevice]]

# Persistence and runtime configuration
CONFIG_DIR = get_config_dir()
COMMAND_HISTORY_PATH = CONFIG_DIR / "command_history.json"
DEVICE_CONFIG_PATH = CONFIG_DIR / "devices"  # Unified directory for all device files

# Environment variable names
AUTO_RECONNECT_ENV = "AQUA_BLE_AUTO_RECONNECT"
STATUS_CAPTURE_WAIT_ENV = "AQUA_BLE_STATUS_WAIT"
AUTO_DISCOVER_ENV = "AQUA_BLE_AUTO_DISCOVER"
AUTO_SAVE_ENV = "AQUA_BLE_AUTO_SAVE"

# Get status capture wait with fallback
STATUS_CAPTURE_WAIT_SECONDS = get_env_float(STATUS_CAPTURE_WAIT_ENV, BLE_STATUS_CAPTURE_WAIT)

# Module logger
logger = logging.getLogger("aquable.service")
_default_level = (os.getenv("AQUA_BLE_LOG_LEVEL", "INFO") or "INFO").upper()
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=getattr(logging, _default_level, logging.INFO),
        format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
    )
try:
    logger.setLevel(getattr(logging, _default_level, logging.INFO))
except Exception:
    logger.setLevel(logging.INFO)


@asynccontextmanager
async def device_session(address: str) -> AsyncIterator[BaseDevice]:
    """Connect to a device and ensure it is disconnected afterwards."""
    device = await get_device_from_address(address)
    try:
        yield device
    finally:
        await device.disconnect()


@dataclass(slots=True)
class CachedStatus:
    """Serialized snapshot for persistence."""

    address: str
    device_type: str
    raw_payload: str | None
    parsed: Dict[str, Any] | None
    updated_at: float
    model_name: str | None = None
    channels: Dict[str, int] | None = None


def filter_supported_devices(
    devices: Iterable[BLEDevice],
) -> list[SupportedDeviceInfo]:
    """Return BLE devices that map to a known Chihiros model.

    This intentionally ignores devices that do not map to a known model
    (for example, TVs or other unrelated BLE peripherals). Calling
    `get_model_class_from_name` may raise DeviceNotFoundError for unknown
    device names; swallow that and continue so discovery is robust.
    """
    supported: list[SupportedDeviceInfo] = []
    for device in devices:
        name = device.name
        if not name:
            continue
        try:
            model_class = get_model_class_from_name(name)
        except DeviceNotFoundError:
            # Unknown device name — skip it
            continue
        # type: ignore[attr-defined]
        codes = getattr(model_class, "model_codes", [])
        if not codes:
            continue
        supported.append((device, model_class))
    return supported


async def discover_supported_devices(
    timeout: float = 5.0,
) -> list[SupportedDeviceInfo]:
    """Discover BLE devices and return the supported Chihiros models.

    Returns empty list if Bluetooth is unavailable or disabled.
    """
    try:
        discovered = await BleakScanner.discover(timeout=timeout)
        return filter_supported_devices(discovered)
    except Exception as e:
        # Bluetooth controller not found, disabled, or other hardware issues
        error_msg = str(e).lower()
        if "bluetooth device is turned off" in error_msg or "not available" in error_msg:
            logger.warning("Bluetooth is disabled or unavailable: %s", e)
        elif "adapter" in error_msg or "controller" in error_msg or "no such file" in error_msg:
            logger.warning("Bluetooth adapter/controller not found: %s", e)
        else:
            logger.warning("Bluetooth discovery failed: %s", e)
        # Return empty list to allow service to continue running
        return []


class BLEService:
    """Manages BLE devices, status cache, and persistence."""

    def __init__(self) -> None:
        """Initialize the BLEService, device maps and runtime flags."""
        self._lock = asyncio.Lock()
        self._devices: Dict[str, Dict[str, BaseDevice]] = {}  # kind -> address -> device
        self._addresses: Dict[str, str] = {}  # kind -> primary address for _refresh_device_status
        self._commands: Dict[str, list] = {}  # Per-device command history
        self._device_metadata: Dict[str, dict] = {}  # Per-device metadata
        self._auto_reconnect = get_env_bool(AUTO_RECONNECT_ENV, True)
        self._auto_discover_on_start = get_env_bool(AUTO_DISCOVER_ENV, False)
        self._reconnect_task: asyncio.Task | None = None
        self._discover_task: asyncio.Task | None = None
        self._auto_save_config = get_env_bool(AUTO_SAVE_ENV, True)

        # Ensure config directory exists
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        # Initialize storage instances for persistent configurations
        # These are initialized with empty metadata dicts which get populated from disk
        from .storage import DoserStorage, LightStorage

        doser_metadata: Dict[str, dict] = {}
        light_metadata: Dict[str, dict] = {}

        self._doser_storage = DoserStorage(DEVICE_CONFIG_PATH, doser_metadata)
        self._light_storage = LightStorage(DEVICE_CONFIG_PATH, light_metadata)
        logger.info("Configuration storage initialized: %s", DEVICE_CONFIG_PATH)

        # Pre-populate metadata from both storage instances after initialization
        # BaseDeviceStorage.__init__ already loads metadata from disk
        # Now copy it into the service's metadata dict
        for device_id, metadata in doser_metadata.items():
            self._device_metadata[device_id] = metadata
        for device_id, metadata in light_metadata.items():
            self._device_metadata[device_id] = metadata

        # Initialize timezone configuration
        from .utils import get_system_timezone

        self._display_timezone = get_system_timezone()
        logger.info("Display timezone: %s", self._display_timezone)

    def _list_all_devices(self) -> list[Dict[str, Any]]:
        """List all devices from both storage systems.

        Returns a combined list of device information from doser and light storage.
        """
        all_devices = []
        all_devices.extend(self._doser_storage.list_all_devices_with_metadata())
        all_devices.extend(self._light_storage.list_all_devices_with_metadata())
        return all_devices

    def _get_storage_for_type(self, device_type: str):
        """Get the appropriate storage instance for a device type."""
        normalized = device_type.lower()
        if normalized == "doser":
            return self._doser_storage
        elif normalized == "light":
            return self._light_storage
        else:
            raise ValueError(f"Unknown device type: {device_type}")

    def _format_message(self, device_type: Optional[str], category: str) -> str:
        """Format a user-friendly error message for device errors."""
        kind = (device_type or "device").lower()
        label = kind.capitalize()
        if category == "not_found":
            return f"{label} not found"
        if category == "wrong_type":
            return f"Device is not a {kind}"
        if category == "not_connected":
            return f"{label} not connected"
        if category == "not_reachable":
            return f"{label} not reachable"
        return f"{label} error"

    def _get_device_kind(self, device: BaseDevice | Type[BaseDevice]) -> Optional[str]:
        """Return the device kind attribute lowercased if present."""
        kind = getattr(device, "device_kind", None)
        if isinstance(kind, str) and kind:
            return kind.lower()
        return None

    async def _auto_discover_worker(self) -> None:
        """Background worker that auto-discovers and connects devices."""
        try:
            logger.info("Auto-discover worker: scanning for supported devices")
            connected_any = await self._auto_discover_and_connect()
            device_count = len(self._list_all_devices())
            if connected_any and device_count > 0:
                logger.info("Auto-discover worker: discovered devices saved to storage")
            else:
                if self._auto_reconnect:
                    logger.info("Auto-discover found no devices; scheduling reconnect worker")
                    if self._reconnect_task is None or self._reconnect_task.done():
                        self._reconnect_task = asyncio.create_task(self._reconnect_and_refresh())
                        logger.info("Reconnect worker scheduled by auto-discover worker")
        except asyncio.CancelledError:
            logger.info("Auto-discover worker cancelled")
            raise
        except Exception:  # pragma: no cover - runtime diagnostics
            logger.exception("Auto-discover worker failed unexpectedly")

    async def _auto_discover_and_connect(self) -> bool:
        supported = await discover_supported_devices(timeout=5.0)
        if not supported:
            logger.info("No supported devices discovered")
            return False
        logger.info("Discovered %d supported devices", len(supported))
        connected_any = False
        for device, model_class in supported:
            address = device.address
            try:
                inferred_type = self._get_device_kind(model_class)
                if not inferred_type:
                    logger.debug(
                        "Skipping unsupported model for %s: %s",
                        address,
                        model_class,
                    )
                    continue
                status = await self.connect_device(address, inferred_type)
                # Status already persisted to unified storage via connect_device
                logger.info("Connected to %s (%s)", address, status.device_type)
                connected_any = True
            except Exception as exc:  # pragma: no cover - runtime diagnostics
                logger.warning("Connect failed for %s: %s", address, exc)
                continue
        return connected_any

    async def _reconnect_and_refresh(self) -> None:
        """Reconnect to known devices without aggressively refreshing status.

        For aquarium devices, we just ensure connectivity without polling status,
        since status only changes when users explicitly modify configuration.
        """
        try:
            # Load devices from storage and attempt reconnection
            all_devices = self._list_all_devices()
            for device_info in all_devices:
                address = device_info["device_id"]
                device_type = device_info["device_type"]
                try:
                    logger.info(
                        "Attempting reconnect to %s (type=%s)",
                        address,
                        device_type,
                    )
                    await self.connect_device(address, device_type)
                    logger.info(
                        "Device %s is now available (not refreshing status)",
                        address,
                    )
                except Exception as exc:  # pragma: no cover - runtime diagnostics
                    logger.warning("Could not reconnect to %s: %s", address, exc)
                    continue
        except asyncio.CancelledError:
            logger.info("Reconnect worker cancelled")
            raise
        except Exception:  # pragma: no cover - runtime diagnostics
            logger.exception("Reconnect worker failed unexpectedly")

    async def _ensure_device(self, address: str, device_type: Optional[str] = None) -> BaseDevice:
        expected_kind = device_type.lower() if device_type else None
        async with self._lock:
            if expected_kind:
                device_dict = self._devices.get(expected_kind, {})
                current_device = device_dict.get(address)
                if current_device:
                    return current_device
                # If we have a device of this kind but different address, keep it
                # Only disconnect if we're replacing the same address

            # Retry logic: try up to 3 times with delays
            # Device might not be advertising immediately after scan
            device = None
            max_retries = 3

            for attempt in range(max_retries):
                try:
                    device = await get_device_from_address(address)
                    break
                except Exception as exc:
                    if attempt < max_retries - 1:
                        # Wait before retrying (exponential backoff: 0.5s, 1s)
                        wait_time = 0.5 * (2**attempt)
                        logger.warning(
                            f"Device {address} not found on attempt {attempt + 1}/{max_retries}, "
                            f"retrying in {wait_time}s: {exc}"
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        raise HTTPException(
                            status_code=404,
                            detail=self._format_message(expected_kind, "not_found"),
                        ) from exc

            if device is None:  # Should not happen but safety check
                raise HTTPException(status_code=500, detail="Device acquisition failed")

            kind = self._get_device_kind(device)
            if kind is None:
                raise HTTPException(status_code=400, detail="Unsupported device type")
            if expected_kind and kind != expected_kind:
                raise HTTPException(
                    status_code=400,
                    detail=self._format_message(expected_kind, "wrong_type"),
                )

            # Store the device
            if kind not in self._devices:
                self._devices[kind] = {}
            self._devices[kind][address] = device

            # Update primary address for backward compatibility
            self._addresses[kind] = address

            return device

    async def _refresh_device_status(
        self, device_type: str, *, persist: bool = True
    ) -> CachedStatus:
        normalized = device_type.lower()
        device: BaseDevice | None = None
        address: Optional[str] = None
        async with self._lock:
            address = self._addresses.get(normalized)
            if address:
                device_dict = self._devices.get(normalized, {})
                device = device_dict.get(address)
            if not device or not address:
                raise HTTPException(
                    status_code=400,
                    detail=self._format_message(normalized, "not_connected"),
                )
            serializer_name = getattr(device.__class__, "status_serializer", None)
            if serializer_name is None:
                serializer_name = getattr(device, "status_serializer", None)

        if serializer_name is None:
            raise HTTPException(
                status_code=500,
                detail=f"No serializer defined for {normalized}",
            )

        serializer = getattr(_utils, serializer_name, None)
        if serializer is None:  # pragma: no cover - defensive guard
            raise HTTPException(
                status_code=500,
                detail=f"Missing serializer '{serializer_name}' for {normalized}",
            )
        try:
            logger.debug("Requesting %s status from %s", normalized, address)
            await device.request_status()
        except (BleakNotFoundError, BleakConnectionError) as exc:
            logger.warning(
                "%s not reachable %s: %s",
                normalized.capitalize(),
                address,
                exc,
            )
            raise HTTPException(
                status_code=404,
                detail=self._format_message(normalized, "not_reachable"),
            ) from exc
        await asyncio.sleep(STATUS_CAPTURE_WAIT_SECONDS)
        status_obj = getattr(device, "last_status", None)
        if not status_obj:
            raise HTTPException(
                status_code=500,
                detail=f"No status received from {normalized}",
            )
        try:
            parsed = serializer(status_obj)
        except TypeError:
            if not is_dataclass(status_obj):
                parsed = dict(vars(status_obj))
            else:
                raise
        raw_payload = getattr(status_obj, "raw_payload", None)
        raw_hex = raw_payload.hex() if isinstance(raw_payload, (bytes, bytearray)) else None
        # For light devices, capture color channels; for others, None
        channels = getattr(device, "colors", None) if normalized == "light" else None
        cached = CachedStatus(
            address=address,
            device_type=normalized,
            raw_payload=raw_hex,
            parsed=parsed,
            updated_at=time.time(),
            model_name=getattr(device, "model_name", None),
            channels=channels,
        )
        if persist:
            # Update device file with new status (no in-memory cache needed)
            status_dict = {
                "model_name": cached.model_name,
                "raw_payload": cached.raw_payload,
                "parsed": cached.parsed,
                "updated_at": cached.updated_at,
                "channels": cached.channels,
            }
            storage = self._get_storage_for_type(normalized)
            storage.update_device_status(address, status_dict)
            logger.debug(f"Updated device file for {address}")
        return cached

    async def _load_device_configuration(self, address: str, device_kind: str) -> None:
        """Load saved configuration for a device after connection.

        Only loads existing configurations - does not auto-create new ones.
        Configurations should be explicitly created when users edit/create them
        or send commands that require persistence.

        Args:
            address: Device MAC address
            device_kind: Type of device ('doser' or 'light')
        """
        if device_kind == "doser":
            saved_config = self._doser_storage.get_device(address)
            if saved_config:
                logger.info(
                    f"Loaded saved configuration for doser {address} "
                    f"with {len(saved_config.configurations)} configuration(s)"
                )
            else:
                logger.debug(
                    f"No saved configuration found for doser {address} "
                    "(will be created when user configures device)"
                )

        elif device_kind == "light":
            saved_profile = self._light_storage.get_device(address)
            if saved_profile:
                logger.info(
                    f"Loaded saved profile for light {address} "
                    f"with {len(saved_profile.configurations)} configuration(s)"
                )
            else:
                logger.debug(
                    f"No saved profile found for light {address} "
                    "(will be created when user configures device)"
                )

    async def _load_state(self) -> None:
        """Load device state from device files.

        Loads last known status and metadata for all devices.
        """
        # Load from device files
        all_devices = self._list_all_devices()
        logger.info(f"Loading state from {len(all_devices)} device files")

        # Metadata already loaded in __init__() before storage instances were created

        # Load command history from separate file
        if COMMAND_HISTORY_PATH.exists():
            try:
                command_data = json.loads(COMMAND_HISTORY_PATH.read_text(encoding="utf-8"))
                self._commands = {address: cmd_list for address, cmd_list in command_data.items()}
                logger.info(f"Loaded command history for {len(self._commands)} devices")
            except (json.JSONDecodeError, OSError) as exc:
                logger.error(f"Failed to load command history: {exc}")
                self._commands = {}
        else:
            self._commands = {}

    def current_device_address(self, device_type: str) -> Optional[str]:
        """Return the current primary address for a device type, if known."""
        return self._addresses.get(device_type.lower())

    def get_devices_by_kind(self, device_type: str) -> Dict[str, BaseDevice]:
        """Return all connected devices of the specified kind."""
        return self._devices.get(device_type.lower(), {}).copy()

    def get_all_devices(self) -> Dict[str, Dict[str, BaseDevice]]:
        """Return all connected devices organized by kind and address."""
        result = {}
        for kind, device_dict in self._devices.items():
            result[kind] = device_dict.copy()
        return result

    def get_device_count(self) -> int:
        """Return the total number of connected devices."""
        return sum(len(device_dict) for device_dict in self._devices.values())

    def get_status_snapshot(self) -> Dict[str, CachedStatus]:
        """Return a snapshot of all device statuses from storage."""
        snapshot: Dict[str, CachedStatus] = {}

        # Load all devices from storage
        all_devices = self._list_all_devices()
        for device_info in all_devices:
            last_status = device_info.get("last_status")
            if last_status:
                # Convert status dict to CachedStatus
                cached = CachedStatus(
                    address=device_info["device_id"],
                    device_type=device_info["device_type"],
                    raw_payload=last_status.get("raw_payload"),
                    parsed=last_status.get("parsed"),
                    updated_at=last_status.get("updated_at"),
                    model_name=last_status.get("model_name"),
                    channels=last_status.get("channels"),
                )
                snapshot[device_info["device_id"]] = cached

        return snapshot

    async def start(self) -> None:
        """Start background tasks and load persisted state."""
        await self._load_state()
        # Count devices from storage instead of cache
        device_count = len(self._list_all_devices())
        logger.info("Service start: loaded %d devices", device_count)
        logger.info(
            "Settings: auto_discover_on_start=%s, " "auto_reconnect=%s, capture_wait=%.2fs",
            self._auto_discover_on_start,
            self._auto_reconnect,
            STATUS_CAPTURE_WAIT_SECONDS,
        )
        discover_scheduled = False
        if device_count == 0 and self._auto_discover_on_start:
            try:
                logger.info("Auto-discover enabled; scheduling background scan")
                self._discover_task = asyncio.create_task(self._auto_discover_worker())
                discover_scheduled = True
                logger.info("Auto-discover worker scheduled in background")
            except Exception as exc:  # pragma: no cover - runtime diagnostics
                logger.warning("Failed to schedule auto-discover: %s", exc)
        if self._auto_reconnect:
            if discover_scheduled:
                logger.info("Auto-reconnect enabled; will be decided by auto-discover worker")
            else:
                logger.info("Auto-reconnect enabled; attempting reconnect to cached devices")
                self._reconnect_task = asyncio.create_task(self._reconnect_and_refresh())
                logger.info("Reconnect worker scheduled in background")

    async def stop(self) -> None:
        """Stop background workers and persist current service state."""
        if self._reconnect_task is not None:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                logger.debug("Reconnect task cancelled during stop()")
        if self._discover_task is not None:
            self._discover_task.cancel()
            try:
                await self._discover_task
            except asyncio.CancelledError:
                logger.debug("Auto-discover task cancelled during stop()")

        # Disconnect all devices
        async with self._lock:
            for kind_devices in self._devices.values():
                for device in kind_devices.values():
                    await device.disconnect()
            self._devices.clear()
            self._addresses.clear()

    async def scan_devices(self, timeout: float = 5.0) -> list[Dict[str, Any]]:
        """Scan for BLE devices and return those matching known models."""
        supported = await discover_supported_devices(timeout=timeout)
        result: list[Dict[str, Any]] = []
        for device, model_class in supported:
            device_type = self._get_device_kind(model_class) or "unknown"
            result.append(
                {
                    "address": device.address,
                    "name": device.name,
                    "product": getattr(model_class, "model_name", device.name),
                    "device_type": device_type,
                }
            )
        return result

    async def connect_device(self, address: str, device_type: Optional[str] = None) -> CachedStatus:
        """Connect to a device by address and fetch its status.

        Establishes connectivity and requests initial status with parsed data.
        """
        device = await self._ensure_device(address, device_type)
        device_kind = self._get_device_kind(device)
        if device_kind is None:
            raise HTTPException(status_code=400, detail="Unsupported device type")

        # Load saved configuration if available
        await self._load_device_configuration(address, device_kind)

        # Request and parse status to populate initial data
        try:
            await device.request_status()
            await asyncio.sleep(STATUS_CAPTURE_WAIT_SECONDS)

            # Get the serializer for this device type
            serializer_name = getattr(device.__class__, "status_serializer", None)
            if serializer_name is None:
                serializer_name = getattr(device, "status_serializer", None)

            if serializer_name is None:
                raise HTTPException(
                    status_code=500,
                    detail=f"No serializer defined for {device_kind}",
                )

            serializer = getattr(_utils, serializer_name, None)
            if serializer is None:
                raise HTTPException(
                    status_code=500,
                    detail=f"Missing serializer '{serializer_name}' for {device_kind}",
                )

            # Parse the status
            status_obj = getattr(device, "last_status", None)
            if not status_obj:
                raise HTTPException(
                    status_code=500,
                    detail=f"No status received from {device_kind}",
                )

            try:
                parsed = serializer(status_obj)
            except TypeError:
                if not is_dataclass(status_obj):
                    parsed = dict(vars(status_obj))
                else:
                    raise

            raw_payload = getattr(status_obj, "raw_payload", None)
            raw_hex = raw_payload.hex() if isinstance(raw_payload, (bytes, bytearray)) else None
            # For light devices, capture color channels; for others, None
            channels = getattr(device, "colors", None) if device_kind == "light" else None

            # Create and persist status
            timestamp = time.time()
            cached_status = CachedStatus(
                address=address,
                device_type=device_kind,
                raw_payload=raw_hex,
                parsed=parsed,
                updated_at=timestamp,
                model_name=getattr(device, "model_name", None),
                channels=channels,
            )

            # Persist to storage
            status_dict = {
                "model_name": cached_status.model_name,
                "raw_payload": cached_status.raw_payload,
                "parsed": cached_status.parsed,
                "updated_at": cached_status.updated_at,
                "channels": cached_status.channels,
            }
            storage = self._get_storage_for_type(device_kind.lower())
            storage.update_device_status(address, status_dict)

            return cached_status

        except (BleakNotFoundError, BleakConnectionError) as exc:
            logger.warning(
                "Could not get status from %s during connect: %s",
                address,
                exc,
            )
            raise HTTPException(
                status_code=404,
                detail=self._format_message(device_kind, "not_reachable"),
            ) from exc
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning(
                "Error getting status for %s during connect: %s",
                address,
                exc,
            )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to connect to {device_kind}: {str(exc)}",
            ) from exc

    async def disconnect_device(self, address: str) -> None:
        """Disconnect a connected device by address if present."""
        async with self._lock:
            for kind, device_dict in list(self._devices.items()):
                if address in device_dict:
                    device = device_dict[address]
                    await device.disconnect()
                    del device_dict[address]
                    if not device_dict:
                        del self._devices[kind]
                    # Update primary address if we disconnected the primary device
                    if self._addresses.get(kind) == address:
                        # If there are other devices of this kind, pick one as primary
                        if device_dict:
                            self._addresses[kind] = next(iter(device_dict.keys()))
                        else:
                            self._addresses.pop(kind, None)
                    break

    async def request_status(self, address: str) -> CachedStatus:
        """Request and return the status for a device by address."""
        logger.info("Manual request_status for %s", address)

        # Try to get device type from storage first by checking both storages
        device_type = None
        all_devices = self._list_all_devices()
        for device_info in all_devices:
            if device_info["device_id"] == address:
                device_type = device_info["device_type"]
                break

        if device_type:
            try:
                return await self.connect_device(address, device_type)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

        try:
            device = await get_device_from_address(address)
        except Exception as exc:
            logger.warning("request_status: device not found for %s: %s", address, exc)
            raise HTTPException(status_code=404, detail="Device not found") from exc

        device_type = self._get_device_kind(device)
        if not device_type:
            raise HTTPException(status_code=400, detail="Unsupported device type")

        logger.debug(
            "request_status: identified %s at %s, ensuring connection",
            device_type,
            address,
        )
        return await self.connect_device(address, device_type)

    # Doser settings

    async def set_doser_schedule(
        self,
        address: str,
        *,
        head_index: int,
        volume_tenths_ml: int,
        hour: int,
        minute: int,
        weekdays: Optional[Sequence[commands.PumpWeekday]] = None,
        confirm: bool = False,
        wait_seconds: float = 1.5,
    ) -> CachedStatus:
        """Set a doser schedule on the given device address."""
        return await device_commands.set_doser_schedule(
            self,
            address,
            head_index=head_index,
            volume_tenths_ml=volume_tenths_ml,
            hour=hour,
            minute=minute,
            weekdays=weekdays,
            confirm=confirm,
            wait_seconds=wait_seconds,
        )

    # Light settings

    async def set_light_brightness(
        self, address: str, *, brightness: int, color: str | int = 0
    ) -> CachedStatus:
        """Set brightness (and optional color) for a light device."""
        return await device_commands.set_light_brightness(
            self, address, brightness=brightness, color=color
        )

    async def turn_light_on(self, address: str) -> CachedStatus:
        """Turn the light device at the address on."""
        return await device_commands.turn_light_on(self, address)

    async def turn_light_off(self, address: str) -> CachedStatus:
        """Turn the light device at the address off."""
        return await device_commands.turn_light_off(self, address)

    async def enable_auto_mode(self, address: str) -> CachedStatus:
        """Enable auto mode on the specified light device."""
        return await device_commands.enable_auto_mode(self, address)

    async def set_manual_mode(self, address: str) -> CachedStatus:
        """Switch the specified light device to manual mode."""
        return await device_commands.set_manual_mode(self, address)

    async def reset_auto_settings(self, address: str) -> CachedStatus:
        """Reset auto mode settings on the specified light device."""
        return await device_commands.reset_auto_settings(self, address)

    async def add_light_auto_setting(
        self,
        address: str,
        *,
        sunrise: _time,
        sunset: _time,
        brightness: int,
        ramp_up_minutes: int = 0,
        weekdays: list[commands.LightWeekday] | None = None,
    ) -> CachedStatus:
        """Add an auto program to a light device."""
        return await device_commands.add_light_auto_setting(
            self,
            address,
            sunrise=sunrise,
            sunset=sunset,
            brightness=brightness,
            ramp_up_minutes=ramp_up_minutes,
            weekdays=weekdays,
        )

    async def get_live_statuses(self) -> tuple[list[CachedStatus], list[str]]:
        """Capture live statuses for known device kinds and return results.

        Returns a tuple of (results, errors).
        """
        results: list[CachedStatus] = []
        errors: list[str] = []

        # Use the generic capture helper for both device kinds. This keeps a
        # single patch point for tests and avoids duplicating collection logic.
        for device_kind in ("doser", "light"):
            try:
                status = await self._refresh_device_status(device_kind, persist=False)
            except HTTPException as exc:
                if exc.status_code == 400:
                    continue
                errors.append(str(exc.detail))
            else:
                results.append(status)

        return results, errors

    # Command persistence methods

    def save_command(self, command_record) -> None:
        """Save a command record to persistent storage."""
        address = command_record.address
        if address not in self._commands:
            self._commands[address] = []

        # Update existing command or append new one
        command_dict = command_record.to_dict()
        existing_commands = self._commands[address]

        # Try to find existing command by ID
        for i, existing in enumerate(existing_commands):
            if existing.get("id") == command_record.id:
                existing_commands[i] = command_dict
                break
        else:
            # New command, append it
            existing_commands.append(command_dict)

            # Keep only last 50 commands per device
            if len(existing_commands) > 50:
                existing_commands[:] = existing_commands[-50:]

    def get_commands(self, address: str, limit: int = 20):
        """Get recent commands for a device."""
        commands = self._commands.get(address, [])
        return commands[-limit:] if limit else commands

    def get_command(self, address: str, command_id: str):
        """Get a specific command by ID."""
        commands = self._commands.get(address, [])
        for cmd in commands:
            if cmd.get("id") == command_id:
                return cmd
        return None
