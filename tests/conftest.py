"""Test configuration ensuring the src package is importable."""

from __future__ import annotations

import shutil
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
