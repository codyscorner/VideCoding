#!/usr/bin/env python3
"""
VHS Metadata Parser
A PyQt6 application to parse and display ComfyUI workflow metadata files.
Supports drag-and-drop and file browser import.
Version: 1.3.0
"""

import csv
import io
import math
import re
import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QLineEdit, QTextEdit, QScrollArea,
    QGroupBox, QFormLayout, QFileDialog, QMenu,
    QFrame, QSplitter, QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QMessageBox, QCheckBox, QDialog, QAbstractItemView
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QFont, QIcon, QAction, QColor

SUPPORTED_EXTENSIONS = ('.mp4', '.json', '.txt')


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


# Input keys that carry prompt text on any node type (CLIPTextEncode, MiniMaxH3ImageToVideo, PromptCycler, ...)
PROMPT_INPUT_KEYS = (
    'prompt', 'text', 'positive', 'negative', 'positive_prompt', 'negative_prompt',
    'custom_prompts', 'string', 'text_positive', 'text_negative',
)

# Safe namespace for evaluating ComfyMathExpression nodes (used to resolve e.g. MiniMax frame counts)
_SAFE_MATH_FUNCS = {
    'max': max, 'min': min, 'round': round, 'abs': abs, 'int': int, 'float': float,
    'floor': math.floor, 'ceil': math.ceil, 'sqrt': math.sqrt, 'pow': pow,
}
_MATH_EXPR_ALLOWED_RE = re.compile(r'^[\w\s+\-*/%().,<>=!]+$')

# Prompt-section parsing (MiniMax H3 shot-list style prompts + generic "Label: text" prompts)
SHOT_MARKER_RE = re.compile(r'\[\s*(shot\s*\d+)[^\]]*\]', re.IGNORECASE)
SHOT_TIME_RE = re.compile(r'^\s*(?:at\s+)?(\d{1,2}:\d{2}(?:\.\d+)?)', re.IGNORECASE)
DIALOGUE_RE = re.compile(r'<d>(.*?)</d>', re.IGNORECASE | re.DOTALL)
SECTION_LABEL_RE = re.compile(
    r'(?<![\w<\[])'                                              # not glued to a word, tag or bracket
    r'((?:[a-z]+(?:_[a-z]+)+)'                                   # snake_case_key  (overall_soundscape)
    r'|(?:[A-Z][a-zA-Z]{1,20}(?:\s[A-Z]?[a-zA-Z]{1,20}){0,2}))'  # Capitalised label, 1-3 words (Camera, Sound Design)
    r':(?=\s|$)'                                                 # colon followed by whitespace/end
)


def _flatten_json_sections(obj: Any, prefix: str = '') -> List[Tuple[str, str]]:
    """Flatten a JSON-style prompt object into (label, text) pairs."""
    out: List[Tuple[str, str]] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            label = f"{prefix}{k}"
            if isinstance(v, (dict, list)):
                out.extend(_flatten_json_sections(v, label + '.'))
            else:
                out.append((label, str(v)))
    elif isinstance(obj, list):
        if all(not isinstance(i, (dict, list)) for i in obj):
            out.append((prefix.rstrip('.') or 'list', '\n'.join(str(i) for i in obj)))
        else:
            for i, item in enumerate(obj):
                out.extend(_flatten_json_sections(item, f"{prefix.rstrip('.')}[{i}]."))
    else:
        out.append((prefix.rstrip('.') or 'value', str(obj)))
    return out


def _split_labeled_chunks(body: str) -> List[Tuple[Optional[str], str]]:
    """Split text on 'Label:' markers. Returns [(None, leading_text), (label, text), ...]."""
    matches = list(SECTION_LABEL_RE.finditer(body))
    if not matches:
        return [(None, body)]
    chunks: List[Tuple[Optional[str], str]] = [(None, body[:matches[0].start()])]
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        chunks.append((m.group(1), body[m.end():end]))
    return chunks


def parse_prompt_sections(text: str) -> List[Tuple[str, str]]:
    """
    Break a prompt into labelled sections so the important parts are easy to read:
      - JSON prompts  -> one section per key (nested keys joined with '.')
      - [Shot N] At 00:04.000 ...  -> one section per shot, plus a 'Shot N · Dialogue' section for <d>...</d> lines
      - Camera: / overall_soundscape: / non_diegetic_music: / Any Label:  -> one section each
    Plain prompts with no markers come back as a single ('Prompt', text) section.
    """
    text = (text or '').strip()
    if not text:
        return []

    if text[0] in '{[':
        try:
            return _flatten_json_sections(json.loads(text))
        except Exception:
            pass

    segments: List[Tuple[str, str]] = []
    shots = list(SHOT_MARKER_RE.finditer(text))
    if shots:
        intro = text[:shots[0].start()].strip()
        if intro:
            segments.append(('Intro', intro))
        for i, m in enumerate(shots):
            end = shots[i + 1].start() if i + 1 < len(shots) else len(text)
            body = text[m.end():end].strip()
            label = re.sub(r'\s+', ' ', m.group(1)).title()
            tm = SHOT_TIME_RE.match(body)
            if tm:
                label += f" @ {tm.group(1)}"
                body = body[tm.end():].strip()
            segments.append((label, body))
    else:
        segments.append(('Prompt', text))

    sections: List[Tuple[str, str]] = []
    for seg_label, body in segments:
        for sub_label, chunk in _split_labeled_chunks(body):
            chunk = chunk.strip()
            if not chunk:
                continue
            label = sub_label if sub_label else seg_label
            sections.append((label, chunk))
            dialogue = [d.strip() for d in DIALOGUE_RE.findall(chunk) if d.strip()]
            if dialogue:
                sections.append((f"{label} · Dialogue", '\n'.join(dialogue)))
    return sections


