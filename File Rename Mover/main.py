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


def set_window_icon(root: tk.Tk, script_dir: Path) -> None:
    """
    Set the window icon if available

    Args:
        root: Tkinter root window
        script_dir: Directory containing the script
    """
    icon_path = script_dir / "app_icon.ico"
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
    set_window_icon(root, script_dir)

    # Create application
    app = MainWindowV2(root, config_manager, VERSION)

    # Start main loop
    root.mainloop()


if __name__ == "__main__":
    main()
