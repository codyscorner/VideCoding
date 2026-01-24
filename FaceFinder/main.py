"""
FaceFinder - Main Entry Point

A tool for searching matching faces in image collections using face recognition.
"""

import tkinter as tk
from pathlib import Path
import sys
from multiprocessing import freeze_support

# Try to import drag and drop support
try:
    from tkinterdnd2 import TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

# Version number
VERSION = "1.1.0"


def close_pyinstaller_splash():
    """Close PyInstaller splash screen if running as frozen exe"""
    try:
        import pyi_splash
        pyi_splash.close()
    except ImportError:
        pass


class SplashScreen:
    """Loading splash screen shown during heavy imports"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("FaceFinder")
        self.root.overrideredirect(True)

        # Window size and centering
        width, height = 300, 100
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")

        # Always on top
        self.root.attributes('-topmost', True)

        # Styling
        self.root.configure(bg='#2b2b2b')

        # Title label
        title = tk.Label(
            self.root,
            text="FaceFinder",
            font=("Segoe UI", 16, "bold"),
            fg='white',
            bg='#2b2b2b'
        )
        title.pack(pady=(15, 5))

        # Status label
        self.status = tk.Label(
            self.root,
            text="Loading face recognition models...",
            font=("Segoe UI", 9),
            fg='#aaaaaa',
            bg='#2b2b2b'
        )
        self.status.pack(pady=5)

        self.root.update()

    def update_status(self, text: str):
        """Update the status message"""
        self.status.config(text=text)
        self.root.update()

    def close(self):
        """Close the splash screen"""
        self.root.destroy()


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
    # Close PyInstaller splash (if running as exe)
    close_pyinstaller_splash()

    # Show loading splash while importing heavy modules
    splash = SplashScreen()

    # Deferred imports (face_recognition models take time to load)
    splash.update_status("Loading face recognition models...")
    from config import ConfigManager
    from ui.main_window import MainWindow

    splash.update_status("Initializing...")

    # Get script directory
    script_dir = get_script_directory()

    # Initialize configuration
    config_file = get_config_file()
    config_manager = ConfigManager(config_file)

    # Close splash before showing main window
    splash.close()

    # Create main window (use TkinterDnD for drag-drop support if available)
    if DND_AVAILABLE:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()

    # Set window icon
    set_window_icon(root, script_dir)

    # Create application
    app = MainWindow(root, config_manager, VERSION)

    # Bring window to front, then allow normal behavior
    root.attributes('-topmost', True)
    root.update()
    root.attributes('-topmost', False)
    root.lift()
    root.focus_force()

    # Start main loop
    root.mainloop()


if __name__ == "__main__":
    freeze_support()  # Required for multiprocessing on Windows
    main()
