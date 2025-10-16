"""Global application settings storage.

Manages settings that apply across all devices, such as display timezone.
Stored in ~/.aquable/global_settings.json
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


class GlobalSettings:
    """Manages global application settings."""

    def __init__(self, config_dir: Path):
        """Initialize global settings manager.

        Args:
            config_dir: The configuration directory (e.g., ~/.aquable)
        """
        self._config_dir = Path(config_dir)
        self._settings_file = self._config_dir / "global_settings.json"
        self._settings: Dict[str, Any] = {}
        self._load_settings()

    def _load_settings(self) -> None:
        """Load settings from file."""
        if not self._settings_file.exists():
            logger.info("No global settings file found, using defaults")
            self._settings = {}
            return

        try:
            self._settings = json.loads(
                self._settings_file.read_text(encoding="utf-8")
            )
            logger.info(f"Loaded global settings from {self._settings_file}")
        except (json.JSONDecodeError, OSError) as exc:
            logger.error(f"Failed to load global settings: {exc}")
            self._settings = {}

    def _save_settings(self) -> None:
        """Save settings to file."""
        self._config_dir.mkdir(parents=True, exist_ok=True)

        tmp_file = self._settings_file.with_suffix(".tmp")
        tmp_file.write_text(
            json.dumps(self._settings, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        tmp_file.replace(self._settings_file)
        logger.debug(f"Saved global settings to {self._settings_file}")

    def get_display_timezone(self) -> str | None:
        """Get the display timezone setting.

        Returns:
            Timezone string (e.g., 'Australia/Sydney') or None if not set
        """
        return self._settings.get("display_timezone")

    def set_display_timezone(self, timezone: str) -> None:
        """Set the display timezone.

        Args:
            timezone: IANA timezone string (e.g., 'Australia/Sydney')
        """
        self._settings["display_timezone"] = timezone
        self._save_settings()
        logger.info(f"Set display timezone to {timezone}")

    def get_all_settings(self) -> Dict[str, Any]:
        """Get all settings as a dictionary.

        Returns:
            Copy of all settings
        """
        return dict(self._settings)
