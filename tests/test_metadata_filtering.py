"""Tests for metadata file filtering in storage."""

import json
import tempfile
from pathlib import Path

from conftest import create_default_doser_config

from aquable.storage import DoserStorage, LightStorage


def test_doser_storage_excludes_metadata_files():
    """Test that DoserStorage.list_devices() excludes .metadata.json files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = DoserStorage(Path(temp_dir), {})

        # Create a regular device using the proper method
        device = create_default_doser_config("AA:BB:CC:DD:EE:FF", "Test Device")
        storage.upsert_device(device)

        # Create a metadata file (should be excluded)
        metadata_data = {
            "id": "AA:BB:CC:DD:EE:FF",
            "name": "Test Device",
            "timezone": "UTC",
            "headNames": {1: "Head 1", 2: "Head 2"},  # Keys should be integers
            "createdAt": "2023-01-01T00:00:00Z",
        }
        metadata_file = Path(temp_dir) / "AA_BB_CC_DD_EE_FF.metadata.json"
        metadata_file.write_text(json.dumps(metadata_data))

        # List devices should only return the regular device, not the metadata
        devices = storage.list_devices()
        assert len(devices) == 1
        assert devices[0].id == "AA:BB:CC:DD:EE:FF"


def test_light_storage_excludes_metadata_files():
    """Test that LightStorage.list_devices() excludes .metadata.json files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = LightStorage(Path(temp_dir), {})

        # Create a regular device file with proper structure
        device_data = {
            "device_type": "light",
            "device_data": {
                "id": "AA:BB:CC:DD:EE:FF",
                "name": "Test Light",
                "channels": [
                    {
                        "key": "red",
                        "label": "Red",
                        "min": 0,
                        "max": 100,
                        "step": 1,
                    }
                ],
                "configurations": [
                    {
                        "id": "config-1",
                        "name": "Test Configuration",
                        "createdAt": "2023-01-01T00:00:00Z",
                        "updatedAt": "2023-01-01T00:00:00Z",
                        "revisions": [
                            {
                                "revision": 1,
                                "savedAt": "2023-01-01T00:00:00Z",
                                "profile": {
                                    "mode": "manual",
                                    "levels": {"red": 50},
                                },
                                "note": "Test revision",
                            }
                        ],
                    }
                ],
                "activeConfigurationId": "config-1",
            },
        }
        device_file = Path(temp_dir) / "AA_BB_CC_DD_EE_FF.json"
        device_file.write_text(json.dumps(device_data))

        # Create a metadata file (should be excluded)
        metadata_data = {
            "id": "AA:BB:CC:DD:EE:FF",
            "name": "Test Light",
            "createdAt": "2023-01-01T00:00:00Z",
        }
        metadata_file = Path(temp_dir) / "AA_BB_CC_DD_EE_FF.metadata.json"
        metadata_file.write_text(json.dumps(metadata_data))

        # List devices should only return the regular device, not the metadata
        devices = storage.list_devices()
        assert len(devices) == 1
        assert devices[0].id == "AA:BB:CC:DD:EE:FF"


def test_doser_storage_metadata_listing_works():
    """Test that deprecated metadata listing returns empty list (Phase 4 deprecation)."""
    with tempfile.TemporaryDirectory() as temp_dir:
        metadata_dict = {
            "AA:BB:CC:DD:EE:FF": {
                "id": "AA:BB:CC:DD:EE:FF",
                "name": "Test Doser",
                "timezone": "UTC",
                "headNames": {1: "Head 1"},
                "createdAt": "2023-01-01T00:00:00Z",
            }
        }
        storage = DoserStorage(Path(temp_dir), metadata_dict)

        # List devices should be empty (no device files written)
        devices = storage.list_devices()
        assert len(devices) == 0

        # Deprecated: list_device_metadata now returns empty list (backward compat)
        metadata_list = storage.list_device_metadata()
        assert len(metadata_list) == 0


def test_doser_storage_excludes_light_metadata_files():
    """Test that deprecated DoserStorage.list_device_metadata() returns empty list.

    After Phase 4 deprecation, metadata methods are no-ops for backward compat.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        metadata_dict = {
            "AA:BB:CC:DD:EE:FF": {
                "id": "AA:BB:CC:DD:EE:FF",
                "name": "Test Doser",
                "timezone": "UTC",
                "headNames": {1: "Head 1"},
                "createdAt": "2023-01-01T00:00:00Z",
            }
        }
        storage = DoserStorage(Path(temp_dir), metadata_dict)

        # Deprecated: list_device_metadata returns empty list (backward compat)
        metadata_list = storage.list_device_metadata()
        assert len(metadata_list) == 0
