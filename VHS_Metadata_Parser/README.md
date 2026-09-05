# VHS Metadata Parser

A desktop tool for parsing and inspecting ComfyUI workflow metadata embedded in video files and JSON exports. Drag and drop a file to view prompts, models, sampler settings, and the full workflow JSON.

**Current version: 1.3.1**

## Features

- Supports `.mp4`, `.json`, and `.txt` metadata files
- Drag-and-drop or File > Open to load a file
- Tabbed interface:
  - **Video Settings** — resolution, frame count, duration, frame rate, format, CRF, audio, input images
  - **Prompts** — Prompt Sections table splitting each prompt into readable parts (shots, dialogue, camera, soundscape, music, JSON keys, with source node shown) plus raw positive / negative text
  - **Models** — CLIP, VAE, UNET (diffusion) / checkpoint, and LoRA models (any loader node)
  - **Sampler** — KSampler / SamplerCustomAdvanced steps, CFG, sampler, scheduler, seed, denoise, and model-sampling shift
  - **Other Settings** — every literal node input not shown on the tabs above (resolution selectors, save flags, turbo/LoRA options, custom nodes…), with a filter box and a link-only toggle
  - **Workflow** — full ComfyUI workflow JSON with copy-to-clipboard and save-to-file buttons
  - **Raw JSON** — complete raw metadata
- Works with WAN 2.x and MiniMax H3 workflows; node links are resolved back to literal values (primitives, same-named inputs, whitelisted `ComfyMathExpression` evaluation)
- **Batch / Search tab**: scan a folder (optionally recursive), live-filter the summary table by filename, LoRA/model name, sampler, or prompt text, diff two rows side by side with differing fields highlighted, double-click a row to load it into the main viewer, export the batch summary to CSV
- Export Models, Sampler & Other Settings to CSV for the currently loaded file
- Copy workflow JSON to clipboard for reimporting into ComfyUI
- Dark blue-green theme
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

## Recent Changes

Full history in [CHANGELOG.md](CHANGELOG.md).

- **1.3.1** — rebuild release shipping the v1.3.0 fixes (MP4-header dimension fallback, layout fixes, `run.bat`, optional CLI file argument)
- **1.3.0** — MiniMax H3 workflow support, generic link resolution, Prompt Sections table, Other Settings tab
- **1.2.0** — Batch / Search tab with live filter, diff view, CSV export
- **1.1.0** — migrated from PyQt5 to PyQt6, dark blue-green theme
- **1.0.0** — initial release
