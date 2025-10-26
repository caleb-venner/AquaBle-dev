"""Tests for name-based device configuration export/import.

Verifies that device configurations can be exported from one machine and
imported to another using device name matching (solves macOS UUID vs Linux MAC issue).
"""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from aquable.storage import DoserDevice, DoserStorage, LightDevice, LightStorage


class TestNameBasedExportImport:
    """Test cross-platform device configuration transfer using name matching."""

    def test_device_name_stored_in_status(self):
        """Test that device_name is stored separately from status."""
        with TemporaryDirectory() as tmpdir:
            storage = DoserStorage(Path(tmpdir), {})

            # Update status with device_name
            status = {
                "device_name": "Dosing Pump-7E68CBF2C600",
                "model_name": "Commander 4",
                "parsed": {"some": "data"},
                "updated_at": 1234567890.0,
            }
            storage.update_device_status("AA:BB:CC:DD:EE:FF", status)

            # Read the file to verify structure
            device_file = Path(tmpdir) / "AA_BB_CC_DD_EE_FF.json"
            assert device_file.exists()

            data = json.loads(device_file.read_text())
            assert data["device_name"] == "Dosing Pump-7E68CBF2C600"
            assert "device_name" not in data["last_status"]  # Should be extracted
            assert data["last_status"]["model_name"] == "Commander 4"

    def test_find_device_by_name(self):
        """Test finding a device's address by its name."""
        with TemporaryDirectory() as tmpdir:
            storage = DoserStorage(Path(tmpdir), {})

            # Create two devices with different addresses but known names
            storage.update_device_status(
                "11:22:33:44:55:66",
                {"device_name": "Dosing Pump-ABC123", "model_name": "Commander 1"},
            )
            storage.update_device_status(
                "AA:BB:CC:DD:EE:FF",
                {"device_name": "Dosing Pump-XYZ789", "model_name": "Commander 4"},
            )

            # Find by name
            found_id = storage.find_device_by_name("Dosing Pump-XYZ789")
            assert found_id == "AA:BB:CC:DD:EE:FF"

            # Not found
            not_found = storage.find_device_by_name("NonExistent Device")
            assert not_found is None

    def test_export_device_config(self):
        """Test exporting a device configuration with name."""
        with TemporaryDirectory() as tmpdir:
            storage = DoserStorage(Path(tmpdir), {})

            # Create a device with configuration using storage helper
            device = storage.create_default_device("AA:BB:CC:DD:EE:FF")
            device.name = "Test Doser"
            storage.upsert_device(device)

            # Add device name via status update
            storage.update_device_status(
                "AA:BB:CC:DD:EE:FF",
                {"device_name": "Dosing Pump-7E68CBF2C600", "model_name": "Commander 4"},
            )

            # Export configuration
            exported = storage.export_device_config("AA:BB:CC:DD:EE:FF")

            assert exported is not None
            assert exported["device_type"] == "doser"
            assert exported["device_name"] == "Dosing Pump-7E68CBF2C600"
            assert exported["device_data"] is not None
            assert exported["device_data"]["id"] == "AA:BB:CC:DD:EE:FF"
            assert "exported_at" in exported

    def test_import_device_config_to_new_address(self):
        """Test importing a configuration to a device with a different address."""
        with TemporaryDirectory() as tmpdir:
            storage = DoserStorage(Path(tmpdir), {})

            # Original device on "machine 1" (Linux with MAC address)
            original_device = storage.create_default_device("E4:3A:D5:3A:D8:02")
            original_device.name = "My Doser"
            storage.upsert_device(original_device)
            storage.update_device_status(
                "E4:3A:D5:3A:D8:02",
                {"device_name": "Dosing Pump-7E68CBF2C600", "model_name": "Commander 4"},
            )

            # Export from "machine 1"
            exported = storage.export_device_config("E4:3A:D5:3A:D8:02")
            assert exported is not None

            # Simulate "machine 2" (macOS with UUID) - same device, different address
            # First, connect to the device to get its name stored
            storage.update_device_status(
                "A6A644D2-08CB-9326-46AA-7087FB7DD70A",
                {"device_name": "Dosing Pump-7E68CBF2C600", "model_name": "Commander 4"},
            )

            # Import configuration using the new address
            imported = storage.import_device_config(
                exported, "A6A644D2-08CB-9326-46AA-7087FB7DD70A"
            )

            assert imported is not None
            assert imported.id == "A6A644D2-08CB-9326-46AA-7087FB7DD70A"
            assert imported.name == "My Doser"  # Configuration transferred

    def test_complete_cross_platform_workflow(self):
        """Test complete export/import workflow between two 'machines'."""
        # Machine 1 (Linux - MAC addresses)
        with TemporaryDirectory() as tmpdir1:
            storage1 = LightStorage(Path(tmpdir1), {})

            # Create and configure a light device
            device1 = storage1.create_default_device("E4:3A:D5:3A:D8:02")
            device1.name = "Aquarium Light"
            storage1.upsert_device(device1)
            storage1.update_device_status(
                "E4:3A:D5:3A:D8:02",
                {"device_name": "WRGB II Pro-7087FB7DD70A", "model_name": "WRGB II Pro"},
            )

            # Export configuration
            exported = storage1.export_device_config("E4:3A:D5:3A:D8:02")
            assert exported is not None
            assert exported["device_name"] == "WRGB II Pro-7087FB7DD70A"

        # Machine 2 (macOS - UUIDs)
        with TemporaryDirectory() as tmpdir2:
            storage2 = LightStorage(Path(tmpdir2), {})

            # Device discovered on macOS with UUID address
            macos_address = "A6A644D2-08CB-9326-46AA-7087FB7DD70A"

            # When device connects, its name is stored
            storage2.update_device_status(
                macos_address,
                {"device_name": "WRGB II Pro-7087FB7DD70A", "model_name": "WRGB II Pro"},
            )

            # Find the device by name
            found_address = storage2.find_device_by_name("WRGB II Pro-7087FB7DD70A")
            assert found_address == macos_address

            # Import the configuration
            imported = storage2.import_device_config(exported, found_address)
            assert imported is not None
            assert imported.id == macos_address
            assert imported.name == "Aquarium Light"  # Config from machine 1
            assert len(imported.channels) == len(device1.channels)  # Settings preserved

    def test_export_nonexistent_device_returns_none(self):
        """Test that exporting a nonexistent device returns None."""
        with TemporaryDirectory() as tmpdir:
            storage = DoserStorage(Path(tmpdir), {})
            exported = storage.export_device_config("99:99:99:99:99:99")
            assert exported is None

    def test_import_wrong_device_type_fails(self):
        """Test that importing a config of wrong type fails gracefully."""
        with TemporaryDirectory() as tmpdir:
            doser_storage = DoserStorage(Path(tmpdir), {})
            light_storage = LightStorage(Path(tmpdir), {})

            # Create a doser config
            device = doser_storage.create_default_device("AA:BB:CC:DD:EE:FF")
            device.name = "Test"
            doser_storage.upsert_device(device)
            exported = doser_storage.export_device_config("AA:BB:CC:DD:EE:FF")

            # Try to import doser config into light storage
            assert exported is not None  # Ensure we have a config to test with
            result = light_storage.import_device_config(exported, "11:22:33:44:55:66")
            assert result is None  # Should fail gracefully
