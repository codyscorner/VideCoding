"""
Format-aware model of a ComfyUI workflow JSON.

Two on-disk formats are handled:

* **API format** — ``{"<id>": {"class_type": ..., "inputs": {...}, "_meta": {...}}}``.
  Editable fields are the ``inputs`` whose values are scalars; a ``[node_id, slot]``
  list is a connection to another node.
* **UI / graph format** — ``{"nodes": [...], "links": [...], ...}`` as saved by the
  ComfyUI frontend. Widget values are positional in ``widgets_values`` with no field
  names, so names come from :data:`WIDGET_NAMES` for known node types and fall back
  to ``Value N``.

Everything the editor does not touch is passed through untouched on save.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

# ── categories ────────────────────────────────────────────────────────────────

CAT_PROMPT  = "Prompts"
CAT_LORA    = "LoRAs"
CAT_SAMPLER = "Sampling"
CAT_OUTPUT  = "Output"
CAT_LOADER  = "Loaders"
CAT_MEDIA   = "Image / Video / Latent"
CAT_OTHER   = "Other"
CAT_NOTES   = "Notes"

CATEGORY_ORDER = [CAT_PROMPT, CAT_LORA, CAT_SAMPLER, CAT_MEDIA, CAT_LOADER, CAT_OUTPUT, CAT_OTHER, CAT_NOTES]

# a node with a paragraph field by one of these names is a prompt node, whatever its type
PROMPT_KEYS = {"text", "prompt", "positive", "negative", "positive_prompt", "negative_prompt"}
_NOTE_TYPES = {"note", "markdownnote"}

# class types whose input is a float even when the JSON happens to hold a whole number
FLOAT_FIELDS_BY_TYPE: dict[str, set[str]] = {
    "PrimitiveFloat": {"value"},
    "FloatConstant":  {"value"},
}

_INT32_MAX = 2 ** 31 - 1

# ── choice lists for string fields ────────────────────────────────────────────

SAMPLER_NAMES = [
    "euler", "euler_cfg_pp", "euler_ancestral", "euler_ancestral_cfg_pp", "heun", "heunpp2",
    "dpm_2", "dpm_2_ancestral", "lms", "dpm_fast", "dpm_adaptive",
    "dpmpp_2s_ancestral", "dpmpp_2s_ancestral_cfg_pp", "dpmpp_sde", "dpmpp_sde_gpu",
    "dpmpp_2m", "dpmpp_2m_cfg_pp", "dpmpp_2m_sde", "dpmpp_2m_sde_gpu",
    "dpmpp_3m_sde", "dpmpp_3m_sde_gpu", "ddpm", "lcm", "ipndm", "ipndm_v", "deis",
    "res_multistep", "res_multistep_cfg_pp", "res_multistep_ancestral",
    "gradient_estimation", "er_sde", "seeds_2", "seeds_3", "sa_solver", "sa_solver_pece",
    "ddim", "uni_pc", "uni_pc_bh2",
]
SCHEDULER_NAMES = [
    "normal", "karras", "exponential", "sgm_uniform", "simple", "ddim_uniform",
    "beta", "linear_quadratic", "kl_optimal",
]

# field name -> choices.  Combos are editable, so a value outside the list is kept.
CHOICES: dict[str, list[str]] = {
    "sampler_name":               SAMPLER_NAMES,
    "scheduler":                  SCHEDULER_NAMES,
    "control_after_generate":     ["fixed", "increment", "decrement", "randomize"],
    "upscale_method":             ["nearest-exact", "bilinear", "area", "bicubic", "lanczos"],
    "weight_dtype":               ["default", "fp8_e4m3fn", "fp8_e4m3fn_fast", "fp8_e5m2"],
    "device":                     ["default", "cpu"],
    "add_noise":                  ["enable", "disable"],
    "return_with_leftover_noise": ["enable", "disable"],
    "crop":                       ["disabled", "center"],
    "keep_proportion":            ["stretch", "resize", "pad", "pad_edge", "crop"],
    "crop_position":              ["center", "top", "bottom", "left", "right"],
    "sort_method":                ["Alphabetical (ASC)", "Alphabetical (DESC)", "Numerical (ASC)", "Numerical (DESC)"],
}

# field names whose string value is a paragraph rather than a one-liner
MULTILINE_NAMES = {"text", "prompt", "positive", "negative", "expression", "string", "note", "value_text"}

# field names holding seeds (may exceed int32 → plain text editor, not QSpinBox)
SEED_NAMES = {"seed", "noise_seed"}

# ── positional widget names for the UI/graph format ───────────────────────────
# Order must match the node's widget order in the ComfyUI frontend.

WIDGET_NAMES: dict[str, list[str]] = {
    "CLIPTextEncode":          ["text"],
    "CLIPLoader":              ["clip_name", "type", "device"],
    "DualCLIPLoader":          ["clip_name1", "clip_name2", "type", "device"],
    "TripleCLIPLoader":        ["clip_name1", "clip_name2", "clip_name3"],
    "VAELoader":               ["vae_name"],
    "UNETLoader":              ["unet_name", "weight_dtype"],
    "CheckpointLoaderSimple":  ["ckpt_name"],
    "ControlNetLoader":        ["control_net_name"],
    "UpscaleModelLoader":      ["model_name"],
    "CLIPVisionLoader":        ["clip_name"],
    "CLIPSetLastLayer":        ["stop_at_clip_layer"],
    "LoraLoader":              ["lora_name", "strength_model", "strength_clip"],
    "LoraLoaderModelOnly":     ["lora_name", "strength_model"],
    "KSampler":                ["seed", "control_after_generate", "steps", "cfg", "sampler_name", "scheduler", "denoise"],
    "KSamplerAdvanced":        ["add_noise", "noise_seed", "control_after_generate", "steps", "cfg", "sampler_name",
                                "scheduler", "start_at_step", "end_at_step", "return_with_leftover_noise"],
    "KSamplerSelect":          ["sampler_name"],
    "SamplerCustom":           ["add_noise", "noise_seed", "control_after_generate", "cfg"],
    "BasicScheduler":          ["scheduler", "steps", "denoise"],
    "Flux2Scheduler":          ["steps", "width", "height"],
    "RandomNoise":             ["noise_seed", "control_after_generate"],
    "CFGGuider":               ["cfg"],
    "FluxGuidance":            ["guidance"],
    "ModelSamplingSD3":        ["shift"],
    "ModelSamplingAuraFlow":   ["shift"],
    "ModelSamplingFlux":       ["max_shift", "base_shift", "width", "height"],
    "EmptyLatentImage":        ["width", "height", "batch_size"],
    "EmptySD3LatentImage":     ["width", "height", "batch_size"],
    "EmptyFlux2LatentImage":   ["width", "height", "batch_size"],
    "EmptyHunyuanLatentVideo": ["width", "height", "length", "batch_size"],
    "WanImageToVideo":         ["width", "height", "length", "batch_size"],
    "WanVideoToVideo":         ["width", "height", "length", "batch_size"],
    "LoadImage":               ["image", "upload"],
    "LoadImageMask":           ["image", "channel", "upload"],
    "LoadVideo":               ["file", "upload"],
    "SaveImage":               ["filename_prefix"],
    "PreviewImage":            [],
    "SaveVideo":               ["filename_prefix", "format", "codec"],
    "CreateVideo":             ["fps"],
    "ImageScale":              ["upscale_method", "width", "height", "crop"],
    "ImageScaleBy":            ["upscale_method", "scale_by"],
    "ImageScaleToTotalPixels": ["upscale_method", "megapixels", "resolution_steps"],
    "LatentUpscale":           ["upscale_method", "width", "height", "crop"],
    "LatentUpscaleBy":         ["upscale_method", "scale_by"],
    "ImageResizeKJv2":         ["width", "height", "upscale_method", "keep_proportion", "pad_color",
                                "crop_position", "divisible_by", "device"],
    "PrimitiveInt":            ["value", "control_after_generate"],
    "PrimitiveFloat":          ["value"],
    "PrimitiveString":         ["value"],
    "PrimitiveStringMultiline": ["value"],
    "PrimitiveBoolean":        ["value"],
    "Note":                    ["text"],
    "MarkdownNote":            ["text"],
    "VHS_VideoCombine":        ["frame_rate", "loop_count", "filename_prefix", "format", "pix_fmt", "crf",
                                "save_metadata", "pingpong", "save_output"],
}
# rgthree's stack is lora_01, strength_01, lora_02, ... — generated on demand
_RGTHREE_STACK = "Lora Loader Stack (rgthree)"


# ── model ─────────────────────────────────────────────────────────────────────

@dataclass
class Field:
    """One editable value on a node, with a setter that writes back into the JSON."""
    key: str                      # input name (API) or widget name / "Value N" (UI)
    label: str
    value: Any
    kind: str                     # "bool" | "int" | "bigint" | "float" | "choice" | "text" | "line" | "readonly"
    choices: list[str] = field(default_factory=list)
    _setter: Callable[[Any], None] | None = None

    def apply(self, value: Any):
        if self._setter is not None:
            self._setter(value)


@dataclass
class Link:
    """A connection into a node, shown read-only."""
    name: str
    source: str   # human description of where it comes from


@dataclass
class NodeInfo:
    id: str
    class_type: str
    title: str
    category: str
    fields: list[Field]
    links: list[Link]
    mode: int = 0                 # UI format: 0 normal, 2 muted, 4 bypassed

    @property
    def state_badge(self) -> str:
        return {2: "MUTED", 4: "BYPASSED"}.get(self.mode, "")

    @property
    def is_negative_prompt(self) -> bool:
        t = self.title.lower()
        return self.category == CAT_PROMPT and ("neg" in t)


@dataclass
class WorkflowDoc:
    data: dict
    fmt: str                      # "api" | "ui"
    nodes: list[NodeInfo]

    @property
    def editable_field_count(self) -> int:
        return sum(1 for n in self.nodes for f in n.fields if f.kind != "readonly")


# ── public entry point ────────────────────────────────────────────────────────

def parse_workflow(data: Any) -> WorkflowDoc:
    """Build a :class:`WorkflowDoc` from parsed JSON, or raise ValueError."""
    if not isinstance(data, dict):
        raise ValueError("expected a JSON object at the top level")

    if isinstance(data.get("nodes"), list):
        nodes = _parse_ui(data)
        fmt = "ui"
    else:
        nodes = _parse_api(data)
        fmt = "api"

    if not nodes:
        raise ValueError("no ComfyUI nodes found — is this a workflow file?")

    nodes.sort(key=lambda n: (CATEGORY_ORDER.index(n.category), _id_sort_key(n.id)))
    return WorkflowDoc(data=data, fmt=fmt, nodes=nodes)


# ── API format ────────────────────────────────────────────────────────────────

def _parse_api(data: dict) -> list[NodeInfo]:
    raw = {k: v for k, v in data.items() if isinstance(v, dict) and "class_type" in v}
    titles = {nid: _api_title(nid, node) for nid, node in raw.items()}
    result = []
    for nid, node in raw.items():
        ctype = str(node.get("class_type", ""))
        inputs = node.get("inputs")
        if not isinstance(inputs, dict):
            inputs = node["inputs"] = {}
        fields, links = [], []
        for key, value in inputs.items():
            if _is_api_link(value):
                src_id = str(value[0])
                links.append(Link(key, f"{titles.get(src_id, 'node ' + src_id)} [{src_id}]"))
                continue
            fields.append(_make_field(key, value, _api_setter(inputs, key), ctype=ctype))
        result.append(NodeInfo(
            id=nid, class_type=ctype, title=titles[nid],
            category=_category_for(ctype, titles[nid], fields),
            fields=fields, links=links,
        ))
    return result


def _api_title(nid: str, node: dict) -> str:
    meta = node.get("_meta")
    if isinstance(meta, dict) and meta.get("title"):
        return str(meta["title"])
    return str(node.get("class_type", f"Node {nid}"))


def _is_api_link(value: Any) -> bool:
    return isinstance(value, list) and len(value) == 2 and isinstance(value[1], int)


def _api_setter(inputs: dict, key: str) -> Callable[[Any], None]:
    def _set(v):
        inputs[key] = v
    return _set


# ── UI / graph format ─────────────────────────────────────────────────────────

def _parse_ui(data: dict) -> list[NodeInfo]:
    raw_nodes = [n for n in data["nodes"] if isinstance(n, dict)]
    titles = {str(n.get("id")): _ui_title(n) for n in raw_nodes}

    # link id -> (source node id, source slot)
    link_src: dict[int, tuple[str, int]] = {}
    for ln in data.get("links", []):
        if isinstance(ln, list) and len(ln) >= 3:
            link_src[ln[0]] = (str(ln[1]), ln[2])
        elif isinstance(ln, dict) and "id" in ln:
            link_src[ln["id"]] = (str(ln.get("origin_id")), ln.get("origin_slot", 0))

    result = []
    for node in raw_nodes:
        nid = str(node.get("id"))
        ctype = str(node.get("type", ""))
        title = titles[nid]
        mode = int(node.get("mode", 0) or 0)

        # inputs that are wired up; widget-backed ones also tell us the field is linked
        links, linked_widgets = [], set()
        for inp in node.get("inputs", []) or []:
            if not isinstance(inp, dict) or inp.get("link") is None:
                continue
            src = link_src.get(inp["link"])
            src_desc = f"{titles.get(src[0], 'node ' + src[0])} [{src[0]}]" if src else "linked"
            links.append(Link(str(inp.get("name", "?")), src_desc))
            widget = inp.get("widget")
            if isinstance(widget, dict) and widget.get("name"):
                linked_widgets.add(widget["name"])

        fields = _ui_fields(node, ctype, linked_widgets)
        result.append(NodeInfo(
            id=nid, class_type=ctype, title=title,
            category=_category_for(ctype, title, fields),
            fields=fields, links=links, mode=mode,
        ))
    return result


def _ui_title(node: dict) -> str:
    return str(node.get("title") or node.get("type") or f"Node {node.get('id')}")


def _ui_fields(node: dict, ctype: str, linked: set[str]) -> list[Field]:
    wv = node.get("widgets_values")
    fields: list[Field] = []

    if isinstance(wv, dict):
        # e.g. VHS_VideoCombine stores a dict keyed by widget name
        for key, value in wv.items():
            if key == "videopreview" or isinstance(value, (dict, list)):
                continue
            fields.append(_make_field(key, value, _dict_setter(wv, key), readonly=key in linked, ctype=ctype))
        return fields

    if not isinstance(wv, list):
        return fields

    names = _widget_names_for(ctype, len(wv))
    for idx, value in enumerate(wv):
        key = names[idx] if idx < len(names) else f"Value {idx + 1}"
        if isinstance(value, (dict, list)):
            continue
        fields.append(_make_field(key, value, _list_setter(wv, idx), readonly=key in linked, ctype=ctype))
    return fields


def _widget_names_for(ctype: str, count: int) -> list[str]:
    if ctype == _RGTHREE_STACK:
        names = []
        for i in range(1, count // 2 + 2):
            names += [f"lora_{i:02d}", f"strength_{i:02d}"]
        return names
    return WIDGET_NAMES.get(ctype, [])


def _dict_setter(target: dict, key: str) -> Callable[[Any], None]:
    def _set(v):
        target[key] = v
    return _set


def _list_setter(target: list, idx: int) -> Callable[[Any], None]:
    def _set(v):
        target[idx] = v
    return _set


# ── field construction ────────────────────────────────────────────────────────

def _make_field(key: str, value: Any, setter: Callable[[Any], None],
                readonly: bool = False, ctype: str = "") -> Field:
    label = _humanize(key)
    if readonly:
        return Field(key, label, value, "readonly", _setter=setter)

    lkey = key.lower()
    if isinstance(value, bool):
        kind = "bool"
    elif isinstance(value, int):
        if lkey in SEED_NAMES or abs(value) > _INT32_MAX:
            kind = "bigint"
        elif known_float_field(key) or key in FLOAT_FIELDS_BY_TYPE.get(ctype, ()):
            # JSON drops the ".0" from whole floats (cfg: 1, denoise: 1) — still a float field
            kind = "float"
        else:
            kind = "int"
    elif isinstance(value, float):
        kind = "float"
    elif isinstance(value, str):
        if key in CHOICES:
            kind = "choice"
        elif lkey in MULTILINE_NAMES or "\n" in value or len(value) > 100:
            kind = "text"
        else:
            kind = "line"
    elif value is None:
        kind = "readonly"
    else:
        kind = "readonly"

    return Field(key, label, value, kind, choices=list(CHOICES.get(key, [])), _setter=setter)


def _humanize(key: str) -> str:
    if key.startswith("Value "):
        return key
    words = key.replace("_", " ").replace(".", " › ").strip()
    return words[:1].upper() + words[1:] if words else key


# ── categorisation ────────────────────────────────────────────────────────────

def _category_for(ctype: str, title: str, fields: list[Field]) -> str:
    c = ctype.lower()
    t = title.lower()
    if c in _NOTE_TYPES:
        return CAT_NOTES
    if "textencode" in c or "prompt" in t:
        return CAT_PROMPT
    if any(f.kind == "text" and f.key.lower() in PROMPT_KEYS for f in fields):
        return CAT_PROMPT
    if "lora" in c:
        return CAT_LORA
    if any(k in c for k in ("sampler", "scheduler", "guider", "guidance", "noise", "modelsampling", "cfg")):
        return CAT_SAMPLER
    if any(k in c for k in ("save", "videocombine", "createvideo", "preview")):
        return CAT_OUTPUT
    if any(k in c for k in ("loader", "checkpoint")):
        return CAT_LOADER
    if any(k in c for k in ("image", "video", "latent", "resize", "scale", "vae")):
        return CAT_MEDIA
    return CAT_OTHER


def _id_sort_key(nid: str):
    # "238:227" → (238, 227); "60" → (60,); non-numeric stays stable at the end
    parts = []
    for p in nid.split(":"):
        parts.append(int(p) if re.fullmatch(r"-?\d+", p) else 10 ** 9)
    return tuple(parts)


# ── numeric hints for editors ─────────────────────────────────────────────────

_DEFAULT_HINT = (-1e9, 1e9, 1, 3)


def _known_hint(key: str) -> tuple[float, float, float, int] | None:
    """Range/step/decimals for field names we recognise; None for anything else."""
    k = key.lower()
    if k == "steps" or k.endswith("_step") or k.endswith("_steps"):
        return 0, 10000, 1, 0
    if k in ("cfg", "guidance"):
        return 0, 100, 0.5, 2
    if k == "denoise":
        return 0, 1, 0.05, 2
    if k.startswith("strength") or k in ("scale_by",):
        return -10, 10, 0.05, 2
    if k in ("width", "height"):
        return 0, 16384, 8, 0
    if k in ("length", "frames", "frame_count", "batch_size", "fps", "frame_rate"):
        return 0, 100000, 1, 0
    if "shift" in k:
        return 0, 100, 0.1, 2
    if k == "megapixels":
        return 0, 64, 0.1, 2
    if k == "crf":
        return 0, 63, 1, 0
    return None


def number_hint(key: str) -> tuple[float, float, float, int]:
    """(minimum, maximum, single step, decimals) for a numeric field, by name."""
    return _known_hint(key) or _DEFAULT_HINT


def known_float_field(key: str) -> bool:
    """True when the name alone tells us this is a float (cfg, denoise, strength…)."""
    hint = _known_hint(key)
    return hint is not None and hint[3] > 0
