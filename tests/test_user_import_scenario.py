"""Test for user's specific old export file import scenario."""

import json
from unittest.mock import MagicMock

import pytest

from aquable.storage.doser import DoserStorage


@pytest.fixture
def user_old_export():
    """Load the user's specific old export file structure."""
    return {
        "address": "58159AE1-5E0A-7915-3207-7868CBF2C600",
        "deviceType": "doser",
        "config": {
            "id": "58159AE1-5E0A-7915-3207-7868CBF2C600",
            "name": None,
            "headNames": None,
            "autoReconnect": False,
            "configurations": [
                {
                    "id": "4c41e75a-83f0-4cd6-94f7-b1a45be7d422",
                    "name": "Default",
                    "revisions": [
                        {
                            "revision": 1,
                            "savedAt": "2025-10-25T21:36:09+11:00",
                            "heads": [
                                {
                                    "index": 1,
                                    "label": None,
                                    "active": False,
                                    "schedule": {
                                        "mode": "single",
                                        "dailyDoseMl": 1,
                                        "startTime": "00:00",
                                    },
                                    "recurrence": {"days": ["monday"]},
                                    "missedDoseCompensation": False,
                                    "volumeTracking": None,
                                    "calibration": {
                                        "mlPerSecond": 1,
                                        "lastCalibratedAt": "2025-10-25T21:36:09+11:00",
                                    },
                                    "stats": None,
                                },
                                {
                                    "index": 2,
                                    "label": None,
                                    "active": False,
                                    "schedule": {
                                        "mode": "single",
                                        "dailyDoseMl": 1,
                                        "startTime": "00:00",
                                    },
                                    "recurrence": {"days": ["monday"]},
                                    "missedDoseCompensation": False,
                                    "volumeTracking": None,
                                    "calibration": {
                                        "mlPerSecond": 1,
                                        "lastCalibratedAt": "2025-10-25T21:36:09+11:00",
                                    },
                                    "stats": None,
                                },
                                {
                                    "index": 3,
                                    "label": None,
                                    "active": False,
                                    "schedule": {
                                        "mode": "single",
                                        "dailyDoseMl": 1,
                                        "startTime": "00:00",
                                    },
                                    "recurrence": {"days": ["monday"]},
                                    "missedDoseCompensation": False,
                                    "volumeTracking": None,
                                    "calibration": {
                                        "mlPerSecond": 1,
                                        "lastCalibratedAt": "2025-10-25T21:36:09+11:00",
                                    },
                                    "stats": None,
                                },
                                {
                                    "index": 4,
                                    "label": None,
                                    "active": False,
                                    "schedule": {
                                        "mode": "single",
                                        "dailyDoseMl": 1,
                                        "startTime": "00:00",
                                    },
                                    "recurrence": {"days": ["monday"]},
                                    "missedDoseCompensation": False,
                                    "volumeTracking": None,
                                    "calibration": {
                                        "mlPerSecond": 1,
                                        "lastCalibratedAt": "2025-10-25T21:36:09+11:00",
                                    },
                                    "stats": None,
                                },
                            ],
                            "note": "Default configuration created on first discovery",
                            "savedBy": "system",
                        }
                    ],
                    "createdAt": "2025-10-25T21:36:09+11:00",
                    "updatedAt": "2025-10-25T21:36:09+11:00",
                    "description": "Default configuration created on first discovery",
                }
            ],
            "activeConfigurationId": "4c41e75a-83f0-4cd6-94f7-b1a45be7d422",
            "createdAt": "2025-10-25T21:36:09+11:00",
            "updatedAt": "2025-10-25T21:36:09+11:00",
        },
        "exportedAt": "2025-10-25T10:44:09.882Z",
    }


@pytest.fixture
def storage(tmp_path):
    """Create a test DoserStorage instance."""
    mock_service = MagicMock()
    storage = DoserStorage(tmp_path, mock_service)
    return storage


def test_user_scenario_import_old_export_to_new_device(storage, user_old_export):
    """
    Test the user's exact scenario:
    1. User has old export from macOS (UUID address)
    2. User wants to import to a new device on Home Assistant (MAC address)

    This is the core cross-platform workflow the name-based matching enables.
    """
    # Old device on macOS
    old_uuid = "58159AE1-5E0A-7915-3207-7868CBF2C600"

    # New device on Home Assistant (same physical Dosing Pump)
    new_mac = "E4:3A:D5:3A:D8:02"

    # Create a device placeholder on new system
    new_device = storage.create_default_device(new_mac)
    storage.upsert_device(new_device)

    # Import the old config to the new device
    # This is what /import-to-device/{device_type}/{device_id} enables
    result = storage.import_device_config(user_old_export, new_mac)

    # Verify import succeeded
    assert result is not None
    assert result.id == new_mac
    assert len(result.configurations) == 1
    assert result.configurations[0].name == "Default"

    # Verify the config with 4 heads was preserved
    revision = result.configurations[0].revisions[0]
    assert len(revision.heads) == 4
    for head in revision.heads:
        assert head.schedule.mode == "single"
        assert head.schedule.dailyDoseMl == 1


def test_old_export_includes_all_info_needed_for_manual_import(user_old_export):
    """
    Verify the old export format contains all info needed for
    the /import-to-device/{device_type}/{device_id} endpoint.
    """
    # Verify old format has required fields
    assert "address" in user_old_export  # Source device UUID
    assert "deviceType" in user_old_export  # Device type for validation
    assert "config" in user_old_export  # Device configuration data
    assert "exportedAt" in user_old_export  # Timestamp

    # These are sufficient for manual import with device address
    device_type = user_old_export["deviceType"]
    config_data = user_old_export["config"]

    assert device_type == "doser"
    assert isinstance(config_data, dict)
    assert "configurations" in config_data
