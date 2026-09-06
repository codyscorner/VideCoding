"""Inspect and patch ComfyUI API-format workflow JSON.

Everything the app needs to know about a workflow before running it:
which node takes the starting image (or a whole folder, or a video),
which text fields are prompts, where the seed lives, which node writes
the video, and how many sampler steps to expect for the progress bar.
"""

from __future__ import annotations

import json
import re
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

LORA_EXTS = {".safetensors", ".pt", ".pt2", ".bin", ".pth", ".ckpt", ".pkl", ".sft"}
_LORA_KEY_RE = re.compile(r"^lora(_name|_\d+)$")


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
class LoraSlot:
    """One selectable LoRA in the workflow: a name input plus its strength
    input(s). `LoraLoaderModelOnly` has lora_name/strength_model, rgthree's
    stack has lora_01..lora_NN with strength_NN, MiniMax H3 Turbo has
    lora_name/strength."""
    node_id: str
    name_key: str
    label: str
    name: str
    strengths: dict[str, float] = field(default_factory=dict)   # strength key -> value
    allow_none: bool = False

    def strength_label(self, key: str) -> str:
        return {"strength_model": "Model", "strength_clip": "CLIP"}.get(key, "")


@dataclass
class StepsField:
    """A sampler/scheduler node's `steps` input. WAN 2.2 hi/lo pairs are two
    KSamplerAdvanced nodes sharing one step count and splitting it with
    start_at_step / end_at_step — those boundaries are rescaled when the
    count changes so the split point stays proportional."""
    node_id: str
    label: str
    value: int
    start: int | None = None
    end: int | None = None


@dataclass
class Analysis:
    image_nodes: list[tuple[str, str]] = field(default_factory=list)          # (id, title)
    list_loaders: list[tuple[str, str]] = field(default_factory=list)         # (id, title)
    video_nodes: list[tuple[str, str, str]] = field(default_factory=list)     # (id, title, input key)
    prompts: list[PromptField] = field(default_factory=list)
    loras: list[LoraSlot] = field(default_factory=list)
    steps_fields: list[StepsField] = field(default_factory=list)
    mp_fields: list[ValueField] = field(default_factory=list)      # numeric `megapixels` inputs
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


INVALID_NAME_CHARS = r'<>:"/\|?*'
_RESERVED_NAMES = {"con", "prn", "aux", "nul",
                   *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}


def check_workflow_name(name: str) -> str:
    """Return an error message for a proposed workflow file name, or "" if it's fine."""
    stem = name.strip()
    if stem.lower().endswith(".json"):
        stem = stem[:-5].strip()
    if not stem:
        return "Enter a name."
    bad = sorted({c for c in stem if c in INVALID_NAME_CHARS or ord(c) < 32})
    if bad:
        return "A file name cannot contain " + " ".join(bad)
    if stem.endswith(".") or stem.endswith(" "):
        return "A file name cannot end with a dot or a space."
    if stem.split(".")[0].lower() in _RESERVED_NAMES:
        return f'"{stem}" is a name Windows reserves.'
    if stem.lower().endswith(HISTORY_SUFFIX[:-5]):
        return "That name collides with the prompt-history file naming."
    return ""


def workflow_stem(name: str) -> str:
    """The file stem for a name typed by the user (a typed .json is not doubled up)."""
    stem = name.strip()
    if stem.lower().endswith(".json"):
        stem = stem[:-5].strip()
    return stem


def unique_workflow_path(folder: Path, stem: str) -> Path:
    """`folder/stem.json`, or `stem (2).json`, `stem (3).json`… if that is taken."""
    candidate = folder / f"{stem}.json"
    n = 2
    while candidate.exists():
        candidate = folder / f"{stem} ({n}).json"
        n += 1
    return candidate


