#!/usr/bin/env python3
"""
VHS Metadata Parser
A PyQt5 application to parse and display ComfyUI workflow metadata files.
Supports drag-and-drop and file browser import.
"""

import sys
import json
from typing import Dict, List, Any, Optional

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QLineEdit, QTextEdit, QScrollArea,
    QGroupBox, QFormLayout, QFileDialog, QMenuBar, QMenu, QAction,
    QFrame, QSplitter, QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QMessageBox
)
from PyQt5.QtCore import Qt, QMimeData
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QFont, QClipboard


class MetadataParser:
    """Parses ComfyUI workflow metadata and extracts relevant fields."""

    def __init__(self):
        self.raw_data: Dict = {}
        self.prompt_data: Dict = {}
        self.workflow_data: Dict = {}

    def parse_file(self, file_path: str) -> bool:
        """Load and parse a metadata file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.raw_data = json.load(f)

            # Parse the nested prompt JSON string
            if 'prompt' in self.raw_data:
                prompt_str = self.raw_data['prompt']
                if isinstance(prompt_str, str):
                    self.prompt_data = json.loads(prompt_str)
                else:
                    self.prompt_data = prompt_str

            # Get workflow data
            if 'workflow' in self.raw_data:
                self.workflow_data = self.raw_data['workflow']

            return True
        except Exception as e:
            print(f"Error parsing file: {e}")
            return False

    def get_nodes_by_type(self, class_type: str) -> List[Dict]:
        """Get all nodes of a specific class type."""
        nodes = []
        for node_id, node_data in self.prompt_data.items():
            if node_data.get('class_type') == class_type:
                node_data['_node_id'] = node_id
                nodes.append(node_data)
        return nodes

    def get_positive_prompts(self) -> List[str]:
        """Extract positive prompt texts."""
        prompts = []
        for node in self.get_nodes_by_type('CLIPTextEncode'):
            meta = node.get('_meta', {})
            title = meta.get('title', '')
            if 'Positive' in title or 'positive' in title.lower():
                text = node.get('inputs', {}).get('text', '')
                if text:
                    prompts.append(text)
        # If no title-based match, get all non-negative prompts
        if not prompts:
            for node in self.get_nodes_by_type('CLIPTextEncode'):
                meta = node.get('_meta', {})
                title = meta.get('title', '')
                if 'Negative' not in title and 'negative' not in title.lower():
                    text = node.get('inputs', {}).get('text', '')
                    if text:
                        prompts.append(text)
        return prompts

    def get_negative_prompts(self) -> List[str]:
        """Extract negative prompt texts."""
        prompts = []
        for node in self.get_nodes_by_type('CLIPTextEncode'):
            meta = node.get('_meta', {})
            title = meta.get('title', '')
            if 'Negative' in title or 'negative' in title.lower():
                text = node.get('inputs', {}).get('text', '')
                if text:
                    prompts.append(text)
        return prompts

    def get_video_settings(self) -> Dict:
        """Extract video-related settings."""
        settings = {}

        # From WanImageToVideo
        for node in self.get_nodes_by_type('WanImageToVideo'):
            inputs = node.get('inputs', {})
            settings['width'] = inputs.get('width', 'N/A')
            settings['height'] = inputs.get('height', 'N/A')
            settings['length'] = inputs.get('length', 'N/A')
            settings['batch_size'] = inputs.get('batch_size', 'N/A')

        # From VHS_VideoCombine
        for node in self.get_nodes_by_type('VHS_VideoCombine'):
            inputs = node.get('inputs', {})
            settings['frame_rate'] = inputs.get('frame_rate', 'N/A')
            settings['filename_prefix'] = inputs.get('filename_prefix', 'N/A')
            settings['format'] = inputs.get('format', 'N/A')
            settings['crf'] = inputs.get('crf', 'N/A')
            settings['pix_fmt'] = inputs.get('pix_fmt', 'N/A')
            settings['loop_count'] = inputs.get('loop_count', 'N/A')

        # From ImageResizeKJv2
        for node in self.get_nodes_by_type('ImageResizeKJv2'):
            inputs = node.get('inputs', {})
            if 'width' not in settings or settings['width'] == 'N/A':
                settings['width'] = inputs.get('width', 'N/A')
            if 'height' not in settings or settings['height'] == 'N/A':
                settings['height'] = inputs.get('height', 'N/A')
            settings['upscale_method'] = inputs.get('upscale_method', 'N/A')
            settings['keep_proportion'] = inputs.get('keep_proportion', 'N/A')

        return settings

    def get_models(self) -> Dict[str, List[Dict]]:
        """Extract all model information."""
        models = {
            'clip': [],
            'vae': [],
            'unet': [],
            'lora': []
        }

        # CLIP models
        for node in self.get_nodes_by_type('CLIPLoader'):
            inputs = node.get('inputs', {})
            models['clip'].append({
                'name': inputs.get('clip_name', 'N/A'),
                'type': inputs.get('type', 'N/A'),
                'device': inputs.get('device', 'N/A')
            })

        # VAE models
        for node in self.get_nodes_by_type('VAELoader'):
            inputs = node.get('inputs', {})
            models['vae'].append({
                'name': inputs.get('vae_name', 'N/A')
            })

        # UNET/Diffusion models
        for node in self.get_nodes_by_type('UNETLoader'):
            inputs = node.get('inputs', {})
            models['unet'].append({
                'name': inputs.get('unet_name', 'N/A'),
                'weight_dtype': inputs.get('weight_dtype', 'N/A')
            })

        # LoRA models
        for node in self.get_nodes_by_type('LoraLoaderModelOnly'):
            inputs = node.get('inputs', {})
            models['lora'].append({
                'name': inputs.get('lora_name', 'N/A'),
                'strength': inputs.get('strength_model', 'N/A')
            })

        return models

    def get_sampler_settings(self) -> List[Dict]:
        """Extract sampler settings from KSamplerAdvanced nodes."""
        samplers = []
        for node in self.get_nodes_by_type('KSamplerAdvanced'):
            inputs = node.get('inputs', {})
            meta = node.get('_meta', {})
            samplers.append({
                'title': meta.get('title', 'KSampler'),
                'steps': inputs.get('steps', 'N/A'),
                'cfg': inputs.get('cfg', 'N/A'),
                'sampler_name': inputs.get('sampler_name', 'N/A'),
                'scheduler': inputs.get('scheduler', 'N/A'),
                'noise_seed': inputs.get('noise_seed', 'N/A'),
                'add_noise': inputs.get('add_noise', 'N/A'),
                'start_at_step': inputs.get('start_at_step', 'N/A'),
                'end_at_step': inputs.get('end_at_step', 'N/A'),
                'return_with_leftover_noise': inputs.get('return_with_leftover_noise', 'N/A')
            })
        return samplers

    def get_input_images(self) -> List[str]:
        """Extract input image filenames."""
        images = []
        for node in self.get_nodes_by_type('LoadImage'):
            inputs = node.get('inputs', {})
            image = inputs.get('image', '')
            if image:
                images.append(image)
        return images

    def get_model_sampling_settings(self) -> List[Dict]:
        """Extract ModelSamplingSD3 settings."""
        settings = []
        for node in self.get_nodes_by_type('ModelSamplingSD3'):
            inputs = node.get('inputs', {})
            meta = node.get('_meta', {})
            settings.append({
                'title': meta.get('title', 'ModelSamplingSD3'),
                'shift': inputs.get('shift', 'N/A')
            })
        return settings


class DropZone(QLabel):
    """A label widget that accepts drag-and-drop files."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setText("Drag and drop a metadata file here\nor use File > Open")
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 10px;
                padding: 30px;
                background-color: #f5f5f5;
                color: #666;
                font-size: 14px;
            }
            QLabel:hover {
                border-color: #666;
                background-color: #eee;
            }
        """)
        self.setMinimumHeight(100)
        self.file_dropped_callback = None

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                QLabel {
                    border: 2px dashed #4CAF50;
                    border-radius: 10px;
                    padding: 30px;
                    background-color: #e8f5e9;
                    color: #2e7d32;
                    font-size: 14px;
                }
            """)

    def dragLeaveEvent(self, event):
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 10px;
                padding: 30px;
                background-color: #f5f5f5;
                color: #666;
                font-size: 14px;
            }
            QLabel:hover {
                border-color: #666;
                background-color: #eee;
            }
        """)

    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 10px;
                padding: 30px;
                background-color: #f5f5f5;
                color: #666;
                font-size: 14px;
            }
            QLabel:hover {
                border-color: #666;
                background-color: #eee;
            }
        """)

        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if self.file_dropped_callback:
                self.file_dropped_callback(file_path)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.parser = MetadataParser()
        self.setup_ui()

    def setup_ui(self):
        """Set up the user interface."""
        self.setWindowTitle("VHS Metadata Parser")
        self.setMinimumSize(900, 700)

        # Create menu bar
        self.create_menu_bar()

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Drop zone
        self.drop_zone = DropZone()
        self.drop_zone.file_dropped_callback = self.load_file
        main_layout.addWidget(self.drop_zone)

        # File path display
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("Loaded File:"))
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setReadOnly(True)
        self.file_path_edit.setPlaceholderText("No file loaded")
        file_layout.addWidget(self.file_path_edit)
        main_layout.addLayout(file_layout)

        # Tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget, 1)

        # Create tabs
        self.create_video_settings_tab()
        self.create_prompts_tab()
        self.create_models_tab()
        self.create_sampler_tab()
        self.create_workflow_tab()
        self.create_raw_json_tab()

    def create_menu_bar(self):
        """Create the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        open_action = QAction("Open...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file_dialog)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def create_video_settings_tab(self):
        """Create the Video Settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Video dimensions group
        dims_group = QGroupBox("Video Dimensions")
        dims_layout = QFormLayout(dims_group)

        self.width_edit = QLineEdit()
        self.width_edit.setReadOnly(True)
        dims_layout.addRow("Width:", self.width_edit)

        self.height_edit = QLineEdit()
        self.height_edit.setReadOnly(True)
        dims_layout.addRow("Height:", self.height_edit)

        self.length_edit = QLineEdit()
        self.length_edit.setReadOnly(True)
        dims_layout.addRow("Frames/Length:", self.length_edit)

        layout.addWidget(dims_group)

        # Output settings group
        output_group = QGroupBox("Output Settings")
        output_layout = QFormLayout(output_group)

        self.frame_rate_edit = QLineEdit()
        self.frame_rate_edit.setReadOnly(True)
        output_layout.addRow("Frame Rate:", self.frame_rate_edit)

        self.filename_prefix_edit = QLineEdit()
        self.filename_prefix_edit.setReadOnly(True)
        output_layout.addRow("Filename Prefix:", self.filename_prefix_edit)

        self.format_edit = QLineEdit()
        self.format_edit.setReadOnly(True)
        output_layout.addRow("Format:", self.format_edit)

        self.crf_edit = QLineEdit()
        self.crf_edit.setReadOnly(True)
        output_layout.addRow("CRF:", self.crf_edit)

        self.pix_fmt_edit = QLineEdit()
        self.pix_fmt_edit.setReadOnly(True)
        output_layout.addRow("Pixel Format:", self.pix_fmt_edit)

        layout.addWidget(output_group)

        # Input image group
        input_group = QGroupBox("Input Images")
        input_layout = QVBoxLayout(input_group)

        self.input_images_edit = QTextEdit()
        self.input_images_edit.setReadOnly(True)
        self.input_images_edit.setMaximumHeight(80)
        input_layout.addWidget(self.input_images_edit)

        layout.addWidget(input_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, "Video Settings")

    def create_prompts_tab(self):
        """Create the Prompts tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Positive prompts
        pos_group = QGroupBox("Positive Prompts")
        pos_layout = QVBoxLayout(pos_group)

        self.positive_prompts_edit = QTextEdit()
        self.positive_prompts_edit.setReadOnly(True)
        pos_layout.addWidget(self.positive_prompts_edit)

        layout.addWidget(pos_group)

        # Negative prompts
        neg_group = QGroupBox("Negative Prompts")
        neg_layout = QVBoxLayout(neg_group)

        self.negative_prompts_edit = QTextEdit()
        self.negative_prompts_edit.setReadOnly(True)
        neg_layout.addWidget(self.negative_prompts_edit)

        layout.addWidget(neg_group)

        self.tab_widget.addTab(tab, "Prompts")

    def create_models_tab(self):
        """Create the Models tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # CLIP models
        clip_group = QGroupBox("CLIP Models")
        clip_layout = QVBoxLayout(clip_group)
        self.clip_table = self.create_model_table(['Name', 'Type', 'Device'])
        clip_layout.addWidget(self.clip_table)
        layout.addWidget(clip_group)

        # VAE models
        vae_group = QGroupBox("VAE Models")
        vae_layout = QVBoxLayout(vae_group)
        self.vae_table = self.create_model_table(['Name'])
        vae_layout.addWidget(self.vae_table)
        layout.addWidget(vae_group)

        # UNET models
        unet_group = QGroupBox("Diffusion Models (UNET)")
        unet_layout = QVBoxLayout(unet_group)
        self.unet_table = self.create_model_table(['Name', 'Weight Dtype'])
        unet_layout.addWidget(self.unet_table)
        layout.addWidget(unet_group)

        # LoRA models
        lora_group = QGroupBox("LoRA Models")
        lora_layout = QVBoxLayout(lora_group)
        self.lora_table = self.create_model_table(['Name', 'Strength'])
        lora_layout.addWidget(self.lora_table)
        layout.addWidget(lora_group)

        self.tab_widget.addTab(tab, "Models")

    def create_model_table(self, headers: List[str]) -> QTableWidget:
        """Create a table widget for displaying models."""
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        return table

    def create_sampler_tab(self):
        """Create the Sampler Settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Sampler table
        sampler_group = QGroupBox("KSampler Settings")
        sampler_layout = QVBoxLayout(sampler_group)

        self.sampler_table = QTableWidget()
        self.sampler_table.setColumnCount(9)
        self.sampler_table.setHorizontalHeaderLabels([
            'Title', 'Steps', 'CFG', 'Sampler', 'Scheduler',
            'Seed', 'Add Noise', 'Start Step', 'End Step'
        ])
        self.sampler_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.sampler_table.setAlternatingRowColors(True)
        self.sampler_table.setEditTriggers(QTableWidget.NoEditTriggers)
        sampler_layout.addWidget(self.sampler_table)

        layout.addWidget(sampler_group)

        # Model sampling settings
        model_sampling_group = QGroupBox("Model Sampling Settings (Shift)")
        model_sampling_layout = QVBoxLayout(model_sampling_group)

        self.model_sampling_table = QTableWidget()
        self.model_sampling_table.setColumnCount(2)
        self.model_sampling_table.setHorizontalHeaderLabels(['Title', 'Shift'])
        self.model_sampling_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.model_sampling_table.setAlternatingRowColors(True)
        self.model_sampling_table.setEditTriggers(QTableWidget.NoEditTriggers)
        model_sampling_layout.addWidget(self.model_sampling_table)

        layout.addWidget(model_sampling_group)

        self.tab_widget.addTab(tab, "Sampler")

    def create_workflow_tab(self):
        """Create the Workflow JSON tab for ComfyUI import."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Info label
        info_label = QLabel("ComfyUI Workflow JSON - Copy or save this to import into ComfyUI")
        info_label.setStyleSheet("font-weight: bold; color: #2196F3; padding: 5px;")
        layout.addWidget(info_label)

        # Button row
        button_layout = QHBoxLayout()

        self.copy_workflow_btn = QPushButton("Copy to Clipboard")
        self.copy_workflow_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        self.copy_workflow_btn.clicked.connect(self.copy_workflow_to_clipboard)
        button_layout.addWidget(self.copy_workflow_btn)

        self.save_workflow_btn = QPushButton("Save Workflow...")
        self.save_workflow_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)
        self.save_workflow_btn.clicked.connect(self.save_workflow_to_file)
        button_layout.addWidget(self.save_workflow_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        # Workflow JSON text area
        self.workflow_json_edit = QTextEdit()
        self.workflow_json_edit.setReadOnly(True)
        self.workflow_json_edit.setFont(QFont("Consolas", 10))
        self.workflow_json_edit.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.workflow_json_edit)

        self.tab_widget.addTab(tab, "Workflow")

    def copy_workflow_to_clipboard(self):
        """Copy the workflow JSON to clipboard."""
        workflow_text = self.workflow_json_edit.toPlainText()
        if workflow_text and workflow_text != "No workflow data available":
            clipboard = QApplication.clipboard()
            clipboard.setText(workflow_text)
            # Show feedback
            original_text = self.copy_workflow_btn.text()
            self.copy_workflow_btn.setText("Copied!")
            self.copy_workflow_btn.setStyleSheet("""
                QPushButton {
                    background-color: #8BC34A;
                    color: white;
                    padding: 8px 16px;
                    border: none;
                    border-radius: 4px;
                    font-weight: bold;
                }
            """)
            # Reset button after 2 seconds
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(2000, lambda: self.reset_copy_button(original_text))
        else:
            QMessageBox.warning(self, "No Data", "No workflow data to copy. Please load a metadata file first.")

    def reset_copy_button(self, original_text):
        """Reset the copy button to its original state."""
        self.copy_workflow_btn.setText(original_text)
        self.copy_workflow_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)

    def save_workflow_to_file(self):
        """Save the workflow JSON to a file."""
        workflow_text = self.workflow_json_edit.toPlainText()
        if not workflow_text or workflow_text == "No workflow data available":
            QMessageBox.warning(self, "No Data", "No workflow data to save. Please load a metadata file first.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Workflow JSON",
            "workflow.json",
            "JSON Files (*.json);;All Files (*.*)"
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(workflow_text)
                QMessageBox.information(self, "Saved", f"Workflow saved to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save workflow:\n{str(e)}")

    def create_raw_json_tab(self):
        """Create the Raw JSON tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.raw_json_edit = QTextEdit()
        self.raw_json_edit.setReadOnly(True)
        self.raw_json_edit.setFont(QFont("Consolas", 10))
        layout.addWidget(self.raw_json_edit)

        self.tab_widget.addTab(tab, "Raw JSON")

    def open_file_dialog(self):
        """Open a file dialog to select a metadata file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Metadata File",
            "",
            "Text Files (*.txt);;JSON Files (*.json);;All Files (*.*)"
        )
        if file_path:
            self.load_file(file_path)

    def load_file(self, file_path: str):
        """Load and parse a metadata file."""
        if self.parser.parse_file(file_path):
            self.file_path_edit.setText(file_path)
            self.drop_zone.setText(f"File loaded: {file_path.split('/')[-1]}")
            self.populate_all_fields()
        else:
            self.file_path_edit.setText("Error loading file")
            self.drop_zone.setText("Error loading file. Please try again.")

    def populate_all_fields(self):
        """Populate all UI fields with parsed data."""
        self.populate_video_settings()
        self.populate_prompts()
        self.populate_models()
        self.populate_sampler_settings()
        self.populate_workflow()
        self.populate_raw_json()

    def populate_video_settings(self):
        """Populate video settings fields."""
        settings = self.parser.get_video_settings()

        self.width_edit.setText(str(settings.get('width', 'N/A')))
        self.height_edit.setText(str(settings.get('height', 'N/A')))
        self.length_edit.setText(str(settings.get('length', 'N/A')))
        self.frame_rate_edit.setText(str(settings.get('frame_rate', 'N/A')))
        self.filename_prefix_edit.setText(str(settings.get('filename_prefix', 'N/A')))
        self.format_edit.setText(str(settings.get('format', 'N/A')))
        self.crf_edit.setText(str(settings.get('crf', 'N/A')))
        self.pix_fmt_edit.setText(str(settings.get('pix_fmt', 'N/A')))

        # Input images
        images = self.parser.get_input_images()
        self.input_images_edit.setText('\n'.join(images) if images else 'No input images')

    def populate_prompts(self):
        """Populate prompt fields."""
        positive = self.parser.get_positive_prompts()
        negative = self.parser.get_negative_prompts()

        self.positive_prompts_edit.setText('\n\n---\n\n'.join(positive) if positive else 'No positive prompts found')
        self.negative_prompts_edit.setText('\n\n---\n\n'.join(negative) if negative else 'No negative prompts found')

    def populate_models(self):
        """Populate model tables."""
        models = self.parser.get_models()

        # CLIP models
        self.clip_table.setRowCount(len(models['clip']))
        for i, model in enumerate(models['clip']):
            self.clip_table.setItem(i, 0, QTableWidgetItem(str(model['name'])))
            self.clip_table.setItem(i, 1, QTableWidgetItem(str(model['type'])))
            self.clip_table.setItem(i, 2, QTableWidgetItem(str(model['device'])))

        # VAE models
        self.vae_table.setRowCount(len(models['vae']))
        for i, model in enumerate(models['vae']):
            self.vae_table.setItem(i, 0, QTableWidgetItem(str(model['name'])))

        # UNET models
        self.unet_table.setRowCount(len(models['unet']))
        for i, model in enumerate(models['unet']):
            self.unet_table.setItem(i, 0, QTableWidgetItem(str(model['name'])))
            self.unet_table.setItem(i, 1, QTableWidgetItem(str(model['weight_dtype'])))

        # LoRA models
        self.lora_table.setRowCount(len(models['lora']))
        for i, model in enumerate(models['lora']):
            self.lora_table.setItem(i, 0, QTableWidgetItem(str(model['name'])))
            self.lora_table.setItem(i, 1, QTableWidgetItem(str(model['strength'])))

    def populate_sampler_settings(self):
        """Populate sampler settings table."""
        samplers = self.parser.get_sampler_settings()

        self.sampler_table.setRowCount(len(samplers))
        for i, sampler in enumerate(samplers):
            self.sampler_table.setItem(i, 0, QTableWidgetItem(str(sampler['title'])))
            self.sampler_table.setItem(i, 1, QTableWidgetItem(str(sampler['steps'])))
            self.sampler_table.setItem(i, 2, QTableWidgetItem(str(sampler['cfg'])))
            self.sampler_table.setItem(i, 3, QTableWidgetItem(str(sampler['sampler_name'])))
            self.sampler_table.setItem(i, 4, QTableWidgetItem(str(sampler['scheduler'])))
            self.sampler_table.setItem(i, 5, QTableWidgetItem(str(sampler['noise_seed'])))
            self.sampler_table.setItem(i, 6, QTableWidgetItem(str(sampler['add_noise'])))
            self.sampler_table.setItem(i, 7, QTableWidgetItem(str(sampler['start_at_step'])))
            self.sampler_table.setItem(i, 8, QTableWidgetItem(str(sampler['end_at_step'])))

        # Model sampling settings
        model_sampling = self.parser.get_model_sampling_settings()
        self.model_sampling_table.setRowCount(len(model_sampling))
        for i, setting in enumerate(model_sampling):
            self.model_sampling_table.setItem(i, 0, QTableWidgetItem(str(setting['title'])))
            self.model_sampling_table.setItem(i, 1, QTableWidgetItem(str(setting['shift'])))

    def populate_workflow(self):
        """Populate workflow JSON view."""
        try:
            if self.parser.workflow_data:
                formatted_workflow = json.dumps(self.parser.workflow_data, indent=2, ensure_ascii=False)
                self.workflow_json_edit.setText(formatted_workflow)
            else:
                self.workflow_json_edit.setText("No workflow data available")
        except Exception as e:
            self.workflow_json_edit.setText(f"Error formatting workflow JSON: {e}")

    def populate_raw_json(self):
        """Populate raw JSON view."""
        try:
            formatted_json = json.dumps(self.parser.raw_data, indent=2, ensure_ascii=False)
            self.raw_json_edit.setText(formatted_json)
        except Exception as e:
            self.raw_json_edit.setText(f"Error formatting JSON: {e}")


def main():
    app = QApplication(sys.argv)

    # Set application style
    app.setStyle('Fusion')

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
