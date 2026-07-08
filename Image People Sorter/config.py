"""Configuration management for Image People Sorter"""

import json
from pathlib import Path
from typing import Any, Dict


DEFAULT_CONFIG = {
    "default_source_folder": "",
    "default_destination_folder": "",
    "recursive_search": True,
    "copy_mode": True,  # True = Copy, False = Move
    "confidence_threshold": 30,  # percent (0-100), maps to YOLO confidence 0.0-1.0
    "review_mode": False,
    "write_csv_report": True,
}


class ConfigManager:
    """Manages application configuration with JSON persistence"""

    def __init__(self, config_file: Path):
        """
        Initialize the configuration manager

        Args:
            config_file: Path to the JSON configuration file
        """
        self.config_file = config_file
        self.config: Dict[str, Any] = DEFAULT_CONFIG.copy()
        self.load()

    def load(self) -> None:
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    saved_config = json.load(f)
                    # Merge with defaults to handle new config options
                    self.config = {**DEFAULT_CONFIG, **saved_config}
            except (json.JSONDecodeError, IOError):
                self.config = DEFAULT_CONFIG.copy()
        else:
            self.config = DEFAULT_CONFIG.copy()

    def save(self) -> None:
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except IOError as e:
            print(f"Error saving config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value

        Args:
            key: Configuration key
            value: Value to set
        """
        self.config[key] = value
