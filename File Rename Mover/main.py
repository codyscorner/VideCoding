"""
File Rename Mover - Main Entry Point

A tool for batch renaming and moving files with sequential numbering.
"""

import tkinter as tk
from pathlib import Path
import sys

from config import ConfigManager
from ui.main_window_v2 import MainWindowV2

# Version number
VERSION = "2.1.7"


def get_script_directory() -> Path:
    """
    Get the directory where the script is located

    Returns:
        Path object pointing to script directory
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return Path(sys.executable).parent
    else:
        # Running as script
        return Path(__file__).parent


def get_resource_path(filename: str) -> Path:
    """
    Get the path to a bundled resource file

    Args:
        filename: Name of the resource file

    Returns:
        Path object pointing to the resource
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable - resources are in _MEIPASS
        return Path(sys._MEIPASS) / filename
    else:
        # Running as script
        return Path(__file__).parent / filename


def set_window_icon(root: tk.Tk) -> None:
    """
    Set the window icon if available

    Args:
        root: Tkinter root window
    """
    icon_path = get_resource_path("app_icon.ico")
    if icon_path.exists():
        try:
            root.iconbitmap(str(icon_path))
        except Exception:
            # Silently continue if icon cannot be set
            pass


def main():
    """Main application entry point"""
    # Get script directory
    script_dir = get_script_directory()

    # Initialize configuration
    config_file = script_dir / "config.json"
    config_manager = ConfigManager(config_file)

    # Create main window
    root = tk.Tk()

    # Set window icon
    set_window_icon(root)

    # Create application
    app = MainWindowV2(root, config_manager, VERSION)

    # Start main loop
    root.mainloop()


if __name__ == "__main__":
    main()
