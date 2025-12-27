"""
File Copy Manager - Main Entry Point

A tool for batch copying files with automatic duplicate numbering and folder organization.
"""

import tkinter as tk
from pathlib import Path
import sys

from config import ConfigManager
from ui.main_window import MainWindow

# Version number
VERSION = "1.0.1"


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


def main():
    """Main application entry point"""
    # Get script directory
    script_dir = get_script_directory()

    # Initialize configuration
    config_file = script_dir / "config.json"
    config_manager = ConfigManager(config_file)

    # Create main window
    root = tk.Tk()

    # Create application
    app = MainWindow(root, config_manager, VERSION)

    # Start main loop
    root.mainloop()


if __name__ == "__main__":
    main()
