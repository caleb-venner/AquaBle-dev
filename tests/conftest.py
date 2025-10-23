"""Test configuration ensuring the src package is importable."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


# Test file addresses to clean up if accidentally created in real ~/.aqua-ble/devices
TEST_DEVICE_ADDRESSES = [
    "11:22:33:44:55:66",
    "AA:BB:CC:DD:EE:FF",
    "58159AE1-5E0A-7915-3207-7868CBF2C600",
    "A6A644D2-08CB-9326-46AA-7087FB7DD70A",
]


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_device_files():
    """Cleanup any test device files from the real ~/.aqua-ble/devices directory.

    This runs after all tests complete to remove any dummy device files that
    were accidentally created in the production directory during interactive testing.
    """
    devices_dir = Path.home() / ".aqua-ble" / "devices"

    yield  # Tests run here

    # Cleanup after all tests
    if devices_dir.exists():
        for address in TEST_DEVICE_ADDRESSES:
            # Convert address to safe filename (replace : with _)
            safe_name = address.replace(":", "_")
            test_file = devices_dir / f"{safe_name}.json"

            if test_file.exists():
                try:
                    test_file.unlink()
                    print(f"Cleaned up test device file: {test_file}")
                except Exception as e:
                    print(f"Failed to cleanup {test_file}: {e}")


# ========== Test Fixtures for Device Configurations ==========
# These functions create default configurations for testing purposes only.
# They are NOT used in production code.


def create_default_doser_config(address: str, name: str | None = None):
    """Create a default configuration for a new doser device (TEST FIXTURE).

    Args:
        address: The device MAC address
        name: Optional friendly name for the device

    Returns:
        A DoserDevice with default configuration for 4 heads
    """
    from aquable.storage import (
        Calibration,
        ConfigurationRevision,
        DeviceConfiguration,
        DoserDevice,
        DoserHead,
        DoserHeadStats,
        Recurrence,
        SingleSchedule,
    )
    from aquable.utils import now_iso as _now_iso

    device_name = name or f"Doser {address[-8:]}"
    timestamp = _now_iso()

    # Create default heads (all inactive by default)
    default_heads = []
    for idx in range(1, 5):
        head = DoserHead(
            index=idx,  # type: ignore[arg-type]
            label=f"Head {idx}",
            active=False,
            schedule=SingleSchedule(mode="single", dailyDoseMl=10.0, startTime="09:00"),
            recurrence=Recurrence(
                days=[
                    "monday",
                    "tuesday",
                    "wednesday",
                    "thursday",
                    "friday",
                    "saturday",
                    "sunday",
                ]
            ),
            missedDoseCompensation=False,
            calibration=Calibration(mlPerSecond=0.1, lastCalibratedAt=timestamp),
            stats=DoserHeadStats(dosesToday=0, mlDispensedToday=0.0),
        )
        default_heads.append(head)

    # Create initial revision
    revision = ConfigurationRevision(
        revision=1,
        savedAt=timestamp,
        heads=default_heads,
        note="Initial configuration",
        savedBy="system",
    )

    # Create default configuration
    configuration = DeviceConfiguration(
        id="default",
        name="Default Configuration",
        description="Auto-generated default configuration",
        createdAt=timestamp,
        updatedAt=timestamp,
        revisions=[revision],
    )

    # Create device
    device = DoserDevice(
        id=address,
        name=device_name,
        configurations=[configuration],
        activeConfigurationId="default",
        createdAt=timestamp,
        updatedAt=timestamp,
    )

    return device


def create_default_light_profile(
    address: str,
    name: str | None = None,
    channels: list[dict] | None = None,
):
    """Create a default profile for a new light device (TEST FIXTURE).

    Args:
        address: The device MAC address
        name: Optional friendly name for the device
        channels: Optional list of channel definitions from device

    Returns:
        A LightDevice with default manual profile
    """
    from aquable.storage import (
        ChannelDef,
        LightConfiguration,
        LightDevice,
        LightProfileRevision,
        ManualProfile,
    )
    from aquable.utils import now_iso as _now_iso

    device_name = name or f"Light {address[-8:]}"
    timestamp = _now_iso()

    # Create default channel definitions if not provided
    if not channels:
        channel_defs = [
            ChannelDef(key="white", label="White", min=0, max=100, step=1),
            ChannelDef(key="red", label="Red", min=0, max=100, step=1),
            ChannelDef(key="green", label="Green", min=0, max=100, step=1),
            ChannelDef(key="blue", label="Blue", min=0, max=100, step=1),
        ]
    else:
        channel_defs = [
            ChannelDef(
                key=ch.get("name", f"channel{ch.get('index', 0)}").lower(),
                label=ch.get("name", f"Channel {ch.get('index', 0)}"),
                min=0,
                max=100,
                step=1,
            )
            for ch in channels
        ]

    # Create default manual profile (all channels at 50%)
    default_levels = {ch.key: 50 for ch in channel_defs}

    # Create a profile revision with the manual profile
    revision = LightProfileRevision(
        revision=1,
        savedAt=timestamp,
        profile=ManualProfile(mode="manual", levels=default_levels),
        note="Auto-generated default configuration",
    )

    # Create a configuration containing the revision
    default_config = LightConfiguration(
        id="default",
        name="Default Configuration",
        description="Auto-generated default configuration",
        revisions=[revision],
        createdAt=timestamp,
        updatedAt=timestamp,
    )

    # Create device
    device = LightDevice(
        id=address,
        name=device_name,
        channels=channel_defs,
        configurations=[default_config],
        activeConfigurationId="default",
        createdAt=timestamp,
        updatedAt=timestamp,
    )

    return device