class MetadataParser:
    """
    Parses ComfyUI workflow metadata and extracts relevant fields.

    Node inputs are read through `_take()`, which (a) resolves links to the node that
    feeds the value where possible and (b) records the (node, input) pair as "consumed".
    `get_other_settings()` then lists every literal input the dedicated extractors did
    not consume, so settings from unfamiliar node types are never silently dropped.
    """

    def __init__(self):
        self.raw_data: Dict = {}
        self.prompt_data: Dict = {}
        self.workflow_data: Dict = {}
        self.consumed: Dict[str, set] = {}

    # ------------------------------------------------------------------ loading

    def parse_file(self, file_path: str) -> bool:
        try:
            self.raw_data, self.prompt_data, self.workflow_data, self.consumed = {}, {}, {}, {}
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
            elif self.raw_data and all(isinstance(v, dict) and 'class_type' in v for v in self.raw_data.values()):
                # Bare API-format prompt JSON (no {"prompt": ...} wrapper)
                self.prompt_data = self.raw_data

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

    # ------------------------------------------------------------------ node helpers

    @staticmethod
    def _is_link(value: Any) -> bool:
        return isinstance(value, list) and len(value) == 2 and isinstance(value[0], (str, int)) and isinstance(value[1], int)

    def _nodes(self):
        return list(self.prompt_data.items())

    @staticmethod
    def _title(node: Dict, node_id: str = '') -> str:
        return node.get('_meta', {}).get('title') or node.get('class_type') or f"node {node_id}"

    def _mark(self, node_id: str, key: str):
        self.consumed.setdefault(str(node_id), set()).add(key)

    def _eval_math_expression(self, node_id: str, node: Dict, depth: int) -> Optional[Any]:
        """Evaluate a ComfyMathExpression node with a whitelisted namespace. Returns None if unsafe/unknown."""
        ins = node.get('inputs', {})
        expr = ins.get('expression')
        if not isinstance(expr, str) or not _MATH_EXPR_ALLOWED_RE.match(expr):
            return None
        names: Dict[str, Any] = {}
        for k, v in ins.items():
            name = k[7:] if k.startswith('values.') else (k if k in ('a', 'b', 'c') else None)
            if name is None:
                continue
            val = self._resolve(v, name, depth + 1)
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                return None
            names[name] = val
        for ident in re.findall(r'[A-Za-z_]\w*', expr):
            if ident not in names and ident not in _SAFE_MATH_FUNCS:
                return None
        try:
            result = eval(expr, {'__builtins__': {}}, {**_SAFE_MATH_FUNCS, **names})  # noqa: S307 - whitelisted
        except Exception:
            return None
        for k in ins:
            self._mark(node_id, k)
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        return result

    def _resolve(self, value: Any, key: str = '', depth: int = 0) -> Any:
        """Follow a [node_id, slot] link back to a literal value when that is possible."""
        if not self._is_link(value) or depth > 8:
            return value
        src_id = str(value[0])
        src = self.prompt_data.get(src_id)
        if not isinstance(src, dict):
            return f"→ node {src_id}"
        ins = src.get('inputs', {})
        ctype = src.get('class_type', '')

        if ctype == 'ComfyMathExpression':
            result = self._eval_math_expression(src_id, src, depth)
            if result is not None:
                return result

        for k in (key, 'value'):
            if k and k in ins and not self._is_link(ins[k]):
                self._mark(src_id, k)
                return ins[k]

        if key in PROMPT_INPUT_KEYS:
            for k in PROMPT_INPUT_KEYS:
                if isinstance(ins.get(k), str) and ins[k].strip():
                    self._mark(src_id, k)
                    return ins[k]

        if key and key in ins and self._is_link(ins[key]):
            return self._resolve(ins[key], key, depth + 1)

        return f"→ {self._title(src, src_id)} [{src_id}]"

    def _take(self, node_id: str, key: str, default: Any = 'N/A') -> Any:
        """Read one input of a node, resolving links and marking it consumed."""
        node = self.prompt_data.get(str(node_id), {})
        ins = node.get('inputs', {})
        if key not in ins:
            return default
        self._mark(node_id, key)
        return self._resolve(ins[key], key)

    def _link_source(self, node_id: str, key: str):
        """Return (src_id, src_node) for a link input, or (None, None)."""
        ins = self.prompt_data.get(str(node_id), {}).get('inputs', {})
        value = ins.get(key)
        if not self._is_link(value):
            return None, None
        src_id = str(value[0])
        src = self.prompt_data.get(src_id)
        return (src_id, src) if isinstance(src, dict) else (None, None)

    def get_nodes_by_type(self, class_type: str) -> List[Dict]:
        nodes = []
        for node_id, node_data in self._nodes():
            if node_data.get('class_type') == class_type:
                node_data['_node_id'] = node_id
                nodes.append(node_data)
        return nodes

    # ------------------------------------------------------------------ prompts

    def get_prompt_entries(self) -> List[Dict[str, Any]]:
        """
        Every prompt-like text input in the workflow (CLIPTextEncode.text, MiniMaxH3ImageToVideo.prompt,
        PromptCycler.custom_prompts, ...). Literal strings are collected first, then links are resolved,
        and duplicate texts are dropped so a prompt fed through several nodes only appears once.
        """
        entries: List[Dict[str, Any]] = []
        seen_texts: set = set()

        def add(node_id, node, key, text):
            norm = text.strip()
            if not norm or norm in seen_texts:
                return
            seen_texts.add(norm)
            title = self._title(node, node_id)
            polarity = 'negative' if ('negative' in key.lower() or 'negative' in title.lower()) else 'positive'
            entries.append({
                'node_id': node_id, 'class_type': node.get('class_type', ''), 'title': title,
                'key': key, 'text': text, 'polarity': polarity,
            })

        for want_links in (False, True):
            for node_id, node in self._nodes():
                ins = node.get('inputs', {})
                for key in PROMPT_INPUT_KEYS:
                    if key not in ins:
                        continue
                    raw = ins[key]
                    if not want_links and isinstance(raw, str):
                        self._mark(node_id, key)
                        add(node_id, node, key, raw)
                    elif want_links and self._is_link(raw):
                        text = self._resolve(raw, key)
                        if isinstance(text, str) and not text.startswith('→ '):
                            add(node_id, node, key, text)
        return entries

    def get_positive_prompts(self) -> List[str]:
        return [e['text'] for e in self.get_prompt_entries() if e['polarity'] == 'positive']

    def get_negative_prompts(self) -> List[str]:
        return [e['text'] for e in self.get_prompt_entries() if e['polarity'] == 'negative']

    def get_prompt_sections(self) -> List[Dict[str, Any]]:
        """Prompt entries broken into labelled sections (see parse_prompt_sections)."""
        rows = []
        for e in self.get_prompt_entries():
            source = f"{e['title']} [{e['node_id']}] · {e['key']} ({e['polarity']})"
            for label, content in parse_prompt_sections(e['text']):
                rows.append({'source': source, 'section': label, 'content': content, 'polarity': e['polarity']})
        return rows

    # ------------------------------------------------------------------ video / models / sampler

    def get_video_settings(self) -> Dict:
        settings: Dict[str, Any] = {}
        for node_id, node in self._nodes():
            ctype = node.get('class_type', '')
            ins = node.get('inputs', {})
            # WanImageToVideo, MiniMaxH3ImageToVideo, *TextToVideo, EmptyHunyuanLatentVideo, ...
            if ctype.endswith('ToVideo') or ctype.endswith('LatentVideo'):
                for key in ('width', 'height', 'length', 'batch_size'):
                    if key in ins:
                        settings[key] = self._take(node_id, key)
        for node_id, node in self._nodes():
            if node.get('class_type') == 'VHS_VideoCombine':
                for key in ('frame_rate', 'filename_prefix', 'format', 'crf', 'pix_fmt', 'loop_count'):
                    settings[key] = self._take(node_id, key)
                src_id, src = self._link_source(node_id, 'audio')
                settings['has_audio'] = f"Yes — {self._title(src, src_id)} [{src_id}]" if src else 'No'
        for node_id, node in self._nodes():
            if node.get('class_type') in ('ImageResizeKJv2', 'ImageScale', 'ImageResize+'):
                ins = node.get('inputs', {})
                for key in ('width', 'height'):
                    if not isinstance(settings.get(key), int) and key in ins:
                        settings[key] = self._take(node_id, key)
                if 'upscale_method' in ins:
                    settings['upscale_method'] = self._take(node_id, 'upscale_method')
                if 'keep_proportion' in ins:
                    settings['keep_proportion'] = self._take(node_id, 'keep_proportion')

        length, fps = settings.get('length'), settings.get('frame_rate')
        if isinstance(length, (int, float)) and isinstance(fps, (int, float)) and fps:
            settings['duration_s'] = round(length / fps, 2)
        return settings

    def get_models(self) -> Dict[str, List[Dict]]:
        models: Dict[str, List[Dict]] = {'clip': [], 'vae': [], 'unet': [], 'lora': []}
        for node_id, node in self._nodes():
            ins = node.get('inputs', {})
            if 'clip_name' in ins:
                models['clip'].append({'name': self._take(node_id, 'clip_name'),
                                       'type': self._take(node_id, 'type'),
                                       'device': self._take(node_id, 'device')})
            for key in ('clip_name1', 'clip_name2', 'clip_name3'):
                if key in ins:
                    models['clip'].append({'name': self._take(node_id, key),
                                           'type': self._take(node_id, 'type'),
                                           'device': self._take(node_id, 'device')})
            if 'vae_name' in ins:
                models['vae'].append({'name': self._take(node_id, 'vae_name')})
            if 'unet_name' in ins:
                models['unet'].append({'name': self._take(node_id, 'unet_name'),
                                       'weight_dtype': self._take(node_id, 'weight_dtype')})
            if 'ckpt_name' in ins:
                models['unet'].append({'name': self._take(node_id, 'ckpt_name'), 'weight_dtype': 'checkpoint'})
            if 'lora_name' in ins:
                strength = self._take(node_id, 'strength_model', None)
                if strength is None:
                    strength = self._take(node_id, 'strength', 'N/A')
                models['lora'].append({'name': self._take(node_id, 'lora_name'), 'strength': strength,
                                       'title': self._title(node, node_id)})
        return models

    def get_sampler_settings(self) -> List[Dict]:
        samplers = []
        for node_id, node in self._nodes():
            ctype = node.get('class_type', '')
            ins = node.get('inputs', {})
            title = self._title(node, node_id)
            if ctype.startswith('KSampler') and 'steps' in ins:
                samplers.append({
                    'title': title,
                    'steps': self._take(node_id, 'steps'),
                    'cfg': self._take(node_id, 'cfg'),
                    'sampler_name': self._take(node_id, 'sampler_name'),
                    'scheduler': self._take(node_id, 'scheduler'),
                    'noise_seed': self._take(node_id, 'noise_seed') if 'noise_seed' in ins else self._take(node_id, 'seed'),
                    'add_noise': self._take(node_id, 'add_noise'),
                    'start_at_step': self._take(node_id, 'start_at_step'),
                    'end_at_step': self._take(node_id, 'end_at_step'),
                    'denoise': self._take(node_id, 'denoise'),
                })
            elif ctype in ('SamplerCustomAdvanced', 'SamplerCustom'):
                row = {'title': title, 'steps': 'N/A', 'cfg': 'N/A', 'sampler_name': 'N/A', 'scheduler': 'N/A',
                       'noise_seed': 'N/A', 'add_noise': self._take(node_id, 'add_noise'),
                       'start_at_step': 'N/A', 'end_at_step': 'N/A', 'denoise': 'N/A'}
                # seed: literal on SamplerCustom, or from the RandomNoise node feeding SamplerCustomAdvanced
                if 'noise_seed' in ins:
                    row['noise_seed'] = self._take(node_id, 'noise_seed')
                else:
                    src_id, src = self._link_source(node_id, 'noise')
                    if src:
                        row['noise_seed'] = self._take(src_id, 'noise_seed')
                # cfg: literal, or from a CFGGuider; BasicGuider has no CFG
                if 'cfg' in ins:
                    row['cfg'] = self._take(node_id, 'cfg')
                else:
                    src_id, src = self._link_source(node_id, 'guider')
                    if src:
                        row['cfg'] = self._take(src_id, 'cfg', f"N/A ({self._title(src, src_id)})")
                # sampler: KSamplerSelect name, or the custom sampler node's title (e.g. MiniMax-H3 Turbo Sampler)
                src_id, src = self._link_source(node_id, 'sampler')
                if src:
                    row['sampler_name'] = self._take(src_id, 'sampler_name', self._title(src, src_id))
                # sigmas: BasicScheduler & friends carry scheduler / steps / denoise
                src_id, src = self._link_source(node_id, 'sigmas')
                if src:
                    row['scheduler'] = self._take(src_id, 'scheduler', self._title(src, src_id))
                    row['steps'] = self._take(src_id, 'steps')
                    row['denoise'] = self._take(src_id, 'denoise')
                samplers.append(row)
        return samplers

    def get_input_images(self) -> List[str]:
        images = []
        for node_id, node in self._nodes():
            ctype = node.get('class_type', '')
            ins = node.get('inputs', {})
            if ctype == 'LoadImage' and isinstance(ins.get('image'), str):
                images.append(self._take(node_id, 'image'))
            elif ctype in ('LoadVideo', 'VHS_LoadVideo') and isinstance(ins.get('video'), str):
                images.append(f"[video] {self._take(node_id, 'video')}")
            elif ctype == 'LoadAudio' and isinstance(ins.get('audio'), str):
                images.append(f"[audio] {self._take(node_id, 'audio')}")
        return images

    def get_model_sampling_settings(self) -> List[Dict]:
        settings = []
        for node_id, node in self._nodes():
            ctype = node.get('class_type', '')
            if not ctype.startswith('ModelSampling'):
                continue
            ins = node.get('inputs', {})
            if 'shift' in ins:
                shift = self._take(node_id, 'shift')
            else:
                parts = [f"{k}={self._take(node_id, k)}" for k, v in ins.items() if not self._is_link(v)]
                shift = ', '.join(parts) if parts else 'N/A'
            settings.append({'title': self._title(node, node_id), 'shift': shift})
        return settings

    # ------------------------------------------------------------------ everything else

    def get_other_settings(self) -> List[Dict[str, Any]]:
        """
        Literal inputs that none of the dedicated extractors consumed, grouped per node.
        Each item: {'node_id', 'class_type', 'title', 'settings': [(key, value), ...], 'covered': bool}
        `covered` is True when the node contributed something to another tab (so an empty
        settings list there just means "fully shown elsewhere").
        """
        # Run every extractor so `consumed` is complete
        self.get_video_settings()
        self.get_prompt_entries()
        self.get_models()
        self.get_sampler_settings()
        self.get_input_images()
        self.get_model_sampling_settings()

        rows = []
        for node_id, node in self._nodes():
            ins = node.get('inputs', {})
            used = self.consumed.get(str(node_id), set())
            leftovers = [(k, v) for k, v in ins.items() if not self._is_link(v) and k not in used]
            rows.append({
                'node_id': node_id,
                'class_type': node.get('class_type', ''),
                'title': self._title(node, node_id),
                'settings': leftovers,
                'covered': bool(used),
            })
        return rows


