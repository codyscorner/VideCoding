"""Inspect and patch ComfyUI API-format workflow JSON.

Everything the app needs to know about a workflow before running it:
which node takes the starting image (or a whole folder, or a video),
which text fields are prompts, where the seed lives, which node writes
the video, and how many sampler steps to expect for the progress bar.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

IMAGE_NODE_TYPES = {"LoadImage": "image"}
LIST_LOADER_TYPES = {
    "LoadImageListFromDir //Inspire": "directory",
    "LoadImagesFromDir //Inspire": "directory",
}
VIDEO_NODE_TYPES = {"LoadVideo": "file", "VHS_LoadVideo": "video"}
VIDEO_OUTPUT_TYPES = {"VHS_VideoCombine", "SaveVideo"}
IMAGE_OUTPUT_TYPES = {"SaveImage", "SaveAnimatedWEBP", "SaveAnimatedPNG"}

# Post-sampling nodes that produce no step-level progress events — each
# counts as one extra unit on the progress bar so it doesn't sit at 100%
# while the VAE decode / encode / save stretch is still running.
STATUS_NODE_LABELS = {
    "VAEDecode": "Decoding video (VAE)...",
    "VAEDecodeAudio": "Decoding audio (VAE)...",
    "CreateVideo": "Encoding video...",
    "SaveVideo": "Saving video...",
    "VHS_VideoCombine": "Saving video...",
}

HISTORY_SUFFIX = ".prompt_history.json"


class WorkflowError(Exception):
    pass


@dataclass
class PromptField:
    node_id: str
    key: str
    label: str
    negative: bool = False
    text: str = ""


@dataclass
class ValueField:
    node_id: str
    key: str
    label: str
    kind: str          # "int" | "float"
    value: float


@dataclass
class Analysis:
    image_nodes: list[tuple[str, str]] = field(default_factory=list)          # (id, title)
    list_loaders: list[tuple[str, str]] = field(default_factory=list)         # (id, title)
    video_nodes: list[tuple[str, str, str]] = field(default_factory=list)     # (id, title, input key)
    prompts: list[PromptField] = field(default_factory=list)
    seed_fields: list[tuple[str, str]] = field(default_factory=list)          # (id, key)
    length_field: ValueField | None = None
    output_nodes: list[str] = field(default_factory=list)
    image_output_nodes: list[str] = field(default_factory=list)
    sampler_steps: list[int] = field(default_factory=list)
    post_phases: int = 0

    @property
    def accepts_image(self) -> bool:
        return bool(self.image_nodes or self.list_loaders)

    @property
    def accepts_video(self) -> bool:
        return bool(self.video_nodes)

    def describe(self) -> str:
        parts = []
        if self.image_nodes:
            parts.append("image input: " + ", ".join(t or i for i, t in self.image_nodes))
        if self.list_loaders:
            parts.append("folder loader (the single image is staged into a run folder)")
        if self.video_nodes:
            parts.append("video input: " + ", ".join(t or i for i, t, _ in self.video_nodes))
        if not parts:
            parts.append("no image or video input node found")
        outs = len(self.output_nodes)
        if outs:
            parts.append(f"{outs} video output node" + ("s" if outs != 1 else ""))
        else:
            parts.append("no video output node (SaveVideo / VHS_VideoCombine)")
        return " · ".join(parts)


# --------------------------------------------------------------------- #
# Loading / listing
# --------------------------------------------------------------------- #

def is_api_format(data) -> bool:
    if not isinstance(data, dict) or not data:
        return False
    nodes = [v for v in data.values() if isinstance(v, dict)]
    return bool(nodes) and all("class_type" in v for v in nodes)


def load_workflow(path: Path) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise WorkflowError(f"{path.name}: not valid JSON ({e})") from e
    except OSError as e:
        raise WorkflowError(f"{path.name}: cannot read file ({e})") from e
    if isinstance(data, dict) and "nodes" in data and "links" in data:
        raise WorkflowError(
            f"{path.name} is a UI-format workflow (the kind ComfyUI saves with Ctrl+S). "
            "The API needs the API export: in ComfyUI use Workflow > Export (API) and pick that file."
        )
    if not is_api_format(data):
        raise WorkflowError(
            f"{path.name}: not a ComfyUI API-format workflow (expected a JSON object of node-id -> node)."
        )
    return data


def list_workflows(workflow_dir: Path) -> list[str]:
    """Relative POSIX paths of every candidate workflow JSON under the folder."""
    if not workflow_dir or not workflow_dir.is_dir():
        return []
    out = []
    for p in sorted(workflow_dir.rglob("*.json"), key=lambda p: str(p).lower()):
        if p.name.lower().endswith(HISTORY_SUFFIX):
            continue
        if any(part.lower() == "thumbnails" for part in p.relative_to(workflow_dir).parts):
            continue
        out.append(p.relative_to(workflow_dir).as_posix())
    return out


# --------------------------------------------------------------------- #
# Analysis
# --------------------------------------------------------------------- #

def _title(node: dict) -> str:
    return (node.get("_meta") or {}).get("title") or ""


def _sort_key(nid: str):
    # "105:104" style ids from subgraphs sort after plain ints
    try:
        return (0, int(nid), "")
    except ValueError:
        return (1, 0, nid)


def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def analyze(workflow: dict) -> Analysis:
    a = Analysis()
    positives: list[PromptField] = []
    negatives: list[PromptField] = []
    duration: ValueField | None = None
    length_int: ValueField | None = None

    for nid in sorted(workflow.keys(), key=_sort_key):
        node = workflow[nid]
        if not isinstance(node, dict):
            continue
        ct = node.get("class_type", "")
        title = _title(node)
        inp = node.get("inputs", {}) or {}

        if ct in IMAGE_NODE_TYPES:
            a.image_nodes.append((nid, title))
        elif ct in LIST_LOADER_TYPES:
            a.list_loaders.append((nid, title))
        elif ct in VIDEO_NODE_TYPES:
            a.video_nodes.append((nid, title, VIDEO_NODE_TYPES[ct]))

        if ct in VIDEO_OUTPUT_TYPES:
            a.output_nodes.append(nid)
        elif ct in IMAGE_OUTPUT_TYPES:
            a.image_output_nodes.append(nid)

        # Prompts ------------------------------------------------------
        if ct == "CLIPTextEncode" and isinstance(inp.get("text"), str):
            neg = "neg" in title.lower()
            label = title or ("Negative Prompt" if neg else "Positive Prompt")
            (negatives if neg else positives).append(PromptField(nid, "text", label, neg, inp["text"]))
        elif ct.startswith("MiniMaxH3") and isinstance(inp.get("prompt"), str):
            positives.append(PromptField(nid, "prompt", title or "MiniMax H3 Prompt", False, inp["prompt"]))
        elif ct == "PrimitiveStringMultiline" and isinstance(inp.get("value"), str):
            neg = "neg" in title.lower()
            (negatives if neg else positives).append(PromptField(nid, "value", title or "Text", neg, inp["value"]))

        # Seeds --------------------------------------------------------
        for key in ("noise_seed", "seed"):
            if _is_int(inp.get(key)):
                a.seed_fields.append((nid, key))

        # Length / duration -------------------------------------------
        if ct == "PrimitiveFloat" and "duration" in title.lower() and isinstance(inp.get("value"), (int, float)):
            if duration is None:
                duration = ValueField(nid, "value", "Duration (seconds)", "float", float(inp["value"]))
        elif ct in ("WanImageToVideo", "EmptyMiniMaxH3LatentAV", "MiniMaxH3ImageToVideo",
                    "MiniMaxH3ReferenceToVideo", "EmptyHunyuanLatentVideo") and _is_int(inp.get("length")):
            if length_int is None:
                length_int = ValueField(nid, "length", "Length (frames)", "int", int(inp["length"]))

        # Sampler steps -----------------------------------------------
        if "sampler" in ct.lower() or ct == "BasicScheduler":
            steps = inp.get("steps")
            if _is_int(steps) and steps > 0:
                start, end = inp.get("start_at_step"), inp.get("end_at_step")
                if _is_int(start) and _is_int(end):
                    steps = max(0, min(end, steps) - max(start, 0))
                if steps:
                    a.sampler_steps.append(steps)
        if ct in STATUS_NODE_LABELS:
            a.post_phases += 1

    a.prompts = positives + negatives
    a.length_field = duration or length_int
    return a


# --------------------------------------------------------------------- #
# Patching
# --------------------------------------------------------------------- #

def apply_prompts(workflow: dict, edits: dict[tuple[str, str], str]) -> None:
    for (nid, key), text in edits.items():
        node = workflow.get(nid)
        if isinstance(node, dict):
            node.setdefault("inputs", {})[key] = text


def apply_seed(workflow: dict, seed: int) -> int:
    n = 0
    for node in workflow.values():
        if not isinstance(node, dict):
            continue
        inp = node.get("inputs", {}) or {}
        for key in ("noise_seed", "seed"):
            if _is_int(inp.get(key)):
                inp[key] = seed
                n += 1
    return n


def apply_value(workflow: dict, fld: ValueField, value: float) -> None:
    node = workflow.get(fld.node_id)
    if isinstance(node, dict):
        node.setdefault("inputs", {})[fld.key] = int(value) if fld.kind == "int" else float(value)


def set_output_prefix(workflow: dict, prefix: str) -> None:
    for node in workflow.values():
        if not isinstance(node, dict):
            continue
        if node.get("class_type") in VIDEO_OUTPUT_TYPES | IMAGE_OUTPUT_TYPES:
            if "filename_prefix" in (node.get("inputs") or {}):
                node["inputs"]["filename_prefix"] = prefix


def save_workflow(path: Path, workflow: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(workflow, f, indent=2, ensure_ascii=False)
