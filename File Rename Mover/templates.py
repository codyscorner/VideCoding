"""Template management for File Rename Mover application"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


class TemplateManager:
    """Manages saved configuration templates"""

    # Keys that are saved in templates (all user-configurable settings)
    TEMPLATE_KEYS = [
        "default_source_folder",
        "default_destination_folder",
        "last_extension",
        "last_rename_to",
        "sort_by",
        "sort_order",
        "pattern_type",
        "datetime_format",
        "include_counter",
        "folder_structure",
        "base_name_folder",
        "custom_pattern"
    ]

    def __init__(self, templates_path: Path):
        """
        Initialize the template manager

        Args:
            templates_path: Path to the templates JSON file
        """
        self.templates_path = templates_path
        self._templates: Dict[str, Dict[str, Any]] = self._load()

    def _load(self) -> Dict[str, Dict[str, Any]]:
        """Load templates from file"""
        if self.templates_path.exists():
            try:
                with open(self.templates_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    def _save(self) -> bool:
        """
        Save templates to file

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.templates_path, 'w') as f:
                json.dump(self._templates, f, indent=4)
            return True
        except OSError:
            return False

    def get_template_names(self) -> List[str]:
        """
        Get list of all template names sorted alphabetically

        Returns:
            List of template names
        """
        return sorted(self._templates.keys())

    def get_template(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a template by name

        Args:
            name: Template name

        Returns:
            Template data dictionary or None if not found
        """
        return self._templates.get(name)

    def save_template(self, name: str, settings: Dict[str, Any]) -> bool:
        """
        Save a new template or overwrite existing one

        Args:
            name: Template name
            settings: Dictionary of settings to save

        Returns:
            True if successful, False otherwise
        """
        # Only save recognized keys
        template_data = {
            key: settings.get(key)
            for key in self.TEMPLATE_KEYS
            if key in settings
        }

        # Add metadata
        template_data["_created"] = self._templates.get(name, {}).get(
            "_created",
            datetime.now().isoformat()
        )
        template_data["_modified"] = datetime.now().isoformat()

        self._templates[name] = template_data
        return self._save()

    def delete_template(self, name: str) -> bool:
        """
        Delete a template by name

        Args:
            name: Template name to delete

        Returns:
            True if successful, False otherwise
        """
        if name in self._templates:
            del self._templates[name]
            return self._save()
        return False

    def rename_template(self, old_name: str, new_name: str) -> bool:
        """
        Rename a template

        Args:
            old_name: Current template name
            new_name: New template name

        Returns:
            True if successful, False otherwise
        """
        if old_name in self._templates and new_name not in self._templates:
            self._templates[new_name] = self._templates.pop(old_name)
            self._templates[new_name]["_modified"] = datetime.now().isoformat()
            return self._save()
        return False

    def template_exists(self, name: str) -> bool:
        """
        Check if a template exists

        Args:
            name: Template name to check

        Returns:
            True if template exists, False otherwise
        """
        return name in self._templates

    def duplicate_template(self, source_name: str, new_name: str) -> bool:
        """
        Duplicate an existing template with a new name

        Args:
            source_name: Name of template to duplicate
            new_name: Name for the new template

        Returns:
            True if successful, False otherwise
        """
        if source_name in self._templates and new_name not in self._templates:
            template_copy = self._templates[source_name].copy()
            template_copy["_created"] = datetime.now().isoformat()
            template_copy["_modified"] = datetime.now().isoformat()
            self._templates[new_name] = template_copy
            return self._save()
        return False
