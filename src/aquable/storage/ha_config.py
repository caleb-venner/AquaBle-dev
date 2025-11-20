"""
Home Assistant Entity Configuration Storage

Manages persistent storage of configured Home Assistant entities in ~/.aquable/ha_entities.json
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Entity types supported
EntityType = Literal["switch", "script"]


class HAEntity(BaseModel):
    """Home Assistant entity configuration"""
    entity_id: str = Field(..., description="Entity ID (e.g., switch.aquarium_pump)")
    label: str = Field(..., description="User-friendly label")
    type: EntityType = Field(..., description="Entity type (switch or script)")


class HAConfig(BaseModel):
    """Home Assistant configuration"""
    entities: List[HAEntity] = Field(default_factory=list, description="Configured entities")


class HAConfigStorage:
    """Storage manager for Home Assistant entity configuration"""

    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize storage.

        Args:
            base_path: Base directory for storage (defaults to ~/.aquable)
        """
        if base_path is None:
            base_path = Path.home() / ".aquable"
        
        self.base_path = base_path
        self.config_file = base_path / "ha_entities.json"
        
        # Ensure directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)

    def load(self) -> HAConfig:
        """
        Load configuration from disk.

        Returns:
            HAConfig object (empty if file doesn't exist)
        """
        if not self.config_file.exists():
            logger.info("No HA config file found, returning empty config")
            return HAConfig()

        try:
            with open(self.config_file, "r") as f:
                data = json.load(f)
            config = HAConfig(**data)
            logger.info(f"Loaded {len(config.entities)} HA entities from disk")
            return config
        except Exception as e:
            logger.error(f"Error loading HA config: {e}")
            return HAConfig()

    def save(self, config: HAConfig) -> bool:
        """
        Save configuration to disk.

        Args:
            config: HAConfig object to save

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.config_file, "w") as f:
                json.dump(config.model_dump(), f, indent=2)
            logger.info(f"Saved {len(config.entities)} HA entities to disk")
            return True
        except Exception as e:
            logger.error(f"Error saving HA config: {e}")
            return False

    def add_entity(self, entity_id: str, label: str, entity_type: EntityType) -> bool:
        """
        Add an entity to the configuration.

        Args:
            entity_id: Entity ID
            label: User-friendly label
            entity_type: Entity type (switch or script)

        Returns:
            True if successful, False otherwise
        """
        config = self.load()
        
        # Check if entity already exists
        if any(e.entity_id == entity_id for e in config.entities):
            logger.warning(f"Entity already exists: {entity_id}")
            return False

        # Add new entity
        entity = HAEntity(entity_id=entity_id, label=label, type=entity_type)
        config.entities.append(entity)
        
        return self.save(config)

    def remove_entity(self, entity_id: str) -> bool:
        """
        Remove an entity from the configuration.

        Args:
            entity_id: Entity ID to remove

        Returns:
            True if successful, False otherwise
        """
        config = self.load()
        
        # Filter out the entity
        original_count = len(config.entities)
        config.entities = [e for e in config.entities if e.entity_id != entity_id]
        
        if len(config.entities) == original_count:
            logger.warning(f"Entity not found: {entity_id}")
            return False

        return self.save(config)

    def get_entity(self, entity_id: str) -> Optional[HAEntity]:
        """
        Get a specific entity configuration.

        Args:
            entity_id: Entity ID to retrieve

        Returns:
            HAEntity if found, None otherwise
        """
        config = self.load()
        for entity in config.entities:
            if entity.entity_id == entity_id:
                return entity
        return None

    def list_entities(self) -> List[HAEntity]:
        """
        Get all configured entities.

        Returns:
            List of HAEntity objects
        """
        config = self.load()
        return config.entities

    def clear(self) -> bool:
        """
        Clear all entities from configuration.

        Returns:
            True if successful, False otherwise
        """
        config = HAConfig()
        return self.save(config)


# Global storage instance
_ha_storage: Optional[HAConfigStorage] = None


def get_ha_storage() -> HAConfigStorage:
    """Get the global Home Assistant storage instance"""
    global _ha_storage
    if _ha_storage is None:
        _ha_storage = HAConfigStorage()
    return _ha_storage
