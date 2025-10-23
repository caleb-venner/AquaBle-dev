"""Tests for the CommandExecutor and configuration saving logic."""

import asyncio
from datetime import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from conftest import create_default_doser_config, create_default_light_profile

from aquable.ble_service import BLEService, CachedStatus
from aquable.commands.encoder import LightWeekday, PumpWeekday
from aquable.commands_model import CommandRequest
from aquable.config import CommandExecutor

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def ble_service(tmp_path: Path) -> BLEService:
    """Fixture for a BLEService instance with temporary storage."""
    with patch("aquable.ble_service.CONFIG_DIR", tmp_path):
        service = BLEService()
        # Disable auto-saving at the service level for more controlled testing
        service._auto_save_config = True
        return service


@pytest.fixture
def command_executor(ble_service: BLEService) -> CommandExecutor:
    """Fixture for a CommandExecutor instance."""
    return CommandExecutor(ble_service)


async def test_execute_set_doser_schedule_success(
    command_executor: CommandExecutor, ble_service: BLEService, tmp_path: Path
):
    """Verify set_schedule command execution and config persistence for dosers."""
    address = "AA:BB:CC:DD:EE:FF"
    device_config = create_default_doser_config(address)
    ble_service._doser_storage.upsert_device(device_config)

    # Mock the BLE command method
    mock_status = CachedStatus(
        address=address,
        device_type="doser",
        raw_payload=None,
        parsed={},
        updated_at=0,
    )
    ble_service.set_doser_schedule = AsyncMock(return_value=mock_status)

    # Define the command request
    request = CommandRequest(
        action="set_schedule",
        args={
            "head_index": 1,  # Use 1-based indexing to match default config
            "volume_tenths_ml": 55,  # 5.5ml
            "hour": 10,
            "minute": 30,
            "weekdays": [
                PumpWeekday.monday,
                PumpWeekday.wednesday,
                PumpWeekday.friday,
            ],
        },
    )

    # Execute the command
    record = await command_executor.execute_command(address, request)

    # --- Assertions ---
    # 1. Check command record status
    assert record.status == "success"
    assert record.error is None

    # 2. Verify the BLE service method was called correctly
    ble_service.set_doser_schedule.assert_awaited_once()
    call_args = ble_service.set_doser_schedule.call_args
    assert call_args[0][0] == address
    assert call_args[1]["head_index"] == 1  # Updated to match 1-based indexing
    assert call_args[1]["volume_tenths_ml"] == 55
    assert call_args[1]["hour"] == 10
    assert call_args[1]["minute"] == 30
    assert call_args[1]["weekdays"] == [
        PumpWeekday.monday,
        PumpWeekday.wednesday,
        PumpWeekday.friday,
    ]

    # 3. Verify the configuration was saved correctly
    saved_config = ble_service._doser_storage.get_device(address)
    assert saved_config is not None
    active_config = saved_config.get_active_configuration()
    head_config = active_config.latest_revision().heads[0]  # First head in list (index=1)
    assert head_config is not None
    assert head_config.schedule.dailyDoseMl == 5.5
    assert head_config.schedule.startTime == "10:30"
    assert set(head_config.recurrence.days) == {"monday", "wednesday", "friday"}


