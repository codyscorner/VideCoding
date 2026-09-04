# VHS Metadata Parser

A desktop tool for parsing and inspecting ComfyUI workflow metadata embedded in video files and JSON exports. Drag and drop a file to view prompts, models, sampler settings, and the full workflow JSON.

## Features

- Supports `.mp4`, `.json`, and `.txt` metadata files
- Drag-and-drop or File > Open to load a file
- Tabbed interface:
  - **Video Settings** — resolution, frame count, duration, frame rate, format, CRF, audio, input images
  - **Prompts** — prompt sections table (shots, dialogue, camera, soundscape, music, JSON keys) plus raw positive / negative text
  - **Models** — CLIP, VAE, UNET (diffusion) / checkpoint, and LoRA models (any loader node)
  - **Sampler** — KSampler / SamplerCustomAdvanced steps, CFG, sampler, scheduler, seed, denoise, and model-sampling shift
  - **Other Settings** — every literal node input not shown on the tabs above (resolution selectors, save flags, turbo/LoRA options, custom nodes…)
  - **Workflow** — full ComfyUI workflow JSON with copy-to-clipboard and save buttons
  - **Raw JSON** — complete raw metadata
- Works with WAN 2.x and MiniMax H3 workflows; node links are resolved back to literal values
- Batch / Search tab: scan a folder, filter by LoRA / model / prompt text, diff two files, export CSV
- Copy workflow JSON to clipboard for reimporting into ComfyUI
- Packaged as a standalone Windows EXE

## Requirements

```
Python 3.x
PyQt6
```

```bash
pip install PyQt6
```

## Usage

```bash
python vhs_metadata_parser.py
```

1. Drag a ComfyUI output file (`.mp4`, `.json`, or `.txt`) onto the drop zone
2. Browse the tabs to inspect settings, prompts, and models
3. Use the **Workflow** tab to copy or save the workflow JSON for reuse in ComfyUI

Or run the standalone `dist/VHS_Metadata_Parser.exe` — no Python required.

## Build EXE

```bash
pip install pyinstaller
pyinstaller VHS_Metadata_Parser.spec
```
