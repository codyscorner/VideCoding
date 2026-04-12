import sys
import os
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from ui.main_window import MainWindow
from version import VERSION

def main():
    app = QApplication(sys.argv)

    icon_path = Path(__file__).parent.parent / "app_icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    theme_path = os.path.join(os.path.dirname(__file__), "ui", "dark_theme.qss")
    try:
        with open(theme_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        print(f"Warning: stylesheet not found at {theme_path}", file=sys.stderr)
        
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