async def test_execute_add_light_auto_setting_success(
    command_executor: CommandExecutor, ble_service: BLEService, tmp_path: Path
):
    """Verify add_auto_setting command and config persistence for lights."""
    address = "11:22:33:44:55:66"
    device_profile = create_default_light_profile(address)
    ble_service._light_storage.upsert_device(device_profile)

    # Mock _get_device_channels to return RGBW channels
    command_executor._get_device_channels = lambda address: [
        {"name": "white", "index": 0},
        {"name": "red", "index": 1},
        {"name": "green", "index": 2},
        {"name": "blue", "index": 3},
    ]

    # Mock the BLE command method
    mock_status = CachedStatus(
        address=address,
        device_type="light",
        raw_payload=None,
        parsed={},
        updated_at=0,
    )
    ble_service.add_light_auto_setting = AsyncMock(return_value=mock_status)

    # Define the command request
    request = CommandRequest(
        action="add_auto_setting",
        args={
            "sunrise": "08:00",
            "sunset": "20:00",
            "brightness": 80,
            "ramp_up_minutes": 15,
            "weekdays": [LightWeekday.saturday, LightWeekday.sunday],
        },
    )

    # Execute the command
    record = await command_executor.execute_command(address, request)

    # --- Assertions ---
    # 1. Check command record status
    assert record.status == "success"
    assert record.error is None

    # 2. Verify the BLE service method was called correctly
    ble_service.add_light_auto_setting.assert_awaited_once()
    call_args = ble_service.add_light_auto_setting.call_args
    assert call_args[0][0] == address
    assert call_args[1]["sunrise"] == time(8, 0)
    assert call_args[1]["sunset"] == time(20, 0)
    assert call_args[1]["brightness"] == 80
    assert call_args[1]["weekdays"] == [
        LightWeekday.saturday,
        LightWeekday.sunday,
    ]

    # 3. Verify the configuration was saved correctly
    saved_profile = ble_service._light_storage.get_device(address)
    assert saved_profile is not None
    active_config = saved_profile.get_active_configuration()
    profile_revision = active_config.latest_revision()

    # After add_auto_setting, the profile should be converted to AutoProfile
    from aquable.storage import AutoProfile

    assert isinstance(profile_revision.profile, AutoProfile)

    auto_profile = profile_revision.profile
    assert len(auto_profile.programs) == 1
    program = auto_profile.programs[0]
    assert program.sunrise == "08:00"
    assert program.sunset == "20:00"
    assert program.rampMinutes == 15
    # Check weekdays conversion from enum to string
    assert set(program.days) == {"saturday", "sunday"}


async def test_execute_set_brightness_saves_config(
    command_executor: CommandExecutor, ble_service: BLEService, tmp_path: Path
):
    """Verify set_brightness command saves manual profile to light device config."""
    address = "11:22:33:44:55:66"
    device_profile = create_default_light_profile(address)
    ble_service._light_storage.upsert_device(device_profile)

    # Mock _get_device_channels to return RGBW channels
    command_executor._get_device_channels = lambda address: [
        {"name": "white", "index": 0},
        {"name": "red", "index": 1},
        {"name": "green", "index": 2},
        {"name": "blue", "index": 3},
    ]

    # Mock the BLE command method
    mock_status = CachedStatus(
        address=address,
        device_type="light",
        raw_payload=None,
        parsed={},
        updated_at=0,
    )
    ble_service.set_light_brightness = AsyncMock(return_value=mock_status)

    # Get initial revision count
    initial_device = ble_service._light_storage.get_device(address)
    assert initial_device is not None
    initial_config = initial_device.get_active_configuration()
    initial_revision_count = len(initial_config.revisions)

    # Define the command request - set red channel to 75%
    request = CommandRequest(
        action="set_brightness",
        args={
            "brightness": 75,
            "color": 1,  # Red channel
        },
    )

    # Execute the command
    record = await command_executor.execute_command(address, request)

    # --- Assertions ---
    # 1. Check command record status
    assert record.status == "success"
    assert record.error is None

    # 2. Verify the BLE service method was called correctly
    ble_service.set_light_brightness.assert_awaited_once()
    call_args = ble_service.set_light_brightness.call_args
    assert call_args[0][0] == address
    assert call_args[1]["brightness"] == 75
    assert call_args[1]["color"] == 1

    # 3. Verify the configuration was saved with new manual profile revision
    saved_profile = ble_service._light_storage.get_device(address)
    assert saved_profile is not None
    active_config = saved_profile.get_active_configuration()
    profile_revision = active_config.latest_revision()

    # Should have a new revision
    assert len(active_config.revisions) == initial_revision_count + 1

    # New revision should be a ManualProfile
    from aquable.storage import ManualProfile

    assert isinstance(profile_revision.profile, ManualProfile)

    manual_profile = profile_revision.profile
    # Red channel (index 1) should be 75, others should be 0
    assert manual_profile.levels["white"] == 0
    assert manual_profile.levels["red"] == 75
    assert manual_profile.levels["green"] == 0
    assert manual_profile.levels["blue"] == 0
    assert profile_revision.note == "Manual brightness adjustment"
    assert profile_revision.savedBy == "user"
