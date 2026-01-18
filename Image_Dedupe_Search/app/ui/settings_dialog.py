"""Settings dialog for Image Dedupe Search"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSpinBox, QCheckBox, QGroupBox, QFormLayout, QMessageBox,
    QComboBox, QFrame
)
from PySide6.QtCore import Qt, Slot
from typing import Dict, Any, Optional
import torch


class SettingsDialog(QDialog):
    """Advanced settings dialog"""

    def __init__(
        self,
        config: Dict[str, Any],
        parent=None,
        theme=None
    ):
        super().__init__(parent)
        self.config = config
        self.theme = theme
        self._changes_made = False

        self._setup_ui()
        self._load_settings()
        self._apply_theme()

    def _setup_ui(self) -> None:
        """Build the UI"""
        self.setWindowTitle("Settings")
        self.setMinimumWidth(450)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Hardware section
        self._create_hardware_section(layout)

        # Performance section
        self._create_performance_section(layout)

        # Model section
        self._create_model_section(layout)

        # Buttons
        self._create_buttons(layout)

    def _create_hardware_section(self, parent_layout: QVBoxLayout) -> None:
        """Create hardware detection and settings section"""
        group = QGroupBox("Hardware")
        layout = QFormLayout(group)

        # GPU detection info
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            gpu_info = f"{gpu_name} ({gpu_memory:.1f} GB)"
            self.gpu_status_label = QLabel(f"✓ {gpu_info}")
            self.gpu_status_label.setStyleSheet("color: #4CAF50;")
        else:
            self.gpu_status_label = QLabel("✗ No CUDA GPU detected - using CPU")
            self.gpu_status_label.setStyleSheet("color: #FF9800;")

        layout.addRow("GPU Status:", self.gpu_status_label)

        # Use GPU checkbox
        self.use_gpu_checkbox = QCheckBox("Use GPU acceleration")
        self.use_gpu_checkbox.setEnabled(cuda_available)
        self.use_gpu_checkbox.setToolTip(
            "Enable GPU acceleration for faster embedding computation" if cuda_available
            else "No CUDA GPU available - CPU will be used"
        )
        layout.addRow("", self.use_gpu_checkbox)

        # CPU info
        import os
        cpu_count = os.cpu_count() or 4
        self.cpu_info_label = QLabel(f"{cpu_count} logical processors")
        layout.addRow("CPU:", self.cpu_info_label)

        parent_layout.addWidget(group)

    def _create_performance_section(self, parent_layout: QVBoxLayout) -> None:
        """Create performance tuning section"""
        group = QGroupBox("Performance Tuning")
        layout = QFormLayout(group)

        # Batch size
        self.batch_size_spin = QSpinBox()
        self.batch_size_spin.setRange(8, 1024)
        self.batch_size_spin.setSingleStep(8)
        self.batch_size_spin.setToolTip(
            "Number of images to process per GPU batch.\n"
            "Higher = faster but uses more VRAM.\n"
            "Recommended: 64-128 for 4GB VRAM, 256-512 for 8GB+, 512+ for 24GB+"
        )
        layout.addRow("Batch Size:", self.batch_size_spin)

        # Batch size presets
        preset_layout = QHBoxLayout()
        presets = [
            ("Low (64)", 64),
            ("Medium (256)", 256),
            ("High (512)", 512),
        ]
        for label, value in presets:
            btn = QPushButton(label)
            btn.setFixedWidth(90)
            btn.clicked.connect(lambda checked, v=value: self.batch_size_spin.setValue(v))
            preset_layout.addWidget(btn)
        preset_layout.addStretch()
        layout.addRow("Presets:", preset_layout)

        # IO Workers
        self.io_workers_spin = QSpinBox()
        self.io_workers_spin.setRange(1, 32)
        self.io_workers_spin.setToolTip(
            "Number of parallel threads for loading images from disk.\n"
            "Higher = faster loading but more CPU usage.\n"
            "Recommended: 4-8 for HDD, 8-16 for SSD, 12-24 for NVMe"
        )
        layout.addRow("I/O Workers:", self.io_workers_spin)

        # IO Workers presets
        io_preset_layout = QHBoxLayout()
        io_presets = [
            ("HDD (4)", 4),
            ("SSD (8)", 8),
            ("NVMe (16)", 16),
        ]
        for label, value in io_presets:
            btn = QPushButton(label)
            btn.setFixedWidth(90)
            btn.clicked.connect(lambda checked, v=value: self.io_workers_spin.setValue(v))
            io_preset_layout.addWidget(btn)
        io_preset_layout.addStretch()
        layout.addRow("Presets:", io_preset_layout)

        # Thumbnail size
        self.thumbnail_size_spin = QSpinBox()
        self.thumbnail_size_spin.setRange(50, 300)
        self.thumbnail_size_spin.setSingleStep(10)
        self.thumbnail_size_spin.setToolTip("Size of thumbnail images in the grid view")
        layout.addRow("Thumbnail Size:", self.thumbnail_size_spin)

        parent_layout.addWidget(group)

    def _create_model_section(self, parent_layout: QVBoxLayout) -> None:
        """Create model selection section"""
        group = QGroupBox("Model")
        layout = QFormLayout(group)

        # Model selection
        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "clip-ViT-B-32",
            "clip-ViT-B-16",
            "clip-ViT-L-14",
        ])
        self.model_combo.setToolTip(
            "CLIP model to use for image embeddings.\n"
            "ViT-B-32: Fastest, good quality\n"
            "ViT-B-16: Slower, better quality\n"
            "ViT-L-14: Slowest, best quality (requires more VRAM)"
        )
        layout.addRow("CLIP Model:", self.model_combo)

        # Note about model changes
        note_label = QLabel("Note: Changing models will invalidate the embedding cache.")
        note_label.setStyleSheet("color: #888; font-size: 11px;")
        note_label.setWordWrap(True)
        layout.addRow("", note_label)

        parent_layout.addWidget(group)

    def _create_buttons(self, parent_layout: QVBoxLayout) -> None:
        """Create dialog buttons"""
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        parent_layout.addWidget(line)

        button_layout = QHBoxLayout()

        # Auto-detect button
        self.auto_detect_btn = QPushButton("Auto-Detect Best Settings")
        self.auto_detect_btn.setToolTip("Automatically configure settings based on your hardware")
        self.auto_detect_btn.clicked.connect(self._auto_detect_settings)
        button_layout.addWidget(self.auto_detect_btn)

        button_layout.addStretch()

        # Cancel button
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        # Save button
        self.save_btn = QPushButton("Save")
        self.save_btn.setProperty("cssClass", "primary")
        self.save_btn.clicked.connect(self._save_settings)
        button_layout.addWidget(self.save_btn)

        parent_layout.addLayout(button_layout)

    def _load_settings(self) -> None:
        """Load current settings into UI"""
        self.use_gpu_checkbox.setChecked(self.config.get("use_gpu", True))
        self.batch_size_spin.setValue(self.config.get("batch_size", 512))
        self.io_workers_spin.setValue(self.config.get("io_workers", 12))
        self.thumbnail_size_spin.setValue(self.config.get("thumbnail_size", 150))

        model_name = self.config.get("model_name", "clip-ViT-B-32")
        index = self.model_combo.findText(model_name)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)

    def _apply_theme(self) -> None:
        """Apply theme stylesheet"""
        if self.theme:
            self.setStyleSheet(self.theme.get_stylesheet())

    @Slot()
    def _auto_detect_settings(self) -> None:
        """Auto-detect optimal settings based on hardware"""
        import os

        cuda_available = torch.cuda.is_available()
        cpu_count = os.cpu_count() or 4

        if cuda_available:
            # GPU available - configure based on VRAM
            vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)

            if vram_gb >= 20:  # 24GB+ (RTX 3090, 4090, etc.)
                batch_size = 512
                io_workers = min(24, cpu_count)
            elif vram_gb >= 10:  # 12GB+ (RTX 3080, 4080, etc.)
                batch_size = 256
                io_workers = min(16, cpu_count)
            elif vram_gb >= 6:  # 8GB (RTX 3070, etc.)
                batch_size = 128
                io_workers = min(12, cpu_count)
            else:  # 4-6GB
                batch_size = 64
                io_workers = min(8, cpu_count)

            self.use_gpu_checkbox.setChecked(True)
        else:
            # CPU only - conservative settings
            batch_size = 32
            io_workers = min(4, cpu_count)
            self.use_gpu_checkbox.setChecked(False)

        self.batch_size_spin.setValue(batch_size)
        self.io_workers_spin.setValue(io_workers)

        QMessageBox.information(
            self,
            "Auto-Detect Complete",
            f"Settings configured for your hardware:\n\n"
            f"• GPU: {'Enabled' if cuda_available else 'Not available (using CPU)'}\n"
            f"• Batch Size: {batch_size}\n"
            f"• I/O Workers: {io_workers}\n\n"
            f"Click 'Save' to apply these settings."
        )

    @Slot()
    def _save_settings(self) -> None:
        """Save settings to config"""
        self.config["use_gpu"] = self.use_gpu_checkbox.isChecked()
        self.config["batch_size"] = self.batch_size_spin.value()
        self.config["io_workers"] = self.io_workers_spin.value()
        self.config["thumbnail_size"] = self.thumbnail_size_spin.value()
        self.config["model_name"] = self.model_combo.currentText()

        self._changes_made = True
        self.accept()

    def changes_made(self) -> bool:
        """Check if settings were changed"""
        return self._changes_made
