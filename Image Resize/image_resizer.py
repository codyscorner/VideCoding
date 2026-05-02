import sys
import os
import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QComboBox,
    QCheckBox, QProgressBar, QListWidget, QGroupBox, QMessageBox,
    QSpinBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon
from PIL import Image

VERSION = "1.1.0"

def get_settings_file():
    """Get the settings file path based on the executable/script name."""
    if getattr(sys, 'frozen', False):
        # Running as compiled EXE
        exe_path = sys.executable
        exe_dir = os.path.dirname(exe_path)
        exe_name = os.path.splitext(os.path.basename(exe_path))[0]
    else:
        # Running as script
        exe_path = os.path.abspath(__file__)
        exe_dir = os.path.dirname(exe_path)
        exe_name = os.path.splitext(os.path.basename(exe_path))[0]

    return os.path.join(exe_dir, f"{exe_name}_config.json")

SETTINGS_FILE = get_settings_file()

# Standard 16 colors
PADDING_COLORS = {
    "Black": "#000000",
    "White": "#FFFFFF",
    "Red": "#FF0000",
    "Green": "#008000",
    "Blue": "#0000FF",
    "Yellow": "#FFFF00",
    "Cyan": "#00FFFF",
    "Magenta": "#FF00FF",
    "Gray": "#808080",
    "Silver": "#C0C0C0",
    "Maroon": "#800000",
    "Olive": "#808000",
    "Navy": "#000080",
    "Purple": "#800080",
    "Teal": "#008080",
    "Lime": "#00FF00",
}

SUPPORTED_FORMATS = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')

# Resolution presets for image-to-video (I2V) workflows
RESOLUTION_PRESETS = [
    ("Custom", None, None, "Manual width/height entry"),
    ("384x384", 384, 384, "1:1 - Fast drafts"),
    ("448x448", 448, 448, "1:1 - Higher-quality previews"),
    ("512x512", 512, 512, "1:1 - Standard output"),
    ("576x576", 576, 576, "1:1 - High-detail square"),
    ("640x640", 640, 640, "1:1 - Near-max square"),
    ("480x640", 480, 640, "3:4 - Portrait previews"),
    ("540x720", 540, 720, "3:4 - Portrait high-quality"),
    ("360x640", 360, 640, "9:16 - Vertical quick tests"),
    ("512x768", 512, 768, "2:3 - Stylized portraits"),
    ("512x288", 512, 288, "16:9 - Landscape previews"),
    ("768x432", 768, 432, "16:9 - Higher-quality landscape"),
    ("960x540", 960, 540, "16:9 - Near-HD landscape"),
    ("1280x720", 1280, 720, "16:9 - HD output (via upscale)"),
    # ── Desktop wallpapers ────────────────────────────────────────────
    ("1920x1080", 1920, 1080, "16:9 - Full HD wallpaper"),
    ("2560x1440", 2560, 1440, "16:9 - 2K / QHD wallpaper"),
    ("3840x2160", 3840, 2160, "16:9 - 4K UHD wallpaper"),
    ("2560x1080", 2560, 1080, "21:9 - UltraWide FHD wallpaper"),
    ("3440x1440", 3440, 1440, "21:9 - UltraWide QHD wallpaper"),
    ("3840x1600", 3840, 1600, "21:9 - UltraWide 4K wallpaper"),
    ("5120x1440", 5120, 1440, "32:9 - Super UltraWide wallpaper"),
]