def list_workflow_folders(workflow_dir: Path) -> list[str]:
    """Relative POSIX paths of the workflow folder and every subfolder ("" = root)."""
    if not workflow_dir or not workflow_dir.is_dir():
        return []
    out = [""]
    for p in sorted(workflow_dir.rglob("*"), key=lambda p: str(p).lower()):
        if not p.is_dir():
            continue
        rel = p.relative_to(workflow_dir)
        if any(part.lower() == "thumbnails" for part in rel.parts):
            continue
        out.append(rel.as_posix())
    return out


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

        # LoRAs --------------------------------------------------------
        if "lora" in ct.lower():
            for key, val in inp.items():
                if not (isinstance(val, str) and _LORA_KEY_RE.match(key)):
                    continue
                if key == "lora_name":
                    cand = ["strength_model", "strength_clip", "strength"]
                    slot_label = title or ct
                else:
                    cand = [key.replace("lora_", "strength_")]
                    slot_label = f"{title or 'LoRA Stack'} #{key.split('_')[1]}"
                strengths = {
                    k: float(inp[k]) for k in cand
                    if isinstance(inp.get(k), (int, float)) and not isinstance(inp.get(k), bool)
                }
                a.loras.append(LoraSlot(nid, key, slot_label, val, strengths, allow_none=(key != "lora_name")))

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

        # Megapixels (ImageScaleToTotalPixels, ResolutionSelector, ...) --
        mp = inp.get("megapixels")
        if isinstance(mp, (int, float)) and not isinstance(mp, bool):
            fld = ValueField(nid, "megapixels", title or ct, "float", float(mp))
            # The scale node is what actually sizes the frames — list it first
            # so the control shows its value (a ResolutionSelector may differ).
            if ct == "ImageScaleToTotalPixels":
                a.mp_fields.insert(0, fld)
            else:
                a.mp_fields.append(fld)

        # Sampler steps -----------------------------------------------
        if "sampler" in ct.lower() or ct == "BasicScheduler":
            steps = inp.get("steps")
            if _is_int(steps) and steps > 0:
                start, end = inp.get("start_at_step"), inp.get("end_at_step")
                a.steps_fields.append(StepsField(
                    nid, title or ct, steps,
                    start if _is_int(start) else None, end if _is_int(end) else None))
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

def apply_inputs(workflow: dict, edits: dict[tuple[str, str], object]) -> None:
    """Set node inputs by (node id, input key). Used for prompt text and
    LoRA name/strength edits alike."""
    for (nid, key), value in edits.items():
        node = workflow.get(nid)
        if isinstance(node, dict):
            node.setdefault("inputs", {})[key] = value


apply_prompts = apply_inputs


def list_loras(loras_dir: Path, sep: str = "\\") -> list[str]:
    """LoRA file names the way ComfyUI lists them: paths relative to the
    models/loras folder. ComfyUI joins subfolders with the server OS
    separator (backslash on Windows, slash on a RunPod Linux pod)."""
    if not loras_dir or not loras_dir.is_dir():
        return []
    out = []
    for p in loras_dir.rglob("*"):
        if p.is_file() and p.suffix.lower() in LORA_EXTS and not p.name.startswith("."):
            out.append(sep.join(p.relative_to(loras_dir).parts))
    return sorted(out, key=str.lower)


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


def apply_steps(workflow: dict, fields: list[StepsField], new_steps: int) -> int:
    """Set every sampler's step count, rescaling KSamplerAdvanced start/end
    boundaries proportionally (a boundary at or past the old count means
    "to the end" and follows the new count). Returns nodes changed."""
    new_steps = max(1, int(new_steps))
    n = 0
    for fld in fields:
        node = workflow.get(fld.node_id)
        if not isinstance(node, dict):
            continue
        inp = node.setdefault("inputs", {})
        old = fld.value if fld.value > 0 else new_steps
        inp["steps"] = new_steps
        if fld.start is not None:
            inp["start_at_step"] = min(new_steps, round(fld.start * new_steps / old)) if fld.start < old else new_steps
        if fld.end is not None:
            inp["end_at_step"] = round(fld.end * new_steps / old) if fld.end < old else max(new_steps, fld.end)
        n += 1
    return n


