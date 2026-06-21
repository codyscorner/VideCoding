#!/usr/bin/env python3
"""
VHS Metadata Parser
A PyQt6 application to parse and display ComfyUI workflow metadata files.
Supports drag-and-drop and file browser import.
Version: 1.1.0
"""

import csv
import io
import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QLineEdit, QTextEdit, QScrollArea,
    QGroupBox, QFormLayout, QFileDialog, QMenu,
    QFrame, QSplitter, QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QFont, QIcon, QAction


# Dark blue-green color scheme
COLORS = {
    'bg_dark':      '#0d1b1e',
    'bg_medium':    '#162528',
    'bg_light':     '#1f3336',
    'fg_primary':   '#e0f2f1',
    'fg_secondary': '#80cbc4',
    'fg_dim':       '#4a7c7a',
    'accent':       '#00838f',
    'accent_hover': '#00acc1',
    'accent_dark':  '#005662',
    'border':       '#2a4f52',
    'success':      '#80cbc4',
    'error':        '#ef9a9a',
    'table_alt':    '#182d30',
}

STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {COLORS['bg_dark']};
    color: {COLORS['fg_primary']};
    font-family: "Segoe UI";
    font-size: 10pt;
}}
QMenuBar {{
    background-color: {COLORS['bg_medium']};
    color: {COLORS['fg_primary']};
    border-bottom: 1px solid {COLORS['border']};
}}
QMenuBar::item:selected {{
    background-color: {COLORS['accent']};
}}
QMenu {{
    background-color: {COLORS['bg_medium']};
    color: {COLORS['fg_primary']};
    border: 1px solid {COLORS['border']};
}}
QMenu::item:selected {{
    background-color: {COLORS['accent']};
}}
QLabel {{
    background-color: transparent;
    color: {COLORS['fg_primary']};
}}
QLabel#drop_zone {{
    background-color: {COLORS['bg_medium']};
    color: {COLORS['fg_secondary']};
    border: 2px dashed {COLORS['accent']};
    border-radius: 8px;
    font-style: italic;
    padding: 20px;
}}
QLabel#subtitle {{
    color: {COLORS['fg_secondary']};
    font-size: 9pt;
}}
QGroupBox {{
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    margin-top: 8px;
    padding: 8px;
    color: {COLORS['accent_hover']};
    font-weight: bold;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
}}
QLineEdit {{
    background-color: {COLORS['bg_light']};
    color: {COLORS['fg_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 3px;
    padding: 5px;
}}
QLineEdit:focus {{
    border: 1px solid {COLORS['accent']};
}}
QTextEdit {{
    background-color: {COLORS['bg_light']};
    color: {COLORS['fg_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 3px;
    padding: 4px;
    font-family: Consolas;
    font-size: 10pt;
}}
QTabWidget::pane {{
    border: 1px solid {COLORS['border']};
    background-color: {COLORS['bg_dark']};
}}
QTabBar::tab {{
    background-color: {COLORS['bg_medium']};
    color: {COLORS['fg_secondary']};
    padding: 6px 16px;
    border: 1px solid {COLORS['border']};
    border-bottom: none;
}}
QTabBar::tab:selected {{
    background-color: {COLORS['accent']};
    color: white;
    font-weight: bold;
}}
QTabBar::tab:hover:!selected {{
    background-color: {COLORS['bg_light']};
    color: {COLORS['fg_primary']};
}}
QPushButton {{
    background-color: {COLORS['accent']};
    color: white;
    font-weight: bold;
    border: none;
    border-radius: 4px;
    padding: 8px 18px;
    font-size: 10pt;
}}
QPushButton:hover {{
    background-color: {COLORS['accent_hover']};
}}
QPushButton:disabled {{
    background-color: {COLORS['bg_light']};
    color: {COLORS['fg_dim']};
}}
QTableWidget {{
    background-color: {COLORS['bg_medium']};
    color: {COLORS['fg_primary']};
    border: 1px solid {COLORS['border']};
    gridline-color: {COLORS['border']};
    alternate-background-color: {COLORS['table_alt']};
}}
QTableWidget::item:selected {{
    background-color: {COLORS['accent']};
    color: white;
}}
QHeaderView::section {{
    background-color: {COLORS['bg_light']};
    color: {COLORS['fg_secondary']};
    padding: 5px;
    border: 1px solid {COLORS['border']};
    font-weight: bold;
}}
QScrollBar:vertical {{
    background-color: {COLORS['bg_dark']};
    width: 12px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background-color: {COLORS['border']};
    border-radius: 6px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    background-color: {COLORS['bg_dark']};
    height: 12px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background-color: {COLORS['border']};
    border-radius: 6px;
    min-width: 20px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}
"""


class MetadataParser:
    """Parses ComfyUI workflow metadata and extracts relevant fields."""

    def __init__(self):
        self.raw_data: Dict = {}
        self.prompt_data: Dict = {}
        self.workflow_data: Dict = {}

    def parse_file(self, file_path: str) -> bool:
        try:
            file_lower = file_path.lower()
            if file_lower.endswith('.mp4'):
                self.raw_data = self._extract_metadata_from_mp4(file_path)
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.raw_data = json.load(f)

            if 'prompt' in self.raw_data:
                prompt_str = self.raw_data['prompt']
                if isinstance(prompt_str, str):
                    self.prompt_data = json.loads(prompt_str)
                else:
                    self.prompt_data = prompt_str

            if 'workflow' in self.raw_data:
                self.workflow_data = self.raw_data['workflow']

            return True
        except Exception as e:
            print(f"Error parsing file: {e}")
            return False

    def _extract_metadata_from_mp4(self, file_path: str) -> Dict:
        with open(file_path, 'rb') as f:
            data = f.read()
        idx = data.find(b'{"prompt"')
        if idx == -1:
            raise ValueError("No ComfyUI metadata found in MP4 file")
        json_bytes = bytearray()
        brace_count = 0
        started = False
        for i in range(idx, len(data)):
            byte = data[i]
            if byte < 128:
                char = chr(byte)
                if char == '{':
                    brace_count += 1
                    started = True
                elif char == '}':
                    brace_count -= 1
                if started:
                    json_bytes.append(byte)
                if started and brace_count == 0:
                    break
        return json.loads(json_bytes.decode('utf-8'))

    def get_nodes_by_type(self, class_type: str) -> List[Dict]:
        nodes = []
        for node_id, node_data in self.prompt_data.items():
            if node_data.get('class_type') == class_type:
                node_data['_node_id'] = node_id
                nodes.append(node_data)
        return nodes

    def get_positive_prompts(self) -> List[str]:
        prompts = []
        for node in self.get_nodes_by_type('CLIPTextEncode'):
            meta = node.get('_meta', {})
            title = meta.get('title', '')
            if 'Positive' in title or 'positive' in title.lower():
                text = node.get('inputs', {}).get('text', '')
                if text:
                    prompts.append(text)
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
        settings = {}
        for node in self.get_nodes_by_type('WanImageToVideo'):
            inputs = node.get('inputs', {})
            settings['width'] = inputs.get('width', 'N/A')
            settings['height'] = inputs.get('height', 'N/A')
            settings['length'] = inputs.get('length', 'N/A')
            settings['batch_size'] = inputs.get('batch_size', 'N/A')
        for node in self.get_nodes_by_type('VHS_VideoCombine'):
            inputs = node.get('inputs', {})
            settings['frame_rate'] = inputs.get('frame_rate', 'N/A')
            settings['filename_prefix'] = inputs.get('filename_prefix', 'N/A')
            settings['format'] = inputs.get('format', 'N/A')
            settings['crf'] = inputs.get('crf', 'N/A')
            settings['pix_fmt'] = inputs.get('pix_fmt', 'N/A')
            settings['loop_count'] = inputs.get('loop_count', 'N/A')
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
        models = {'clip': [], 'vae': [], 'unet': [], 'lora': []}
        for node in self.get_nodes_by_type('CLIPLoader'):
            inputs = node.get('inputs', {})
            models['clip'].append({'name': inputs.get('clip_name', 'N/A'), 'type': inputs.get('type', 'N/A'), 'device': inputs.get('device', 'N/A')})
        for node in self.get_nodes_by_type('VAELoader'):
            inputs = node.get('inputs', {})
            models['vae'].append({'name': inputs.get('vae_name', 'N/A')})
        for node in self.get_nodes_by_type('UNETLoader'):
            inputs = node.get('inputs', {})
            models['unet'].append({'name': inputs.get('unet_name', 'N/A'), 'weight_dtype': inputs.get('weight_dtype', 'N/A')})
        for node in self.get_nodes_by_type('LoraLoaderModelOnly'):
            inputs = node.get('inputs', {})
            models['lora'].append({'name': inputs.get('lora_name', 'N/A'), 'strength': inputs.get('strength_model', 'N/A')})
        return models

    def get_sampler_settings(self) -> List[Dict]:
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
            })
        return samplers

    def get_input_images(self) -> List[str]:
        images = []
        for node in self.get_nodes_by_type('LoadImage'):
            image = node.get('inputs', {}).get('image', '')
            if image:
                images.append(image)
        return images

    def get_model_sampling_settings(self) -> List[Dict]:
        settings = []
        for node in self.get_nodes_by_type('ModelSamplingSD3'):
            inputs = node.get('inputs', {})
            meta = node.get('_meta', {})
            settings.append({'title': meta.get('title', 'ModelSamplingSD3'), 'shift': inputs.get('shift', 'N/A')})
        return settings


class DropZoneLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("drop_zone")
        self.setText("Drag and drop a metadata file here\n(supports .txt, .json, .mp4)\nor use File > Open")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(80)
        self.setAcceptDrops(True)
        self.file_dropped_callback = None

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls and self.file_dropped_callback:
            self.file_dropped_callback(urls[0].toLocalFile())


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.parser = MetadataParser()
        self.setWindowTitle("VHS Metadata Parser v1.1.1")
        self.setMinimumSize(900, 700)
        self.setStyleSheet(STYLESHEET)
        self.setAcceptDrops(True)

        icon_path = Path(__file__).parent / "app_icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self._build_ui()

    def _build_ui(self):
        self._create_menu_bar()

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.drop_zone = DropZoneLabel()
        self.drop_zone.file_dropped_callback = self.load_file
        layout.addWidget(self.drop_zone)

        file_row = QHBoxLayout()
        file_row.addWidget(QLabel("Loaded File:"))
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setReadOnly(True)
        self.file_path_edit.setPlaceholderText("No file loaded")
        file_row.addWidget(self.file_path_edit)
        layout.addLayout(file_row)

        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget, 1)

        self._create_video_settings_tab()
        self._create_prompts_tab()
        self._create_models_tab()
        self._create_sampler_tab()
        self._create_workflow_tab()
        self._create_raw_json_tab()

    def _create_menu_bar(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")

        open_action = QAction("Open...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_file_dialog)
        file_menu.addAction(open_action)

        export_csv_action = QAction("Export Models & Sampler (CSV)…", self)
        export_csv_action.setShortcut("Ctrl+E")
        export_csv_action.triggered.connect(self._export_models_sampler_csv)
        file_menu.addAction(export_csv_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            self.load_file(urls[0].toLocalFile())

    def _create_video_settings_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        dims_group = QGroupBox("Video Dimensions")
        dims_layout = QFormLayout(dims_group)
        self.width_edit = QLineEdit(); self.width_edit.setReadOnly(True)
        self.height_edit = QLineEdit(); self.height_edit.setReadOnly(True)
        self.length_edit = QLineEdit(); self.length_edit.setReadOnly(True)
        dims_layout.addRow("Width:", self.width_edit)
        dims_layout.addRow("Height:", self.height_edit)
        dims_layout.addRow("Frames/Length:", self.length_edit)
        layout.addWidget(dims_group)

        output_group = QGroupBox("Output Settings")
        output_layout = QFormLayout(output_group)
        self.frame_rate_edit = QLineEdit(); self.frame_rate_edit.setReadOnly(True)
        self.filename_prefix_edit = QLineEdit(); self.filename_prefix_edit.setReadOnly(True)
        self.format_edit = QLineEdit(); self.format_edit.setReadOnly(True)
        self.crf_edit = QLineEdit(); self.crf_edit.setReadOnly(True)
        self.pix_fmt_edit = QLineEdit(); self.pix_fmt_edit.setReadOnly(True)
        output_layout.addRow("Frame Rate:", self.frame_rate_edit)
        output_layout.addRow("Filename Prefix:", self.filename_prefix_edit)
        output_layout.addRow("Format:", self.format_edit)
        output_layout.addRow("CRF:", self.crf_edit)
        output_layout.addRow("Pixel Format:", self.pix_fmt_edit)
        layout.addWidget(output_group)

        input_group = QGroupBox("Input Images")
        input_layout = QVBoxLayout(input_group)
        self.input_images_edit = QTextEdit(); self.input_images_edit.setReadOnly(True); self.input_images_edit.setMaximumHeight(80)
        input_layout.addWidget(self.input_images_edit)
        layout.addWidget(input_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, "Video Settings")

    def _create_prompts_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        pos_group = QGroupBox("Positive Prompts")
        pos_layout = QVBoxLayout(pos_group)
        self.positive_prompts_edit = QTextEdit(); self.positive_prompts_edit.setReadOnly(True)
        pos_layout.addWidget(self.positive_prompts_edit)
        layout.addWidget(pos_group)

        neg_group = QGroupBox("Negative Prompts")
        neg_layout = QVBoxLayout(neg_group)
        self.negative_prompts_edit = QTextEdit(); self.negative_prompts_edit.setReadOnly(True)
        neg_layout.addWidget(self.negative_prompts_edit)
        layout.addWidget(neg_group)

        self.tab_widget.addTab(tab, "Prompts")

    def _create_models_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        clip_group = QGroupBox("CLIP Models")
        clip_layout = QVBoxLayout(clip_group)
        self.clip_table = self._make_table(['Name', 'Type', 'Device'])
        clip_layout.addWidget(self.clip_table)
        layout.addWidget(clip_group)

        vae_group = QGroupBox("VAE Models")
        vae_layout = QVBoxLayout(vae_group)
        self.vae_table = self._make_table(['Name'])
        vae_layout.addWidget(self.vae_table)
        layout.addWidget(vae_group)

        unet_group = QGroupBox("Diffusion Models (UNET)")
        unet_layout = QVBoxLayout(unet_group)
        self.unet_table = self._make_table(['Name', 'Weight Dtype'])
        unet_layout.addWidget(self.unet_table)
        layout.addWidget(unet_group)

        lora_group = QGroupBox("LoRA Models")
        lora_layout = QVBoxLayout(lora_group)
        self.lora_table = self._make_table(['Name', 'Strength'])
        lora_layout.addWidget(self.lora_table)
        layout.addWidget(lora_group)

        export_btn = QPushButton("Export Models CSV…")
        export_btn.clicked.connect(self._export_models_sampler_csv)
        layout.addWidget(export_btn)

        self.tab_widget.addTab(tab, "Models")

    def _make_table(self, headers: List[str]) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        return table

    def _create_sampler_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        sampler_group = QGroupBox("KSampler Settings")
        sampler_layout = QVBoxLayout(sampler_group)
        self.sampler_table = QTableWidget()
        self.sampler_table.setColumnCount(9)
        self.sampler_table.setHorizontalHeaderLabels(['Title', 'Steps', 'CFG', 'Sampler', 'Scheduler', 'Seed', 'Add Noise', 'Start Step', 'End Step'])
        self.sampler_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.sampler_table.setAlternatingRowColors(True)
        self.sampler_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        sampler_layout.addWidget(self.sampler_table)
        layout.addWidget(sampler_group)

        ms_group = QGroupBox("Model Sampling Settings (Shift)")
        ms_layout = QVBoxLayout(ms_group)
        self.model_sampling_table = QTableWidget()
        self.model_sampling_table.setColumnCount(2)
        self.model_sampling_table.setHorizontalHeaderLabels(['Title', 'Shift'])
        self.model_sampling_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.model_sampling_table.setAlternatingRowColors(True)
        self.model_sampling_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        ms_layout.addWidget(self.model_sampling_table)
        layout.addWidget(ms_group)

        export_btn = QPushButton("Export Sampler CSV…")
        export_btn.clicked.connect(self._export_models_sampler_csv)
        layout.addWidget(export_btn)

        self.tab_widget.addTab(tab, "Sampler")

    def _create_workflow_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        info = QLabel("ComfyUI Workflow JSON — Copy or save this to import into ComfyUI")
        info.setObjectName("subtitle")
        layout.addWidget(info)

        btn_row = QHBoxLayout()
        self.copy_workflow_btn = QPushButton("Copy to Clipboard")
        self.copy_workflow_btn.clicked.connect(self._copy_workflow)
        btn_row.addWidget(self.copy_workflow_btn)

        save_btn = QPushButton("Save Workflow...")
        save_btn.clicked.connect(self._save_workflow)
        btn_row.addWidget(save_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.workflow_json_edit = QTextEdit()
        self.workflow_json_edit.setReadOnly(True)
        layout.addWidget(self.workflow_json_edit)

        self.tab_widget.addTab(tab, "Workflow")

    def _create_raw_json_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.raw_json_edit = QTextEdit()
        self.raw_json_edit.setReadOnly(True)
        layout.addWidget(self.raw_json_edit)
        self.tab_widget.addTab(tab, "Raw JSON")

    def _open_file_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Metadata File", "",
            "All Supported Files (*.txt *.json *.mp4);;MP4 Videos (*.mp4);;Text Files (*.txt);;JSON Files (*.json);;All Files (*.*)"
        )
        if path:
            self.load_file(path)

    def load_file(self, file_path: str):
        if self.parser.parse_file(file_path):
            self.file_path_edit.setText(file_path)
            self.drop_zone.setText(f"File loaded: {Path(file_path).name}")
            self._populate_all()
        else:
            self.file_path_edit.setText("Error loading file")
            self.drop_zone.setText("Error loading file. Please try again.")

    def _populate_all(self):
        self._populate_video_settings()
        self._populate_prompts()
        self._populate_models()
        self._populate_sampler()
        self._populate_workflow()
        self._populate_raw_json()

    def _populate_video_settings(self):
        s = self.parser.get_video_settings()
        self.width_edit.setText(str(s.get('width', 'N/A')))
        self.height_edit.setText(str(s.get('height', 'N/A')))
        self.length_edit.setText(str(s.get('length', 'N/A')))
        self.frame_rate_edit.setText(str(s.get('frame_rate', 'N/A')))
        self.filename_prefix_edit.setText(str(s.get('filename_prefix', 'N/A')))
        self.format_edit.setText(str(s.get('format', 'N/A')))
        self.crf_edit.setText(str(s.get('crf', 'N/A')))
        self.pix_fmt_edit.setText(str(s.get('pix_fmt', 'N/A')))
        images = self.parser.get_input_images()
        self.input_images_edit.setPlainText('\n'.join(images) if images else 'No input images')

    def _populate_prompts(self):
        positive = self.parser.get_positive_prompts()
        negative = self.parser.get_negative_prompts()
        self.positive_prompts_edit.setPlainText('\n\n---\n\n'.join(positive) if positive else 'No positive prompts found')
        self.negative_prompts_edit.setPlainText('\n\n---\n\n'.join(negative) if negative else 'No negative prompts found')

    def _populate_models(self):
        models = self.parser.get_models()
        self.clip_table.setRowCount(len(models['clip']))
        for i, m in enumerate(models['clip']):
            self.clip_table.setItem(i, 0, QTableWidgetItem(str(m['name'])))
            self.clip_table.setItem(i, 1, QTableWidgetItem(str(m['type'])))
            self.clip_table.setItem(i, 2, QTableWidgetItem(str(m['device'])))
        self.vae_table.setRowCount(len(models['vae']))
        for i, m in enumerate(models['vae']):
            self.vae_table.setItem(i, 0, QTableWidgetItem(str(m['name'])))
        self.unet_table.setRowCount(len(models['unet']))
        for i, m in enumerate(models['unet']):
            self.unet_table.setItem(i, 0, QTableWidgetItem(str(m['name'])))
            self.unet_table.setItem(i, 1, QTableWidgetItem(str(m['weight_dtype'])))
        self.lora_table.setRowCount(len(models['lora']))
        for i, m in enumerate(models['lora']):
            self.lora_table.setItem(i, 0, QTableWidgetItem(str(m['name'])))
            self.lora_table.setItem(i, 1, QTableWidgetItem(str(m['strength'])))

    def _populate_sampler(self):
        samplers = self.parser.get_sampler_settings()
        self.sampler_table.setRowCount(len(samplers))
        for i, s in enumerate(samplers):
            for j, key in enumerate(['title', 'steps', 'cfg', 'sampler_name', 'scheduler', 'noise_seed', 'add_noise', 'start_at_step', 'end_at_step']):
                self.sampler_table.setItem(i, j, QTableWidgetItem(str(s[key])))
        ms = self.parser.get_model_sampling_settings()
        self.model_sampling_table.setRowCount(len(ms))
        for i, s in enumerate(ms):
            self.model_sampling_table.setItem(i, 0, QTableWidgetItem(str(s['title'])))
            self.model_sampling_table.setItem(i, 1, QTableWidgetItem(str(s['shift'])))

    def _populate_workflow(self):
        try:
            if self.parser.workflow_data:
                self.workflow_json_edit.setPlainText(json.dumps(self.parser.workflow_data, indent=2, ensure_ascii=False))
            else:
                self.workflow_json_edit.setPlainText("No workflow data available")
        except Exception as e:
            self.workflow_json_edit.setPlainText(f"Error formatting workflow JSON: {e}")

    def _populate_raw_json(self):
        try:
            self.raw_json_edit.setPlainText(json.dumps(self.parser.raw_data, indent=2, ensure_ascii=False))
        except Exception as e:
            self.raw_json_edit.setPlainText(f"Error formatting JSON: {e}")

    def _export_models_sampler_csv(self):
        if not self.parser.raw_data:
            QMessageBox.warning(self, "No Data", "Please load a metadata file first.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Models & Sampler CSV",
            Path(self.file_path_edit.text()).stem + "_models_sampler.csv" if self.file_path_edit.text() else "models_sampler.csv",
            "CSV Files (*.csv);;All Files (*.*)"
        )
        if not path:
            return

        buf = io.StringIO()
        writer = csv.writer(buf)

        # Models
        models = self.parser.get_models()
        writer.writerow(["=== CLIP Models ==="])
        writer.writerow(["Name", "Type", "Device"])
        for m in models['clip']:
            writer.writerow([m['name'], m['type'], m['device']])
        writer.writerow([])

        writer.writerow(["=== VAE Models ==="])
        writer.writerow(["Name"])
        for m in models['vae']:
            writer.writerow([m['name']])
        writer.writerow([])

        writer.writerow(["=== Diffusion Models (UNET) ==="])
        writer.writerow(["Name", "Weight Dtype"])
        for m in models['unet']:
            writer.writerow([m['name'], m['weight_dtype']])
        writer.writerow([])

        writer.writerow(["=== LoRA Models ==="])
        writer.writerow(["Name", "Strength"])
        for m in models['lora']:
            writer.writerow([m['name'], m['strength']])
        writer.writerow([])

        # Sampler
        writer.writerow(["=== KSampler Settings ==="])
        writer.writerow(["Title", "Steps", "CFG", "Sampler", "Scheduler", "Seed", "Add Noise", "Start Step", "End Step"])
        for s in self.parser.get_sampler_settings():
            writer.writerow([s['title'], s['steps'], s['cfg'], s['sampler_name'],
                             s['scheduler'], s['noise_seed'], s['add_noise'],
                             s['start_at_step'], s['end_at_step']])
        writer.writerow([])

        writer.writerow(["=== Model Sampling (Shift) ==="])
        writer.writerow(["Title", "Shift"])
        for s in self.parser.get_model_sampling_settings():
            writer.writerow([s['title'], s['shift']])

        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                f.write(buf.getvalue())
            QMessageBox.information(self, "Exported", f"CSV saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", str(e))

    def _copy_workflow(self):
        text = self.workflow_json_edit.toPlainText()
        if text and text != "No workflow data available":
            QApplication.clipboard().setText(text)
            self.copy_workflow_btn.setText("Copied!")
            QTimer.singleShot(2000, lambda: self.copy_workflow_btn.setText("Copy to Clipboard"))
        else:
            QMessageBox.warning(self, "No Data", "No workflow data to copy. Please load a metadata file first.")

    def _save_workflow(self):
        text = self.workflow_json_edit.toPlainText()
        if not text or text == "No workflow data available":
            QMessageBox.warning(self, "No Data", "No workflow data to save. Please load a metadata file first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Workflow JSON", "workflow.json", "JSON Files (*.json);;All Files (*.*)")
        if path:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(text)
                QMessageBox.information(self, "Saved", f"Workflow saved to:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save workflow:\n{e}")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("VHS Metadata Parser")
    icon_path = Path(__file__).parent / "app_icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
