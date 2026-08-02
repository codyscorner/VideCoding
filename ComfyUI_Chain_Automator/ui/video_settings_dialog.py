from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QGroupBox, QFormLayout, QTabWidget, QWidget, QLineEdit,
)

from metadata_parser import extract_chain_segments, SegmentMetadata
from ui.styles import COLORS


class VideoSettingsDialog(QDialog):
    """Read-only view of the prompt/sampler/model settings embedded in a
    stitched Library video, one tab per chain segment."""

    def __init__(self, video_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Generation Settings — {Path(video_path).name}")
        self.setMinimumSize(700, 560)
        self.resize(760, 620)
        self.setStyleSheet(parent.styleSheet() if parent else "")

        layout = QVBoxLayout(self)
        segments = extract_chain_segments(video_path) or {}

        if not segments:
            note = QLabel(
                "No embedded generation metadata found in this video.\n\n"
                "This video was likely stitched before this feature was added, "
                "or its segment videos didn't include ComfyUI metadata."
            )
            note.setWordWrap(True)
            note.setStyleSheet(f"color:{COLORS['fg_dim']};")
            layout.addWidget(note)
        else:
            tabs = QTabWidget()
            for seg_key in sorted(segments, key=lambda k: int(k)):
                tabs.addTab(self._build_segment_tab(segments[seg_key]), f"Segment {seg_key}")
            layout.addWidget(tabs, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setFixedHeight(34)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _build_segment_tab(self, prompt_data: dict) -> QWidget:
        meta = SegmentMetadata(prompt_data)
        tab = QWidget()
        layout = QVBoxLayout(tab)

        pos_group = QGroupBox("Positive Prompt")
        pos_layout = QVBoxLayout(pos_group)
        pos_edit = QTextEdit()
        pos_edit.setReadOnly(True)
        pos_edit.setPlainText("\n\n---\n\n".join(meta.get_positive_prompts()) or "N/A")
        pos_edit.setMaximumHeight(110)
        pos_layout.addWidget(pos_edit)
        layout.addWidget(pos_group)

        neg_group = QGroupBox("Negative Prompt")
        neg_layout = QVBoxLayout(neg_group)
        neg_edit = QTextEdit()
        neg_edit.setReadOnly(True)
        neg_edit.setPlainText("\n\n---\n\n".join(meta.get_negative_prompts()) or "N/A")
        neg_edit.setMaximumHeight(90)
        neg_layout.addWidget(neg_edit)
        layout.addWidget(neg_group)

        vid_settings = meta.get_video_settings()
        vid_group = QGroupBox("Video Settings")
        vid_layout = QFormLayout(vid_group)
        for label, key in (("Width:", "width"), ("Height:", "height"),
                           ("Length (frames):", "length"), ("Frame Rate:", "frame_rate"),
                           ("Format:", "format")):
            edit = QLineEdit(str(vid_settings.get(key, "N/A")))
            edit.setReadOnly(True)
            vid_layout.addRow(label, edit)
        layout.addWidget(vid_group)

        samplers = meta.get_sampler_settings()
        sampler_group = QGroupBox("Sampler")
        sampler_layout = QVBoxLayout(sampler_group)
        if samplers:
            for s in samplers:
                edit = QLineEdit(
                    f"{s['title']}: steps={s['steps']} cfg={s['cfg']} "
                    f"sampler={s['sampler_name']} scheduler={s['scheduler']} "
                    f"seed={s['noise_seed']} range=[{s['start_at_step']},{s['end_at_step']}]"
                )
                edit.setReadOnly(True)
                sampler_layout.addWidget(edit)
        else:
            sampler_layout.addWidget(QLabel("N/A"))
        layout.addWidget(sampler_group)

        models = meta.get_models()
        models_group = QGroupBox("Models")
        models_layout = QVBoxLayout(models_group)
        unet_text = ", ".join(models.get("unet", [])) or "N/A"
        lora_text = ", ".join(models.get("lora", [])) or "N/A"
        models_layout.addWidget(QLabel(f"UNET: {unet_text}"))
        lora_lbl = QLabel(f"LoRA: {lora_text}")
        lora_lbl.setWordWrap(True)
        models_layout.addWidget(lora_lbl)
        layout.addWidget(models_group)

        layout.addStretch()
        return tab
