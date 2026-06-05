"""Tests for functional storage I/O."""

from dataclasses import dataclass
from pathlib import Path

from src.aquable.domain.storage import list_device_files, load_device, save_device


@dataclass
class DummyDevice:
    id: str
    name: str

def test_save_and_load_device(tmp_path: Path):
    device = DummyDevice(id="AA:BB:CC", name="Test Doser")
    
    # Save it
    save_device(tmp_path, device, "doser")
    
    # List files
    files = list_device_files(tmp_path)
    assert len(files) == 1
    assert files[0].name == "AA_BB_CC.json"
    
    # Load it directly from JSON (as a dict instead of a class since our dummy loader is just a raw dict lambda)
    loaded = load_device(tmp_path, "AA:BB:CC", "doser", parser_fn=lambda x: x)
    assert loaded is not None
    assert loaded["id"] == "AA:BB:CC"
    assert loaded["name"] == "Test Doser"

def test_device_type_mismatch(tmp_path: Path):
    device = DummyDevice(id="AA:BB:CC", name="Test Doser")
    save_device(tmp_path, device, "doser")
    
    # Try to load as light
    loaded = load_device(tmp_path, "AA:BB:CC", "light", parser_fn=lambda x: x)
    assert loaded is None