def apply_megapixels(workflow: dict, fields: list[ValueField], value: float) -> int:
    n = 0
    for fld in fields:
        if isinstance(workflow.get(fld.node_id), dict):
            apply_value(workflow, fld, round(float(value), 3))
            n += 1
    return n


# --------------------------------------------------------------------- #
# Output video format (VHS_VideoCombine "format", SaveVideo "codec")
# --------------------------------------------------------------------- #

# ffmpeg's codec name -> the spellings workflows use in their widgets.
# The first alias is the one written back into the workflow.
CODEC_ALIASES: dict[str, tuple[str, ...]] = {
    "h264": ("h264", "avc1", "avc"),
    "hevc": ("h265", "hevc", "x265"),
    "av1": ("av1",),
    "vp9": ("vp9",),
    "vp8": ("vp8",),
    "prores": ("prores",),
    "ffv1": ("ffv1",),
}

# Used when the server can't be asked what the node accepts.
KNOWN_FORMAT_VALUES = {
    "video/h264-mp4", "video/h265-mp4", "video/nvenc_h264-mp4", "video/nvenc_hevc-mp4",
    "video/nvenc_av1-mp4", "video/av1-webm", "video/webm", "video/ProRes", "video/ffv1-mkv",
    "auto", "h264", "h265", "av1", "vp9",
}


@dataclass
class OutputFormat:
    """A video-output node's format/codec widget."""
    node_id: str
    key: str                  # "format" (VHS_VideoCombine) or "codec" (SaveVideo)
    label: str
    value: str

    @property
    def codec(self) -> str:
        """ffmpeg codec name this widget value produces, "" if unrecognized."""
        return codec_of(self.value)


def codec_of(value: str) -> str:
    """"video/nvenc_hevc-mp4" -> "hevc". "" when nothing matches (e.g. "auto")."""
    low = str(value or "").lower()
    for codec, aliases in CODEC_ALIASES.items():
        if any(a in low for a in aliases):
            return codec
    return ""


def output_formats(workflow: dict) -> list[OutputFormat]:
    out: list[OutputFormat] = []
    for nid, node in workflow.items():
        if not isinstance(node, dict) or node.get("class_type") not in VIDEO_OUTPUT_TYPES:
            continue
        inp = node.get("inputs") or {}
        for key in ("format", "codec"):
            val = inp.get(key)
            if isinstance(val, str) and val:
                out.append(OutputFormat(nid, key, _title(node) or node["class_type"], val))
    return out


def match_format_value(current: str, codec: str, allowed: list[str] | None = None) -> str:
    """The `current` widget value rewritten to produce `codec`, keeping the
    container and encoder family (nvenc stays nvenc). "" when there is no
    such value the node would accept."""
    now = codec_of(current)
    if not codec or not now or now == codec:
        return ""
    pool = {str(a) for a in allowed} if allowed else KNOWN_FORMAT_VALUES
    low = current.lower()
    for old in CODEC_ALIASES.get(now, ()):
        if old not in low:
            continue
        start = low.index(old)
        for new in CODEC_ALIASES.get(codec, ()):
            candidate = current[:start] + new + current[start + len(old):]
            for opt in pool:
                if opt.lower() == candidate.lower():
                    return opt
        break
    # No same-shape candidate — take any allowed value with the right codec.
    for opt in sorted(pool):
        if codec_of(opt) == codec:
            return opt
    return ""


def apply_output_format(workflow: dict, fmt: OutputFormat, value: str) -> None:
    node = workflow.get(fmt.node_id)
    if isinstance(node, dict) and isinstance(node.get("inputs"), dict):
        node["inputs"][fmt.key] = value


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
