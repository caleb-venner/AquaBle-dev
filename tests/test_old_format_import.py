"""Tests for backwards compatibility with old export format."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from aquable.storage.doser import DoserStorage


@pytest.fixture
def old_format_export():
    """Create an old-format export (pre-name-based-matching)."""
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
                    "id": "test-config-id",
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
                                }
                            ],
                            "note": "Default configuration",
                            "savedBy": "system",
                        }
                    ],
                    "createdAt": "2025-10-25T21:36:09+11:00",
                    "updatedAt": "2025-10-25T21:36:09+11:00",
                    "description": "Default configuration",
                }
            ],
            "activeConfigurationId": "test-config-id",
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


def test_import_old_format_with_deviceType_key(storage, old_format_export):
    """Test that old format with 'deviceType' key is accepted."""
    # Ensure target device exists
    target_device_id = "E4:3A:D5:3A:D8:02"
    default_device = storage.create_default_device(target_device_id)
    storage.upsert_device(default_device)

    # Import old format
    result = storage.import_device_config(old_format_export, target_device_id)
    assert result is not None
    assert result.id == target_device_id


def test_import_old_format_with_config_key(storage, old_format_export):
    """Test that old format with 'config' key is extracted correctly."""
    target_device_id = "E4:3A:D5:3A:D8:02"
    default_device = storage.create_default_device(target_device_id)
    storage.upsert_device(default_device)

    # Verify the old format uses 'config' instead of 'device_data'
    assert "config" in old_format_export
    assert "device_data" not in old_format_export
    assert "deviceType" in old_format_export
    assert "device_type" not in old_format_export

    # Import should still work
    result = storage.import_device_config(old_format_export, target_device_id)
    assert result is not None


def test_import_old_format_preserves_configurations(storage, old_format_export):
    """Test that old format configurations are preserved during import."""
    target_device_id = "E4:3A:D5:3A:D8:02"
    default_device = storage.create_default_device(target_device_id)
    storage.upsert_device(default_device)

    original_config_count = len(old_format_export["config"]["configurations"])

    result = storage.import_device_config(old_format_export, target_device_id)
    assert result is not None
    assert len(result.configurations) == original_config_count


def test_import_old_format_rejects_wrong_device_type(storage):
    """Test that old format with wrong device_type is rejected."""
    # Create a config for "light" type but try to import to doser storage
    light_config = {
        "deviceType": "light",  # Wrong type
        "config": {"id": "test", "channels": []},
    }

    target_device_id = "E4:3A:D5:3A:D8:02"
    default_device = storage.create_default_device(target_device_id)
    storage.upsert_device(default_device)

    # Import should fail
    result = storage.import_device_config(light_config, target_device_id)
    assert result is None


def test_old_format_address_available_for_manual_import(old_format_export):
    """Test that old format exports include 'address' for manual import."""
    assert "address" in old_format_export
    assert old_format_export["address"] == "58159AE1-5E0A-7915-3207-7868CBF2C600"
    # This allows the `/import-to-device/{device_type}/{device_id}` endpoint
    # to work by parsing the source address from the old export


def test_old_format_missing_device_name_in_new_format():
    """Test that old formats don't have device_name (by design)."""
    old_format = {"deviceType": "doser", "config": {}, "address": "some-id"}
    new_format = {"device_type": "doser", "device_data": {}, "device_name": "My Device"}

    assert "device_name" not in old_format
    assert "device_name" in new_format
    # This confirms old and new formats are structurally different
    # and our dual-format support is necessary
