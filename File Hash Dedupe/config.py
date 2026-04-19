"""Configuration management for File Hash Dedupe"""

import json
from pathlib import Path
from typing import Optional


class ConfigManager:
    """Manages application configuration with JSON persistence"""

    def __init__(self, config_file: Path):
        """
        Initialize the config manager

        Args:
            config_file: Path to the JSON config file
        """
        self.config_file = config_file
        self._config = self._load_config()

    def _load_config(self) -> dict:
        """Load configuration from file or return defaults"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return self._get_defaults()

    def _get_defaults(self) -> dict:
        """Get default configuration values"""
        import os
        # Default to half the logical CPU count, clamped between 2 and 16
        cpu_count = os.cpu_count() or 4
        default_workers = max(2, min(16, cpu_count // 2))
        return {
            'source_folder': '',
            'recursive': True,
            'window_geometry': None,
            'io_workers': default_workers,
        }

    def save(self) -> None:
        """Save current configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self._config, f, indent=2)
        except IOError:
            pass

    def get(self, key: str, default=None):
        """Get a configuration value"""
        return self._config.get(key, default)

    def set(self, key: str, value) -> None:
        """Set a configuration value"""
        self._config[key] = value

    @property
    def source_folder(self) -> str:
        return self._config.get('source_folder', '')

    @source_folder.setter
    def source_folder(self, value: str) -> None:
        self._config['source_folder'] = value

    @property
    def recursive(self) -> bool:
        return self._config.get('recursive', True)

    @recursive.setter
    def recursive(self, value: bool) -> None:
        self._config['recursive'] = value

    @property
    def window_geometry(self) -> Optional[str]:
        return self._config.get('window_geometry')

    @window_geometry.setter
    def window_geometry(self, value: str) -> None:
        self._config['window_geometry'] = value
