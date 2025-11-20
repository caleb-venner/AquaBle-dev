"""
Tests for Home Assistant configuration storage
"""

import json
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from aquable.storage.ha_config import HAConfigStorage, HAEntity, HAConfig


@pytest.fixture
def temp_storage():
    """Create temporary storage for testing"""
    with TemporaryDirectory() as tmpdir:
        yield HAConfigStorage(base_path=Path(tmpdir))


class TestHAConfigStorage:
    """Test HA configuration storage operations"""

    def test_load_empty_config(self, temp_storage):
        """Should return empty config when file doesn't exist"""
        config = temp_storage.load()
        assert isinstance(config, HAConfig)
        assert len(config.entities) == 0

    def test_save_and_load_config(self, temp_storage):
        """Should persist and retrieve configuration"""
        entity = HAEntity(
            entity_id="switch.test",
            label="Test Switch",
            type="switch"
        )
        config = HAConfig(entities=[entity])
        
        success = temp_storage.save(config)
        assert success is True
        
        loaded_config = temp_storage.load()
        assert len(loaded_config.entities) == 1
        assert loaded_config.entities[0].entity_id == "switch.test"
        assert loaded_config.entities[0].label == "Test Switch"
        assert loaded_config.entities[0].type == "switch"

    def test_add_entity(self, temp_storage):
        """Should add entity to configuration"""
        success = temp_storage.add_entity(
            entity_id="switch.pump",
            label="Main Pump",
            entity_type="switch"
        )
        assert success is True
        
        config = temp_storage.load()
        assert len(config.entities) == 1
        assert config.entities[0].entity_id == "switch.pump"

    def test_add_duplicate_entity(self, temp_storage):
        """Should not add duplicate entity"""
        temp_storage.add_entity("switch.test", "Test", "switch")
        
        success = temp_storage.add_entity("switch.test", "Test Duplicate", "switch")
        assert success is False
        
        config = temp_storage.load()
        assert len(config.entities) == 1

    def test_remove_entity(self, temp_storage):
        """Should remove entity from configuration"""
        temp_storage.add_entity("switch.test", "Test", "switch")
        
        success = temp_storage.remove_entity("switch.test")
        assert success is True
        
        config = temp_storage.load()
        assert len(config.entities) == 0

    def test_remove_nonexistent_entity(self, temp_storage):
        """Should fail when removing nonexistent entity"""
        success = temp_storage.remove_entity("switch.nonexistent")
        assert success is False

    def test_get_entity(self, temp_storage):
        """Should retrieve specific entity"""
        temp_storage.add_entity("switch.test", "Test", "switch")
        
        entity = temp_storage.get_entity("switch.test")
        assert entity is not None
        assert entity.entity_id == "switch.test"
        assert entity.label == "Test"

    def test_get_nonexistent_entity(self, temp_storage):
        """Should return None for nonexistent entity"""
        entity = temp_storage.get_entity("switch.nonexistent")
        assert entity is None

    def test_list_entities(self, temp_storage):
        """Should list all entities"""
        temp_storage.add_entity("switch.pump", "Pump", "switch")
        temp_storage.add_entity("script.routine", "Routine", "script")
        
        entities = temp_storage.list_entities()
        assert len(entities) == 2
        assert entities[0].entity_id == "switch.pump"
        assert entities[1].entity_id == "script.routine"

    def test_clear_config(self, temp_storage):
        """Should clear all entities"""
        temp_storage.add_entity("switch.test", "Test", "switch")
        
        success = temp_storage.clear()
        assert success is True
        
        config = temp_storage.load()
        assert len(config.entities) == 0

    def test_json_format(self, temp_storage):
        """Should save in correct JSON format"""
        temp_storage.add_entity("switch.test", "Test", "switch")
        
        with open(temp_storage.config_file, "r") as f:
            data = json.load(f)
        
        assert "entities" in data
        assert len(data["entities"]) == 1
        assert data["entities"][0]["entity_id"] == "switch.test"
        assert data["entities"][0]["label"] == "Test"
        assert data["entities"][0]["type"] == "switch"


class TestHAEntity:
    """Test HAEntity model validation"""

    def test_valid_switch_entity(self):
        """Should create valid switch entity"""
        entity = HAEntity(
            entity_id="switch.test",
            label="Test",
            type="switch"
        )
        assert entity.entity_id == "switch.test"
        assert entity.type == "switch"

    def test_valid_script_entity(self):
        """Should create valid script entity"""
        entity = HAEntity(
            entity_id="script.routine",
            label="Routine",
            type="script"
        )
        assert entity.entity_id == "script.routine"
        assert entity.type == "script"