STYLESHEET = """
QMainWindow {
    background-color: #1e1e1e;
}
QWidget {
    background-color: #1e1e1e;
    color: #e0e0e0;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 10pt;
}
QGroupBox {
    border: 1px solid #3a3a3a;
    border-radius: 6px;
    margin-top: 8px;
    padding: 10px;
    background-color: #252526;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 15px;
    padding: 0 8px;
    color: #3fb950;
    font-weight: bold;
}
QLineEdit, QSpinBox {
    background-color: #2d2d30;
    border: 1px solid #3a3a3a;
    border-radius: 4px;
    padding: 6px 8px;
    min-height: 20px;
    color: #e0e0e0;
    selection-background-color: #2ea043;
}
QLineEdit:focus, QSpinBox:focus {
    border: 1px solid #3fb950;
}
QPushButton {
    background-color: #238636;
    border: none;
    border-radius: 4px;
    padding: 10px 20px;
    color: white;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #2ea043;
}
QPushButton:pressed {
    background-color: #196c2e;
}
QPushButton:disabled {
    background-color: #3a3a3a;
    color: #6a6a6a;
}
QPushButton#browseBtn {
    background-color: #3a3a3a;
    padding: 8px 15px;
}
QPushButton#browseBtn:hover {
    background-color: #4a4a4a;
}
QPushButton#startBtn {
    background-color: #2ea043;
    padding: 12px 30px;
    font-size: 11pt;
}
QPushButton#startBtn:hover {
    background-color: #3fb950;
}
QPushButton#startBtn:pressed {
    background-color: #238636;
}
QComboBox {
    background-color: #2d2d30;
    border: 1px solid #3a3a3a;
    border-radius: 4px;
    padding: 6px 8px;
    min-height: 20px;
    color: #e0e0e0;
}
QComboBox#colorCombo {
    min-width: 100px;
    min-height: 26px;
    padding: 4px 8px;
}
QComboBox:hover {
    border: 1px solid #3fb950;
}
QComboBox::drop-down {
    border: none;
    padding-right: 10px;
}
QComboBox::down-arrow {
    width: 12px;
    height: 12px;
}
QComboBox QAbstractItemView {
    background-color: #2d2d30;
    border: 1px solid #3a3a3a;
    selection-background-color: #2ea043;
    color: #e0e0e0;
}
QCheckBox {
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 3px;
    border: 1px solid #3a3a3a;
    background-color: #2d2d30;
}
QCheckBox::indicator:checked {
    background-color: #2ea043;
    border-color: #2ea043;
}
QCheckBox::indicator:hover {
    border-color: #3fb950;
}
QProgressBar {
    border: none;
    border-radius: 4px;
    background-color: #2d2d30;
    height: 8px;
}
QProgressBar::text {
    color: transparent;
}
QProgressBar::chunk {
    background-color: #3fb950;
    border-radius: 4px;
}
QListWidget {
    background-color: #2d2d30;
    border: 1px solid #3a3a3a;
    border-radius: 4px;
    padding: 5px;
    color: #e0e0e0;
}
QListWidget::item {
    padding: 4px;
    border-radius: 2px;
}
QListWidget::item:selected {
    background-color: #2ea043;
}
QLabel#colorPreview {
    border: 2px solid #3a3a3a;
    border-radius: 4px;
    min-width: 30px;
    min-height: 30px;
}
"""


def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def resize_with_padding(img, target_size, padding_color_rgb):
    """Resize image preserving aspect ratio and add padding."""
    target_width, target_height = target_size
    original_width, original_height = img.size

    ratio = min(target_width / original_width, target_height / original_height)
    new_width = int(original_width * ratio)
    new_height = int(original_height * ratio)

    resized_img = img.resize((new_width, new_height), Image.LANCZOS)

    if img.mode == 'RGBA':
        new_img = Image.new('RGBA', target_size, padding_color_rgb + (255,))
    else:
        new_img = Image.new('RGB', target_size, padding_color_rgb)

    paste_x = (target_width - new_width) // 2
    paste_y = (target_height - new_height) // 2

    if resized_img.mode == 'RGBA':
        new_img.paste(resized_img, (paste_x, paste_y), resized_img)
    else:
        new_img.paste(resized_img, (paste_x, paste_y))

    return new_img


