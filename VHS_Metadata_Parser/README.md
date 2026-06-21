# VHS Metadata Parser

A desktop tool for parsing and inspecting ComfyUI workflow metadata embedded in video files and JSON exports. Drag and drop a file to view prompts, models, sampler settings, and the full workflow JSON.

## Features

- Supports `.mp4`, `.json`, and `.txt` metadata files
- Drag-and-drop or File > Open to load a file
- Tabbed interface:
  - **Video Settings** — resolution, frame rate, format, CRF, input images
  - **Prompts** — positive and negative prompt text
  - **Models** — CLIP, VAE, UNET (diffusion), and LoRA models
  - **Sampler** — KSampler steps, CFG, scheduler, seed, and shift settings
  - **Workflow** — full ComfyUI workflow JSON with copy-to-clipboard and save buttons
  - **Raw JSON** — complete raw metadata
- Copy workflow JSON to clipboard for reimporting into ComfyUI
- Packaged as a standalone Windows EXE

## Requirements

```
Python 3.x
PyQt5
```

```bash
pip install PyQt5
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
