"""Configuration management for File Copy Manager application"""

import json
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigManager:
    """Manages application configuration with JSON persistence"""

    DEFAULT_CONFIG = {
        "default_source_folder": "",
        "default_destination_folder": "",
        "last_extension": "",
        "preserve_structure": True,
        "folder_structure": "flat",
        "number_duplicates": True,
        "recursive_search": True
    }

    def __init__(self, config_path: Path):
        """
        Initialize the configuration manager

        Args:
            config_path: Path to the configuration file
        """
        self.config_path = config_path
        self._config = self._load()

    def _load(self) -> Dict[str, Any]:
        """Load configuration from file or create default"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    return {**self.DEFAULT_CONFIG, **config}
            except (json.JSONDecodeError, OSError):
                pass

        # Return default config (will be saved later if needed)
        return self.DEFAULT_CONFIG.copy()

    def save(self) -> bool:
        """
        Save current configuration to file

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self._config, f, indent=4)
            return True
        except OSError:
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value

        Args:
            key: Configuration key
            default: Default value if key doesn't exist

        Returns:
            Configuration value or default
        """
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value

        Args:
            key: Configuration key
            value: Value to set
        """
        self._config[key] = value

    def update(self, updates: Dict[str, Any]) -> None:
        """
        Update multiple configuration values

        Args:
            updates: Dictionary of key-value pairs to update
        """
        self._config.update(updates)

    def get_all(self) -> Dict[str, Any]:
        """
        Get all configuration values

        Returns:
            Copy of all configuration data
        """
        return self._config.copy()
