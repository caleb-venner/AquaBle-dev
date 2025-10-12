"""Migration script to consolidate state.json and device files into unified storage.

This script:
1. Reads state.json to get device statuses
2. Reads existing device/*.json files for configurations
3. Merges them into unified device files with both status and configuration
4. Backs up old files before migration
5. Creates global_settings.json for timezone
"""

import json
import logging
import shutil
from pathlib import Path
from typing import Any, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_storage(config_dir: Path) -> None:
    """Migrate from dual storage to unified device files.

    Args:
        config_dir: The ~/.aqua-ble directory
    """
    logger.info(f"Starting storage migration for {config_dir}")

    state_file = config_dir / "state.json"
    devices_dir = config_dir / "devices"
    backup_dir = config_dir / "backup_pre_migration"

    # Create backup directory
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Backup existing files
    if state_file.exists():
        logger.info("Backing up state.json")
        shutil.copy2(state_file, backup_dir / "state.json")

    if devices_dir.exists():
        logger.info("Backing up devices directory")
        backup_devices = backup_dir / "devices"
        if backup_devices.exists():
            shutil.rmtree(backup_devices)
        shutil.copytree(devices_dir, backup_devices)

    # Load state.json
    state_data: Dict[str, Any] = {}
    if state_file.exists():
        try:
            state_data = json.loads(state_file.read_text())
            logger.info(
                f"Loaded state.json with {len(state_data.get('devices', {}))} devices"
            )
        except json.JSONDecodeError as exc:
            logger.error(f"Failed to parse state.json: {exc}")
            return

    devices_status = state_data.get("devices", {})
    device_metadata = state_data.get("device_metadata", {})
    display_timezone = state_data.get("display_timezone")

    # Ensure devices directory exists
    devices_dir.mkdir(parents=True, exist_ok=True)

    # Process each device in state.json
    migrated_count = 0
    for address, status_data in devices_status.items():
        logger.info(f"Migrating device {address}")

        device_type = status_data.get("device_type")
        safe_id = address.replace(":", "_")
        device_file = devices_dir / f"{safe_id}.json"

        # Check if device configuration file already exists
        existing_config = None
        if device_file.exists():
            try:
                existing_data = json.loads(device_file.read_text())
                # Extract device_data if in new format, otherwise use whole thing
                if "device_data" in existing_data:
                    existing_config = existing_data["device_data"]
                else:
                    existing_config = existing_data
                logger.info(f"  Found existing configuration for {address}")
            except json.JSONDecodeError:
                logger.warning(
                    f"  Could not parse existing config for {address}"
                )

        # Build unified device file
        unified_device = {
            "device_type": device_type,
            "device_id": address,
            "last_updated": status_data.get("updated_at", 0),
        }

        # Add metadata if exists
        if address in device_metadata:
            unified_device["metadata"] = device_metadata[address]

        # Add last_status from state.json
        unified_device["last_status"] = {
            "model_name": status_data.get("model_name"),
            "raw_payload": status_data.get("raw_payload"),
            "parsed": status_data.get("parsed"),
            "updated_at": status_data.get("updated_at", 0),
        }

        # Only add channels for light devices
        if device_type == "light" and "channels" in status_data:
            unified_device["last_status"]["channels"] = status_data["channels"]

        # Add device_data (configuration)
        if existing_config:
            # Use existing configuration
            unified_device["device_data"] = existing_config
        else:
            # Create minimal configuration
            if device_type == "doser":
                unified_device["device_data"] = {
                    "id": address,
                    "configurations": [],
                }
            elif device_type == "light":
                unified_device["device_data"] = {
                    "id": address,
                    "channels": [
                        {
                            "key": "red",
                            "label": "Red",
                            "min": 0,
                            "max": 100,
                            "step": 1,
                        },
                        {
                            "key": "green",
                            "label": "Green",
                            "min": 0,
                            "max": 100,
                            "step": 1,
                        },
                        {
                            "key": "blue",
                            "label": "Blue",
                            "min": 0,
                            "max": 100,
                            "step": 1,
                        },
                        {
                            "key": "white",
                            "label": "White",
                            "min": 0,
                            "max": 100,
                            "step": 1,
                        },
                    ],
                    "configurations": [],
                }
            logger.info(f"  Created minimal configuration for {address}")

        # Write unified device file
        tmp_file = device_file.with_suffix(".tmp")
        tmp_file.write_text(
            json.dumps(unified_device, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        tmp_file.replace(device_file)
        migrated_count += 1
        logger.info(f"  Migrated {address} to unified format")

    # Create global settings file for timezone
    if display_timezone:
        settings_file = config_dir / "global_settings.json"
        settings = {"display_timezone": display_timezone}
        settings_file.write_text(
            json.dumps(settings, indent=2, sort_keys=True), encoding="utf-8"
        )
        logger.info(
            f"Created global_settings.json with timezone: {display_timezone}"
        )

    # Archive state.json (don't delete, keep as reference)
    if state_file.exists():
        archive_file = config_dir / "state.json.archived"
        state_file.rename(archive_file)
        logger.info(f"Archived state.json to {archive_file}")

    logger.info(
        f"Migration complete! Migrated {migrated_count} devices. "
        f"Backups saved to {backup_dir}"
    )


def main():
    """Run migration on default config directory."""
    import os

    config_dir_str = os.environ.get("AQUA_BLE_CONFIG_DIR", "~/.aqua-ble")
    config_dir = Path(config_dir_str).expanduser()

    if not config_dir.exists():
        logger.info(
            f"No config directory found at {config_dir}, nothing to migrate"
        )
        return

    state_file = config_dir / "state.json"
    if not state_file.exists():
        logger.info("No state.json found, nothing to migrate")
        return

    # Check if already migrated
    archived_state = config_dir / "state.json.archived"
    if archived_state.exists():
        logger.info("Migration already completed (found state.json.archived)")
        return

    response = input(
        f"This will migrate your storage in {config_dir}. "
        "A backup will be created. Continue? (y/n): "
    )
    if response.lower() != "y":
        logger.info("Migration cancelled")
        return

    migrate_storage(config_dir)


if __name__ == "__main__":
    main()