def summarize_file(file_path: str) -> Dict[str, Any]:
    """Parse a single file and reduce it to a flat summary row used by batch/search/diff."""
    parser = MetadataParser()
    ok = parser.parse_file(file_path)
    row: Dict[str, Any] = {'file': file_path, 'name': Path(file_path).name, 'error': not ok}
    if not ok:
        return row

    settings = parser.get_video_settings()
    models = parser.get_models()
    samplers = parser.get_sampler_settings()
    positive = parser.get_positive_prompts()
    negative = parser.get_negative_prompts()
    lora_names = [m['name'] for m in models['lora']]
    unet_names = [m['name'] for m in models['unet']]
    clip_names = [m['name'] for m in models['clip']]
    vae_names = [m['name'] for m in models['vae']]

    row.update({
        'width': settings.get('width', 'N/A'),
        'height': settings.get('height', 'N/A'),
        'length': settings.get('length', 'N/A'),
        'frame_rate': settings.get('frame_rate', 'N/A'),
        'format': settings.get('format', 'N/A'),
        'duration_s': settings.get('duration_s', 'N/A'),
        'has_audio': settings.get('has_audio', 'N/A'),
        'steps': samplers[0]['steps'] if samplers else 'N/A',
        'cfg': samplers[0]['cfg'] if samplers else 'N/A',
        'sampler_name': samplers[0]['sampler_name'] if samplers else 'N/A',
        'scheduler': samplers[0]['scheduler'] if samplers else 'N/A',
        'lora': ', '.join(lora_names),
        'unet': ', '.join(unet_names),
        'clip': ', '.join(clip_names),
        'vae': ', '.join(vae_names),
        'positive_prompt': ' | '.join(positive),
        'negative_prompt': ' | '.join(negative),
        'prompt_data': parser.prompt_data,
        'workflow_data': parser.workflow_data,
        'raw_data': parser.raw_data,
    })
    return row


