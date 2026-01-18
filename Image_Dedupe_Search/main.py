"""
Image Dedupe Search - Main Entry Point

A tool for finding duplicate and similar images using CLIP embeddings.
"""

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from pathlib import Path
import sys

from config import ConfigManager
from app.ui.main_window import MainWindow

# Version number
VERSION = "1.3.0"


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
    Get the config file path

    Returns:
        Path object pointing to config file
    """
    return get_script_directory() / "dedupe_config.json"


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


def main():
    """Main application entry point"""
    # Create Qt application
    app = QApplication(sys.argv)

    # Initialize configuration
    config_file = get_config_file()
    config_manager = ConfigManager(config_file)

    # Create main window
    window = MainWindow(config_manager, VERSION)

    # Set window icon if available
    icon_path = get_resource_path("app_icon.ico")
    if icon_path.exists():
        window.setWindowIcon(QIcon(str(icon_path)))

    # Show window
    window.show()

    # Start event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
