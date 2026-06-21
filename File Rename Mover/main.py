"""
File Rename Mover - Main Entry Point

A tool for batch renaming and moving files with sequential numbering.
"""

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from pathlib import Path
import sys

from config import ConfigManager
from templates import TemplateManager
from ui.main_window_qt import MainWindowQt

# Version number
VERSION = "3.3.0"


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
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent
    else:
        exe_dir = Path(__file__).parent

    return exe_dir / "Filemove_config.json"


def get_templates_file() -> Path:
    """
    Get the templates file path

    Returns:
        Path object pointing to templates file
    """
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent
    else:
        exe_dir = Path(__file__).parent

    return exe_dir / "Filemove_templates.json"


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

    # Initialize templates
    templates_file = get_templates_file()
    template_manager = TemplateManager(templates_file)

    # Set app-level icon
    icon_path = get_resource_path("app_icon.ico")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Create main window
    window = MainWindowQt(config_manager, VERSION, template_manager)

    # Set window icon if available
    if icon_path.exists():
        window.setWindowIcon(QIcon(str(icon_path)))

    # Show window
    window.show()

    # Start event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
