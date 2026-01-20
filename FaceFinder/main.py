"""
FaceFinder - Main Entry Point

A tool for searching matching faces in image collections using face recognition.
"""

import tkinter as tk
from pathlib import Path
import sys
from multiprocessing import freeze_support

from config import ConfigManager
from ui.main_window import MainWindow

# Version number
VERSION = "1.0.0"


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


def get_config_file() -> Path:
    """
    Get the config file path based on the executable/script name

    Returns:
        Path object pointing to config file
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        exe_name = Path(sys.executable).stem
        exe_dir = Path(sys.executable).parent
    else:
        # Running as script
        exe_name = Path(__file__).stem
        exe_dir = Path(__file__).parent

    return exe_dir / f"{exe_name}_config.json"


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
            pass


def main():
    """Main application entry point"""
    # Get script directory
    script_dir = get_script_directory()

    # Initialize configuration
    config_file = get_config_file()
    config_manager = ConfigManager(config_file)

    # Create main window
    root = tk.Tk()

    # Set window icon
    set_window_icon(root, script_dir)

    # Create application
    app = MainWindow(root, config_manager, VERSION)

    # Start main loop
    root.mainloop()


if __name__ == "__main__":
    freeze_support()  # Required for multiprocessing on Windows
    main()
