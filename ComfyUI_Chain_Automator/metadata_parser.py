"""Reads and writes the ComfyUI generation metadata embedded in MP4s.

VHS_VideoCombine embeds the executed prompt graph as a global MP4 'comment'
atom, e.g. {"prompt": "<json-encoded node graph>", "workflow": {...}}. The
Chain Automator's ffmpeg concat/re-encode step strips that, so _stitch()
(batch_worker.py) re-extracts each segment's prompt graph before it's
discarded and re-embeds a combined payload into the final stitched video
under a distinct top-level key so it can be read back in the Library tab.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional

SEGMENT_PROMPT_MARKER = b'{"prompt"'
CHAIN_SEGMENTS_MARKER = b'{"chain_automator_segments"'


def _scan_balanced_json(data: bytes, marker: bytes) -> Optional[dict]:
    idx = data.find(marker)
    if idx == -1:
        return None
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
    try:
        return json.loads(json_bytes.decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        return None


def extract_segment_prompt(video_path) -> Optional[dict]:
    """Read the raw ComfyUI prompt graph VHS_VideoCombine embeds in a
    freshly-rendered segment video, before it gets stitched/re-encoded."""
    try:
        data = Path(video_path).read_bytes()
    except OSError:
        return None
    raw = _scan_balanced_json(data, SEGMENT_PROMPT_MARKER)
    if not raw:
        return None
    prompt = raw.get('prompt')
    if isinstance(prompt, str):
        try:
            return json.loads(prompt)
        except ValueError:
            return None
    return prompt


def extract_chain_segments(video_path) -> Optional[Dict[str, dict]]:
    """Read back the per-segment prompt graphs Chain Automator embeds into
    its own stitched output videos (see batch_worker._stitch)."""
    try:
        data = Path(video_path).read_bytes()
    except OSError:
        return None
    obj = _scan_balanced_json(data, CHAIN_SEGMENTS_MARKER)
    if not obj:
        return None
    return obj.get('chain_automator_segments')


def ffmetadata_escape(value: str) -> str:
    """Escape a value for an ffmpeg ';FFMETADATA1' key=value line."""
    for ch in ('\\', '=', ';', '#', '\n'):
        value = value.replace(ch, '\\' + ch)
    return value


class SegmentMetadata:
    """Read-only view over one segment's ComfyUI prompt graph (node_id ->
    node dict). Mirrors VHS_Metadata_Parser's MetadataParser getters."""

    def __init__(self, prompt_data: dict):
        self.prompt_data = prompt_data or {}

    def get_nodes_by_type(self, class_type: str) -> List[dict]:
        nodes = []
        for node_id, node_data in self.prompt_data.items():
            if node_data.get('class_type') == class_type:
                node_data = dict(node_data)
                node_data['_node_id'] = node_id
                nodes.append(node_data)
        return nodes

    def get_positive_prompts(self) -> List[str]:
        prompts = []
        for node in self.get_nodes_by_type('CLIPTextEncode'):
            title = node.get('_meta', {}).get('title', '')
            if 'positive' in title.lower():
                text = node.get('inputs', {}).get('text', '')
                if text:
                    prompts.append(text)
        if not prompts:
            for node in self.get_nodes_by_type('CLIPTextEncode'):
                title = node.get('_meta', {}).get('title', '')
                if 'negative' not in title.lower():
                    text = node.get('inputs', {}).get('text', '')
                    if text:
                        prompts.append(text)
        if not prompts:
            # MiniMax H3 nodes (MiniMaxH3ImageToVideo etc.) pack the whole
            # structured prompt into a single `prompt` field — no separate
            # positive/negative split.
            for node_id, node in self.prompt_data.items():
                if node.get('class_type', '').startswith('MiniMaxH3'):
                    text = node.get('inputs', {}).get('prompt', '')
                    if text:
                        prompts.append(text)
        return prompts

    def get_negative_prompts(self) -> List[str]:
        prompts = []
        for node in self.get_nodes_by_type('CLIPTextEncode'):
            title = node.get('_meta', {}).get('title', '')
            if 'negative' in title.lower():
                text = node.get('inputs', {}).get('text', '')
                if text:
                    prompts.append(text)
        return prompts

    def get_sampler_settings(self) -> List[dict]:
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
                'start_at_step': inputs.get('start_at_step', 'N/A'),
                'end_at_step': inputs.get('end_at_step', 'N/A'),
            })
        return samplers

    def get_video_settings(self) -> dict:
        settings = {}
        for node in self.get_nodes_by_type('WanImageToVideo'):
            inputs = node.get('inputs', {})
            settings['width'] = inputs.get('width', 'N/A')
            settings['height'] = inputs.get('height', 'N/A')
            settings['length'] = inputs.get('length', 'N/A')
        for node in self.get_nodes_by_type('VHS_VideoCombine'):
            inputs = node.get('inputs', {})
            settings['frame_rate'] = inputs.get('frame_rate', 'N/A')
            settings['format'] = inputs.get('format', 'N/A')
        return settings

    def get_models(self) -> dict:
        models = {'unet': [], 'lora': []}
        for node in self.get_nodes_by_type('UNETLoader'):
            models['unet'].append(node.get('inputs', {}).get('unet_name', 'N/A'))
        for node in self.get_nodes_by_type('LoraLoaderModelOnly'):
            inputs = node.get('inputs', {})
            models['lora'].append(f"{inputs.get('lora_name', 'N/A')} @ {inputs.get('strength_model', 'N/A')}")
        return models


def build_prompts_text(segments: Dict[str, dict]) -> str:
    """Plain-text summary of every segment's prompt/sampler/video settings,
    meant to be dropped into the per-video zip archive as prompts.txt so it
    can be read without opening any file individually."""
    lines = []
    for seg_key in sorted(segments, key=lambda k: int(k)):
        meta = SegmentMetadata(segments[seg_key])
        lines.append(f"=== Segment {seg_key} ===")

        positive = meta.get_positive_prompts()
        lines.append("Positive Prompt:")
        lines.append("\n---\n".join(positive) if positive else "N/A")
        lines.append("")

        negative = meta.get_negative_prompts()
        lines.append("Negative Prompt:")
        lines.append("\n---\n".join(negative) if negative else "N/A")
        lines.append("")

        vid = meta.get_video_settings()
        if vid:
            lines.append(
                f"Video: {vid.get('width', 'N/A')}x{vid.get('height', 'N/A')}, "
                f"{vid.get('length', 'N/A')} frames, {vid.get('frame_rate', 'N/A')} fps, "
                f"format={vid.get('format', 'N/A')}"
            )

        for s in meta.get_sampler_settings():
            lines.append(
                f"Sampler ({s['title']}): steps={s['steps']} cfg={s['cfg']} "
                f"sampler={s['sampler_name']} scheduler={s['scheduler']} "
                f"seed={s['noise_seed']} range=[{s['start_at_step']},{s['end_at_step']}]"
            )

        models = meta.get_models()
        if models.get('unet'):
            lines.append(f"UNET: {', '.join(models['unet'])}")
        if models.get('lora'):
            lines.append(f"LoRA: {', '.join(models['lora'])}")

        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