def row_matches_search(row: Dict[str, Any], term: str) -> bool:
    if not term:
        return True
    term = term.lower()
    haystacks = [
        row.get('name', ''), row.get('lora', ''), row.get('unet', ''),
        row.get('clip', ''), row.get('vae', ''), row.get('sampler_name', ''),
        row.get('positive_prompt', ''), row.get('negative_prompt', ''), row.get('format', ''),
    ]
    return any(term in str(h).lower() for h in haystacks)


class BatchScanWorker(QThread):
    progress = pyqtSignal(int, int)
    row_ready = pyqtSignal(dict)
    finished_scan = pyqtSignal()

    def __init__(self, files: List[str], parent=None):
        super().__init__(parent)
        self.files = files

    def run(self):
        total = len(self.files)
        for i, file_path in enumerate(self.files, 1):
            row = summarize_file(file_path)
            self.row_ready.emit(row)
            self.progress.emit(i, total)
        self.finished_scan.emit()


class DiffDialog(QDialog):
    """Side-by-side comparison of key metadata fields between two files."""

    FIELDS = [
        ('name', 'File'), ('width', 'Width'), ('height', 'Height'), ('length', 'Frames/Length'),
        ('frame_rate', 'Frame Rate'), ('duration_s', 'Duration (s)'), ('has_audio', 'Audio'),
        ('format', 'Format'), ('steps', 'Steps'), ('cfg', 'CFG'),
        ('sampler_name', 'Sampler'), ('scheduler', 'Scheduler'), ('unet', 'UNET'),
        ('clip', 'CLIP'), ('vae', 'VAE'), ('lora', 'LoRA'),
        ('positive_prompt', 'Positive Prompt'), ('negative_prompt', 'Negative Prompt'),
    ]

    def __init__(self, row_a: Dict[str, Any], row_b: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Diff: {row_a.get('name')} vs {row_b.get('name')}")
        self.resize(900, 600)

        layout = QVBoxLayout(self)
        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(['Field', row_a.get('name', 'File A'), row_b.get('name', 'File B')])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setWordWrap(True)
        table.setRowCount(len(self.FIELDS))

        diff_count = 0
        for i, (key, label) in enumerate(self.FIELDS):
            val_a = str(row_a.get(key, 'N/A'))
            val_b = str(row_b.get(key, 'N/A'))
            differs = val_a != val_b
            if differs and key != 'name':
                diff_count += 1
            table.setItem(i, 0, QTableWidgetItem(label))
            item_a = QTableWidgetItem(val_a)
            item_b = QTableWidgetItem(val_b)
            if differs and key != 'name':
                item_a.setBackground(QColor(COLORS['accent_dark']))
                item_b.setBackground(QColor(COLORS['accent_dark']))
            table.setItem(i, 1, item_a)
            table.setItem(i, 2, item_b)
        table.resizeRowsToContents()
        layout.addWidget(QLabel(f"{diff_count} field(s) differ"))
        layout.addWidget(table)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


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
        self.batch_rows: List[Dict[str, Any]] = []
        self.batch_visible_rows: List[Dict[str, Any]] = []
        self.batch_worker: Optional[BatchScanWorker] = None
        self.setWindowTitle("VHS Metadata Parser v1.3.0")
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
        self.tab_widget.currentChanged.connect(lambda _idx: self._refit_prompt_sections())
        layout.addWidget(self.tab_widget, 1)

        self._create_video_settings_tab()
        self._create_prompts_tab()
        self._create_models_tab()
        self._create_sampler_tab()
        self._create_other_settings_tab()
        self._create_workflow_tab()
        self._create_raw_json_tab()
        self._create_batch_tab()

    def _create_menu_bar(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")

        open_action = QAction("Open...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_file_dialog)
        file_menu.addAction(open_action)

        export_csv_action = QAction("Export Models, Sampler && Other Settings (CSV)…", self)
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
        self.duration_edit = QLineEdit(); self.duration_edit.setReadOnly(True)
        dims_layout.addRow("Frames/Length:", self.length_edit)
        dims_layout.addRow("Duration (s):", self.duration_edit)
        layout.addWidget(dims_group)

        output_group = QGroupBox("Output Settings")
        output_layout = QFormLayout(output_group)
        self.frame_rate_edit = QLineEdit(); self.frame_rate_edit.setReadOnly(True)
        self.filename_prefix_edit = QLineEdit(); self.filename_prefix_edit.setReadOnly(True)
        self.format_edit = QLineEdit(); self.format_edit.setReadOnly(True)
        self.crf_edit = QLineEdit(); self.crf_edit.setReadOnly(True)
        self.pix_fmt_edit = QLineEdit(); self.pix_fmt_edit.setReadOnly(True)
        self.audio_edit = QLineEdit(); self.audio_edit.setReadOnly(True)
        output_layout.addRow("Frame Rate:", self.frame_rate_edit)
        output_layout.addRow("Filename Prefix:", self.filename_prefix_edit)
        output_layout.addRow("Format:", self.format_edit)
        output_layout.addRow("CRF:", self.crf_edit)
        output_layout.addRow("Pixel Format:", self.pix_fmt_edit)
        output_layout.addRow("Audio:", self.audio_edit)
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

        splitter = QSplitter(Qt.Orientation.Vertical)

        sections_group = QGroupBox("Prompt Sections")
        sections_layout = QVBoxLayout(sections_group)
        hint = QLabel("Prompts broken into shots / labelled parts ([Shot N] At 00:00.000, Camera:, overall_soundscape:, "
                      "non_diegetic_music:, <d>dialogue</d>, JSON keys). Source shows which node the text came from.")
        hint.setObjectName("subtitle")
        hint.setWordWrap(True)
        sections_layout.addWidget(hint)
        self.prompt_sections_table = QTableWidget()
        self.prompt_sections_table.setColumnCount(3)
        self.prompt_sections_table.setHorizontalHeaderLabels(['Source', 'Section', 'Content'])
        header = self.prompt_sections_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.prompt_sections_table.setColumnWidth(0, 260)
        self.prompt_sections_table.setColumnWidth(1, 170)
        self.prompt_sections_table.setAlternatingRowColors(True)
        self.prompt_sections_table.setWordWrap(True)
        self.prompt_sections_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.prompt_sections_table.verticalHeader().setVisible(False)
        header.sectionResized.connect(lambda *_: self.prompt_sections_table.resizeRowsToContents())
        sections_layout.addWidget(self.prompt_sections_table)
        splitter.addWidget(sections_group)

        raw_widget = QWidget()
        raw_layout = QVBoxLayout(raw_widget)
        raw_layout.setContentsMargins(0, 0, 0, 0)

        pos_group = QGroupBox("Positive Prompts (raw)")
        pos_layout = QVBoxLayout(pos_group)
        self.positive_prompts_edit = QTextEdit(); self.positive_prompts_edit.setReadOnly(True)
        pos_layout.addWidget(self.positive_prompts_edit)
        raw_layout.addWidget(pos_group)

        neg_group = QGroupBox("Negative Prompts (raw)")
        neg_layout = QVBoxLayout(neg_group)
        self.negative_prompts_edit = QTextEdit(); self.negative_prompts_edit.setReadOnly(True)
        neg_layout.addWidget(self.negative_prompts_edit)
        raw_layout.addWidget(neg_group)
        splitter.addWidget(raw_widget)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)

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
        self.lora_table = self._make_table(['Name', 'Strength', 'Loader'])
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

        sampler_group = QGroupBox("Sampler Settings (KSampler / SamplerCustomAdvanced)")
        sampler_layout = QVBoxLayout(sampler_group)
        self.sampler_table = QTableWidget()
        self.sampler_table.setColumnCount(10)
        self.sampler_table.setHorizontalHeaderLabels(['Title', 'Steps', 'CFG', 'Sampler', 'Scheduler', 'Seed', 'Add Noise', 'Start Step', 'End Step', 'Denoise'])
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

    def _create_other_settings_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        info = QLabel("Every literal node setting that is NOT already shown on the Video / Prompts / Models / Sampler tabs. "
                      "Use this to spot important settings from node types the parser has no dedicated view for "
                      "(resolution selectors, schedulers, turbo samplers, save flags, custom nodes…).")
        info.setObjectName("subtitle")
        info.setWordWrap(True)
        layout.addWidget(info)

        controls = QHBoxLayout()
        self.other_show_empty_check = QCheckBox("Show nodes that have no literal settings (links only)")
        self.other_show_empty_check.setChecked(False)
        self.other_show_empty_check.stateChanged.connect(lambda _state: self._populate_other_settings())
        controls.addWidget(self.other_show_empty_check)
        controls.addWidget(QLabel("Filter:"))
        self.other_filter_edit = QLineEdit()
        self.other_filter_edit.setPlaceholderText("node id, node type, title, setting or value…")
        self.other_filter_edit.textChanged.connect(lambda _text: self._populate_other_settings())
        controls.addWidget(self.other_filter_edit, 1)
        layout.addLayout(controls)

        self.other_status_label = QLabel("No file loaded.")
        self.other_status_label.setObjectName("subtitle")
        layout.addWidget(self.other_status_label)

        self.other_table = QTableWidget()
        self.other_table.setColumnCount(5)
        self.other_table.setHorizontalHeaderLabels(['Node ID', 'Node Type', 'Title', 'Setting', 'Value'])
        header = self.other_table.horizontalHeader()
        for col in range(4):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.other_table.setAlternatingRowColors(True)
        self.other_table.setWordWrap(True)
        self.other_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.other_table.verticalHeader().setVisible(False)
        layout.addWidget(self.other_table, 1)

        export_btn = QPushButton("Export Models, Sampler && Other Settings CSV…")
        export_btn.clicked.connect(self._export_models_sampler_csv)
        layout.addWidget(export_btn)

        self.tab_widget.addTab(tab, "Other Settings")

    def _populate_other_settings(self):
        if not self.parser.prompt_data:
            self.other_table.setRowCount(0)
            self.other_status_label.setText("No file loaded.")
            return
        show_empty = self.other_show_empty_check.isChecked()
        term = self.other_filter_edit.text().strip().lower()
        flat: List[List[str]] = []
        nodes_with_settings = 0
        for node in self.parser.get_other_settings():
            if node['settings']:
                nodes_with_settings += 1
                for key, value in node['settings']:
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value, ensure_ascii=False)
                    flat.append([str(node['node_id']), node['class_type'], node['title'], key, str(value)])
            elif show_empty and not node['covered']:
                flat.append([str(node['node_id']), node['class_type'], node['title'], '(no literal settings)', ''])
        if term:
            flat = [row for row in flat if any(term in cell.lower() for cell in row)]

        self.other_table.setRowCount(len(flat))
        for i, row in enumerate(flat):
            for j, cell in enumerate(row):
                item = QTableWidgetItem(cell)
                if j == 3 and cell == '(no literal settings)':
                    item.setForeground(QColor(COLORS['fg_dim']))
                self.other_table.setItem(i, j, item)
        self.other_table.setCurrentItem(None)
        self.other_table.resizeRowsToContents()
        self.other_status_label.setText(
            f"{len(flat)} setting(s) from {nodes_with_settings} node(s) not covered by the other tabs."
        )

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

    def _create_batch_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        controls = QHBoxLayout()
        self.batch_scan_btn = QPushButton("Scan Folder…")
        self.batch_scan_btn.clicked.connect(self._scan_batch_folder)
        controls.addWidget(self.batch_scan_btn)

        self.batch_recursive_check = QCheckBox("Include subfolders")
        self.batch_recursive_check.setChecked(True)
        controls.addWidget(self.batch_recursive_check)

        controls.addWidget(QLabel("Search:"))
        self.batch_search_edit = QLineEdit()
        self.batch_search_edit.setPlaceholderText("Filter by name, LoRA, model, sampler, prompt text…")
        self.batch_search_edit.textChanged.connect(self._filter_batch_rows)
        controls.addWidget(self.batch_search_edit, 1)
        layout.addLayout(controls)

        self.batch_status_label = QLabel("No folder scanned yet.")
        self.batch_status_label.setObjectName("subtitle")
        layout.addWidget(self.batch_status_label)

        self.batch_table = QTableWidget()
        batch_headers = ['File', 'Width', 'Height', 'Length', 'FPS', 'Format',
                          'Steps', 'CFG', 'Sampler', 'LoRA', 'UNET']
        self.batch_table.setColumnCount(len(batch_headers))
        self.batch_table.setHorizontalHeaderLabels(batch_headers)
        self.batch_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.batch_table.horizontalHeader().setStretchLastSection(True)
        self.batch_table.setAlternatingRowColors(True)
        self.batch_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.batch_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.batch_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.batch_table.doubleClicked.connect(self._load_batch_row_into_viewer)
        layout.addWidget(self.batch_table, 1)

        btn_row = QHBoxLayout()
        diff_btn = QPushButton("Diff Selected (pick 2)")
        diff_btn.clicked.connect(self._diff_selected_batch_rows)
        btn_row.addWidget(diff_btn)

        export_btn = QPushButton("Export Summary CSV…")
        export_btn.clicked.connect(self._export_batch_summary_csv)
        btn_row.addWidget(export_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.tab_widget.addTab(tab, "Batch / Search")

    def _scan_batch_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Scan")
        if not folder:
            return

        folder_path = Path(folder)
        pattern = folder_path.rglob('*') if self.batch_recursive_check.isChecked() else folder_path.glob('*')
        files = [str(p) for p in pattern if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS]

        if not files:
            QMessageBox.information(self, "No Files", "No .mp4, .json, or .txt files found in that folder.")
            return

        self.batch_rows = []
        self.batch_table.setRowCount(0)
        self.batch_scan_btn.setEnabled(False)
        self.batch_status_label.setText(f"Scanning 0 / {len(files)}…")

        self.batch_worker = BatchScanWorker(files, self)
        self.batch_worker.row_ready.connect(self._on_batch_row_ready)
        self.batch_worker.progress.connect(self._on_batch_progress)
        self.batch_worker.finished_scan.connect(self._on_batch_scan_finished)
        self.batch_worker.start()

    def _on_batch_row_ready(self, row: Dict[str, Any]):
        self.batch_rows.append(row)

    def _on_batch_progress(self, done: int, total: int):
        self.batch_status_label.setText(f"Scanning {done} / {total}…")

    def _on_batch_scan_finished(self):
        self.batch_scan_btn.setEnabled(True)
        ok_count = sum(1 for r in self.batch_rows if not r.get('error'))
        err_count = len(self.batch_rows) - ok_count
        suffix = f", {err_count} failed to parse" if err_count else ""
        self.batch_status_label.setText(f"Scanned {len(self.batch_rows)} file(s){suffix}.")
        self._filter_batch_rows()

    def _filter_batch_rows(self):
        term = self.batch_search_edit.text().strip()
        self.batch_visible_rows = [r for r in self.batch_rows if not r.get('error') and row_matches_search(r, term)]
        self._populate_batch_table()

    def _populate_batch_table(self):
        rows = self.batch_visible_rows
        self.batch_table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            values = [r.get('name'), r.get('width'), r.get('height'), r.get('length'),
                      r.get('frame_rate'), r.get('format'), r.get('steps'), r.get('cfg'),
                      r.get('sampler_name'), r.get('lora'), r.get('unet')]
            for j, v in enumerate(values):
                self.batch_table.setItem(i, j, QTableWidgetItem(str(v) if v not in (None, '') else ('' if j in (9, 10) else 'N/A')))

    def _selected_batch_rows(self) -> List[Dict[str, Any]]:
        rows_idx = sorted({idx.row() for idx in self.batch_table.selectionModel().selectedRows()})
        return [self.batch_visible_rows[i] for i in rows_idx if i < len(self.batch_visible_rows)]

    def _load_batch_row_into_viewer(self):
        selected = self._selected_batch_rows()
        if selected:
            self.load_file(selected[0]['file'])
            self.tab_widget.setCurrentIndex(0)

    def _diff_selected_batch_rows(self):
        selected = self._selected_batch_rows()
        if len(selected) != 2:
            QMessageBox.information(self, "Select Two Files", "Select exactly two rows (Ctrl+Click) to diff.")
            return
        dialog = DiffDialog(selected[0], selected[1], self)
        dialog.exec()

    def _export_batch_summary_csv(self):
        if not self.batch_visible_rows:
            QMessageBox.warning(self, "No Data", "Scan a folder first (and clear search filters if the list is empty).")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Batch Summary CSV", "batch_summary.csv", "CSV Files (*.csv);;All Files (*.*)"
        )
        if not path:
            return

        headers = ['File', 'Path', 'Width', 'Height', 'Length', 'Frame Rate', 'Duration (s)', 'Audio', 'Format',
                   'Steps', 'CFG', 'Sampler', 'Scheduler', 'CLIP', 'VAE', 'UNET', 'LoRA',
                   'Positive Prompt', 'Negative Prompt']
        keys = ['name', 'file', 'width', 'height', 'length', 'frame_rate', 'duration_s', 'has_audio', 'format',
                'steps', 'cfg', 'sampler_name', 'scheduler', 'clip', 'vae', 'unet', 'lora',
                'positive_prompt', 'negative_prompt']
        try:
            with open(path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                for r in self.batch_visible_rows:
                    writer.writerow([r.get(k, '') for k in keys])
            QMessageBox.information(self, "Exported", f"CSV saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", str(e))

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
        self._populate_other_settings()
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
        self.duration_edit.setText(str(s.get('duration_s', 'N/A')))
        self.audio_edit.setText(str(s.get('has_audio', 'N/A')))
        images = self.parser.get_input_images()
        self.input_images_edit.setPlainText('\n'.join(images) if images else 'No input images')

    def _populate_prompts(self):
        positive = self.parser.get_positive_prompts()
        negative = self.parser.get_negative_prompts()
        self.positive_prompts_edit.setPlainText('\n\n---\n\n'.join(positive) if positive else 'No positive prompts found')
        self.negative_prompts_edit.setPlainText('\n\n---\n\n'.join(negative) if negative else 'No negative prompts found')

        rows = self.parser.get_prompt_sections()
        self.prompt_sections_table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            source_item = QTableWidgetItem(r['source'])
            section_item = QTableWidgetItem(r['section'])
            content_item = QTableWidgetItem(r['content'])
            if r['polarity'] == 'negative':
                for item in (source_item, section_item, content_item):
                    item.setForeground(QColor(COLORS['error']))
            if 'Dialogue' in r['section']:
                section_item.setForeground(QColor(COLORS['accent_hover']))
            self.prompt_sections_table.setItem(i, 0, source_item)
            self.prompt_sections_table.setItem(i, 1, section_item)
            self.prompt_sections_table.setItem(i, 2, content_item)
        self.prompt_sections_table.setCurrentItem(None)
        self._refit_prompt_sections()

    def _refit_prompt_sections(self):
        # Row heights depend on the Content column width, which is only final once the tab is laid out.
        # (Also fires from tab_widget.currentChanged while tabs are still being built, hence the guard.)
        table = getattr(self, 'prompt_sections_table', None)
        if table is None:
            return
        table.resizeRowsToContents()
        QTimer.singleShot(0, table.resizeRowsToContents)

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
            self.lora_table.setItem(i, 2, QTableWidgetItem(str(m.get('title', ''))))

    def _populate_sampler(self):
        samplers = self.parser.get_sampler_settings()
        self.sampler_table.setRowCount(len(samplers))
        for i, s in enumerate(samplers):
            for j, key in enumerate(['title', 'steps', 'cfg', 'sampler_name', 'scheduler', 'noise_seed', 'add_noise', 'start_at_step', 'end_at_step', 'denoise']):
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
        writer.writerow(["Name", "Strength", "Loader"])
        for m in models['lora']:
            writer.writerow([m['name'], m['strength'], m.get('title', '')])
        writer.writerow([])

        # Sampler
        writer.writerow(["=== Sampler Settings ==="])
        writer.writerow(["Title", "Steps", "CFG", "Sampler", "Scheduler", "Seed", "Add Noise", "Start Step", "End Step", "Denoise"])
        for s in self.parser.get_sampler_settings():
            writer.writerow([s['title'], s['steps'], s['cfg'], s['sampler_name'],
                             s['scheduler'], s['noise_seed'], s['add_noise'],
                             s['start_at_step'], s['end_at_step'], s['denoise']])
        writer.writerow([])

        writer.writerow(["=== Model Sampling (Shift) ==="])
        writer.writerow(["Title", "Shift"])
        for s in self.parser.get_model_sampling_settings():
            writer.writerow([s['title'], s['shift']])
        writer.writerow([])

        writer.writerow(["=== Other Settings (not shown on other tabs) ==="])
        writer.writerow(["Node ID", "Node Type", "Title", "Setting", "Value"])
        for node in self.parser.get_other_settings():
            for key, value in node['settings']:
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False)
                writer.writerow([node['node_id'], node['class_type'], node['title'], key, value])

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
