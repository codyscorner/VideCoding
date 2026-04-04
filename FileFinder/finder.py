import os
import sys
import string
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QListWidget, QLabel, QMessageBox, QSpinBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

VERSION = "1.0.2"

class SearchThread(QThread):
    file_found = pyqtSignal(str)
    search_finished = pyqtSignal()
    status_update = pyqtSignal(str)

    def __init__(self, search_term, min_size_mb=0):
        super().__init__()
        self.search_term = search_term.lower()
        self.min_size_bytes = min_size_mb * 1024 * 1024
        self.is_running = True

    def run(self):
        drives = self.get_available_drives()
        for drive in drives:
            if not self.is_running:
                break
            self.status_update.emit(f"Scanning {drive}...")
            # We want to search the entire drive, so we use drive+\\ and scan recursively.
            self.scan_directory(f"{drive}\\")
        
        if self.is_running:
            self.status_update.emit("Search Complete.")
        self.search_finished.emit()

    def get_available_drives(self):
        # Includes local and mapped network drives formatted like C:, D:
        return ['%s:' % d for d in string.ascii_uppercase if os.path.exists('%s:' % d)]

    def scan_directory(self, path):
        try:
            for item in os.scandir(path):
                if not self.is_running:
                    return
                try:
                    if item.is_dir(follow_symlinks=False):
                        self.scan_directory(item.path)
                    elif item.is_file(follow_symlinks=False):
                        if self.search_term in item.name.lower():
                            if item.stat().st_size >= self.min_size_bytes:
                                self.file_found.emit(item.path)
                except (PermissionError, OSError):
                    # Ignore folders or files we don't have permission to access
                    continue
        except (PermissionError, OSError):
            pass

    def stop(self):
        self.is_running = False

class FileFinderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"File Finder v{VERSION}")
        self.resize(800, 600)
        self.found_count = 0

        # Main Widget and Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Top Bar
        top_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter file name search criteria...")
        self.search_input.returnPressed.connect(self.toggle_search)
        
        self.min_size_label = QLabel("Min Size (MB):")
        self.min_size_spin = QSpinBox()
        self.min_size_spin.setRange(0, 999999)
        self.min_size_spin.setValue(0)
        
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.toggle_search)
        
        top_layout.addWidget(self.search_input)
        top_layout.addWidget(self.min_size_label)
        top_layout.addWidget(self.min_size_spin)
        top_layout.addWidget(self.search_button)
        main_layout.addLayout(top_layout)

        # Results List
        self.results_list = QListWidget()
        self.results_list.itemClicked.connect(self.copy_to_clipboard)
        main_layout.addWidget(self.results_list)

        # Bottom Status
        bottom_layout = QHBoxLayout()
        self.status_label = QLabel("Ready")
        self.count_label = QLabel("Files found: 0")
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        bottom_layout.addWidget(self.status_label)
        bottom_layout.addWidget(self.count_label, stretch=1)
        main_layout.addLayout(bottom_layout)

        # Styling - Dark Green Theme
        self.setStyleSheet("""
            QWidget {
                background-color: #0f2916;
                color: #e8f5e9;
                font-family: Segoe UI, Arial, sans-serif;
                font-size: 14px;
            }
            QLineEdit, QSpinBox {
                background-color: #1b4324;
                border: 1px solid #2e7d32;
                border-radius: 4px;
                padding: 6px;
                color: #e8f5e9;
            }
            QLineEdit:focus, QSpinBox:focus {
                border: 1px solid #4caf50;
            }
            QPushButton {
                background-color: #2e7d32;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                color: #ffffff;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #388e3c;
            }
            QPushButton:pressed {
                background-color: #1b5e20;
            }
            QListWidget {
                background-color: #14361d;
                border: 1px solid #2e7d32;
                border-radius: 4px;
                outline: none;
            }
            QListWidget::item {
                padding: 6px;
                border-bottom: 1px solid #1b4324;
            }
            QListWidget::item:selected {
                background-color: #2e7d32;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #1b4324;
            }
            QLabel {
                color: #a5d6a7;
                font-size: 12px;
            }
        """)

        self.search_thread = None

    def toggle_search(self):
        if self.search_thread is not None and self.search_thread.isRunning():
            self.search_thread.stop()
            self.search_thread.wait()
            self.search_button.setText("Search")
            self.status_label.setText("Search cancelled.")
        else:
            search_term = self.search_input.text().strip()
            if not search_term:
                QMessageBox.warning(self, "Input Error", "Please enter a search term.")
                return
            
            self.results_list.clear()
            self.found_count = 0
            self.count_label.setText("Files found: 0")
            self.search_button.setText("Stop")
            self.status_label.setText("Initializing search...")
            
            min_size_mb = self.min_size_spin.value()
            
            self.search_thread = SearchThread(search_term, min_size_mb)
            self.search_thread.file_found.connect(self.on_file_found)
            self.search_thread.status_update.connect(self.on_status_update)
            self.search_thread.search_finished.connect(self.on_search_finished)
            self.search_thread.start()

    def on_file_found(self, path):
        self.results_list.addItem(path)
        self.found_count += 1
        self.count_label.setText(f"Files found: {self.found_count}")

    def on_status_update(self, message):
        self.status_label.setText(message)

    def on_search_finished(self):
        self.search_button.setText("Search")

    def copy_to_clipboard(self, item):
        path = item.text()
        QApplication.clipboard().setText(path)
        self.status_label.setText(f"Copied: {path}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = FileFinderApp()
    window.show()
    sys.exit(app.exec())