class ResizeWorker(QThread):
    """Worker thread for resizing images."""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, folder_path, output_folder, target_size, preserve_ratio, use_padding, padding_color):
        super().__init__()
        self.folder_path = folder_path
        self.output_folder = output_folder
        self.target_size = target_size
        self.preserve_ratio = preserve_ratio
        self.use_padding = use_padding
        self.padding_color = padding_color

    def run(self):
        image_files = [f for f in os.listdir(self.folder_path) if f.lower().endswith(SUPPORTED_FORMATS)]

        if not image_files:
            self.status.emit("No images found in the selected folder.")
            self.finished_signal.emit()
            return

        for i, filename in enumerate(image_files):
            try:
                img_path = os.path.join(self.folder_path, filename)
                img = Image.open(img_path)

                if self.preserve_ratio and self.use_padding:
                    img_resized = resize_with_padding(img, self.target_size, self.padding_color)
                elif self.preserve_ratio:
                    img.thumbnail(self.target_size, Image.LANCZOS)
                    img_resized = img
                else:
                    img_resized = img.resize(self.target_size, Image.LANCZOS)

                save_path = os.path.join(self.output_folder, filename)

                if filename.lower().endswith(('.jpg', '.jpeg')):
                    if img_resized.mode == 'RGBA':
                        img_resized = img_resized.convert('RGB')
                    img_resized.save(save_path, quality=95)
                else:
                    img_resized.save(save_path)

                self.status.emit(f"✓ Resized: {filename}")

            except Exception as e:
                self.status.emit(f"✗ Error: {filename} - {e}")

            self.progress.emit(int((i + 1) / len(image_files) * 100))

        self.status.emit("─" * 40)
        self.status.emit("✓ Process Complete!")
        self.finished_signal.emit()


class ImageResizerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Image Resizer v{VERSION}")
        self.setMinimumSize(700, 750)
        self.resize(750, 780)
        icon_path = Path(__file__).parent / "app_icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.worker = None
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # Input folder group
        input_group = QGroupBox("Input Folder")
        input_layout = QHBoxLayout(input_group)
        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText("Select a folder containing images...")
        browse_input_btn = QPushButton("Browse")
        browse_input_btn.setObjectName("browseBtn")
        browse_input_btn.clicked.connect(self.browse_input_folder)
        input_layout.addWidget(self.folder_input)
        input_layout.addWidget(browse_input_btn)
        main_layout.addWidget(input_group)

        # Output folder group
        output_group = QGroupBox("Output Folder")
        output_layout = QHBoxLayout(output_group)
        self.output_input = QLineEdit()
        self.output_input.setPlaceholderText("Leave empty to create 'resized_images' subfolder...")
        browse_output_btn = QPushButton("Browse")
        browse_output_btn.setObjectName("browseBtn")
        browse_output_btn.clicked.connect(self.browse_output_folder)
        output_layout.addWidget(self.output_input)
        output_layout.addWidget(browse_output_btn)
        main_layout.addWidget(output_group)

        # Dimensions group
        dim_group = QGroupBox("Target Dimensions")
        dim_layout = QVBoxLayout(dim_group)

        # Preset dropdown
        preset_layout = QHBoxLayout()
        preset_label = QLabel("Preset:")
        preset_label.setFixedWidth(50)
        preset_layout.addWidget(preset_label)
        self.preset_combo = QComboBox()
        for preset in RESOLUTION_PRESETS:
            name, width, height, desc = preset
            if width is None:
                self.preset_combo.addItem(f"{name} - {desc}")
            else:
                self.preset_combo.addItem(f"{name} ({desc})")
        self.preset_combo.setCurrentIndex(3)  # Default to 512x512
        self.preset_combo.currentIndexChanged.connect(self.on_preset_changed)
        preset_layout.addWidget(self.preset_combo, 1)
        dim_layout.addLayout(preset_layout)

        # Manual width/height
        manual_layout = QHBoxLayout()
        width_label = QLabel("Width:")
        width_label.setFixedWidth(50)
        manual_layout.addWidget(width_label)
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 10000)
        self.width_spin.setValue(512)
        self.width_spin.setFixedWidth(80)
        self.width_spin.valueChanged.connect(self.on_manual_dimension_changed)
        manual_layout.addWidget(self.width_spin)
        manual_layout.addSpacing(30)
        height_label = QLabel("Height:")
        height_label.setFixedWidth(50)
        manual_layout.addWidget(height_label)
        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, 10000)
        self.height_spin.setValue(512)
        self.height_spin.setFixedWidth(80)
        self.height_spin.valueChanged.connect(self.on_manual_dimension_changed)
        manual_layout.addWidget(self.height_spin)
        manual_layout.addStretch()
        dim_layout.addLayout(manual_layout)

        main_layout.addWidget(dim_group)

        # Options group
        options_group = QGroupBox("Resize Options")
        options_layout = QVBoxLayout(options_group)

        self.preserve_ratio_check = QCheckBox("Preserve aspect ratio")
        self.preserve_ratio_check.setChecked(True)
        self.preserve_ratio_check.stateChanged.connect(self.toggle_padding_options)
        options_layout.addWidget(self.preserve_ratio_check)

        self.padding_check = QCheckBox("Add padding to fill canvas")
        self.padding_check.setChecked(True)
        self.padding_check.stateChanged.connect(self.toggle_padding_options)
        options_layout.addWidget(self.padding_check)

        # Color selection
        color_layout = QHBoxLayout()
        color_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        color_label = QLabel("Padding color:")
        color_label.setFixedWidth(95)
        color_layout.addWidget(color_label)
        self.color_combo = QComboBox()
        self.color_combo.setObjectName("colorCombo")
        self.color_combo.setFixedWidth(120)
        self.color_combo.addItems(PADDING_COLORS.keys())
        self.color_combo.currentTextChanged.connect(self.update_color_preview)
        color_layout.addWidget(self.color_combo)

        self.color_preview = QLabel()
        self.color_preview.setObjectName("colorPreview")
        self.color_preview.setFixedSize(28, 28)
        self.update_color_preview()
        color_layout.addWidget(self.color_preview)
        color_layout.addStretch()

        options_layout.addLayout(color_layout)
        main_layout.addWidget(options_group)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        main_layout.addWidget(self.progress_bar)

        # Log/feedback list
        log_group = QGroupBox("Progress Log")
        log_layout = QVBoxLayout(log_group)
        self.log_list = QListWidget()
        self.log_list.setMinimumHeight(160)  # ~8 lines
        self.log_list.setMaximumHeight(160)
        log_layout.addWidget(self.log_list)
        main_layout.addWidget(log_group)

        # Start button
        self.start_btn = QPushButton("Start Resizing")
        self.start_btn.setObjectName("startBtn")
        self.start_btn.clicked.connect(self.start_resize)
        main_layout.addWidget(self.start_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def browse_input_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Input Folder")
        if folder:
            self.folder_input.setText(folder)

    def browse_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_input.setText(folder)

    def on_preset_changed(self, index):
        """Update width/height spinboxes when a preset is selected."""
        if index > 0:  # Not "Custom"
            _, width, height, _ = RESOLUTION_PRESETS[index]
            # Block signals to prevent triggering on_manual_dimension_changed
            self.width_spin.blockSignals(True)
            self.height_spin.blockSignals(True)
            self.width_spin.setValue(width)
            self.height_spin.setValue(height)
            self.width_spin.blockSignals(False)
            self.height_spin.blockSignals(False)

    def on_manual_dimension_changed(self):
        """Switch to Custom preset when user manually changes dimensions."""
        # Check if current values match any preset
        current_width = self.width_spin.value()
        current_height = self.height_spin.value()

        for i, preset in enumerate(RESOLUTION_PRESETS):
            _, width, height, _ = preset
            if width == current_width and height == current_height:
                self.preset_combo.blockSignals(True)
                self.preset_combo.setCurrentIndex(i)
                self.preset_combo.blockSignals(False)
                return

        # No match found, set to Custom
        self.preset_combo.blockSignals(True)
        self.preset_combo.setCurrentIndex(0)
        self.preset_combo.blockSignals(False)

    def toggle_padding_options(self):
        enabled = self.preserve_ratio_check.isChecked() and self.padding_check.isChecked()
        self.color_combo.setEnabled(enabled)
        if enabled:
            self.update_color_preview()
        else:
            self.color_preview.setStyleSheet("background-color: #2d2d30; border: 2px solid #3a3a3a; border-radius: 4px;")

    def update_color_preview(self):
        color = PADDING_COLORS.get(self.color_combo.currentText(), "#000000")
        self.color_preview.setStyleSheet(f"background-color: {color}; border: 2px solid #3a3a3a; border-radius: 4px;")

    def start_resize(self):
        folder_path = self.folder_input.text()
        if not folder_path:
            QMessageBox.warning(self, "Error", "Please select an input folder.")
            return

        if not os.path.isdir(folder_path):
            QMessageBox.warning(self, "Error", "The selected input folder does not exist.")
            return

        output_folder = self.output_input.text()
        if not output_folder:
            output_folder = os.path.join(folder_path, "resized_images")

        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        target_size = (self.width_spin.value(), self.height_spin.value())
        preserve_ratio = self.preserve_ratio_check.isChecked()
        use_padding = self.padding_check.isChecked()
        padding_color = hex_to_rgb(PADDING_COLORS[self.color_combo.currentText()])

        # Clear log and reset progress
        self.log_list.clear()
        self.progress_bar.setValue(0)

        # Log settings
        self.log_list.addItem(f"Output folder: {output_folder}")
        self.log_list.addItem(f"Target size: {target_size[0]}x{target_size[1]}")
        if preserve_ratio and use_padding:
            self.log_list.addItem(f"Mode: Preserve ratio with {self.color_combo.currentText()} padding")
        elif preserve_ratio:
            self.log_list.addItem("Mode: Preserve ratio (fit within bounds)")
        else:
            self.log_list.addItem("Mode: Stretch to fit")
        self.log_list.addItem("─" * 40)

        # Save settings before processing
        self.save_settings()

        # Disable start button during processing
        self.start_btn.setEnabled(False)

        # Start worker thread
        self.worker = ResizeWorker(folder_path, output_folder, target_size, preserve_ratio, use_padding, padding_color)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.status.connect(self.add_log)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def add_log(self, message):
        self.log_list.addItem(message)
        self.log_list.scrollToBottom()

    def on_finished(self):
        self.start_btn.setEnabled(True)

    def save_settings(self):
        """Save current settings to JSON file."""
        settings = {
            "input_folder": self.folder_input.text(),
            "output_folder": self.output_input.text(),
            "preset_index": self.preset_combo.currentIndex(),
            "width": self.width_spin.value(),
            "height": self.height_spin.value(),
            "preserve_ratio": self.preserve_ratio_check.isChecked(),
            "use_padding": self.padding_check.isChecked(),
            "padding_color": self.color_combo.currentText(),
        }
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception:
            pass  # Silently fail if we can't save settings

    def load_settings(self):
        """Load settings from JSON file."""
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    settings = json.load(f)

                self.folder_input.setText(settings.get("input_folder", ""))
                self.output_input.setText(settings.get("output_folder", ""))

                preset_index = settings.get("preset_index", 3)
                self.preset_combo.setCurrentIndex(preset_index)

                self.width_spin.blockSignals(True)
                self.height_spin.blockSignals(True)
                self.width_spin.setValue(settings.get("width", 512))
                self.height_spin.setValue(settings.get("height", 512))
                self.width_spin.blockSignals(False)
                self.height_spin.blockSignals(False)

                self.preserve_ratio_check.setChecked(settings.get("preserve_ratio", True))
                self.padding_check.setChecked(settings.get("use_padding", True))

                color = settings.get("padding_color", "Black")
                index = self.color_combo.findText(color)
                if index >= 0:
                    self.color_combo.setCurrentIndex(index)

                self.toggle_padding_options()
        except Exception:
            pass  # Use defaults if we can't load settings


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    icon_path = Path(__file__).parent / "app_icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    window = ImageResizerApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
