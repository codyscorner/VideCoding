# AI Image Studio

**Version:** 3.0.1 | **Status:** Active | **Language:** Python

A three-tab PyQt6 desktop application for AI image generation via ComfyUI (local or RunPod serverless).

## Tabs

- **Text to Image**: Text-to-image generation using any ComfyUI `t2i_*.json` workflow. Supports size presets (512×512 through Super UltraWide), steps, seed, output folder.
- **Scene Composer**: Multi-reference-image composition. Drop up to 4 source images, describe the scene, and a ComfyUI `edit_*.json` workflow blends them together.
- **Library**: Scrollable thumbnail grid of all generated images from both output folders. Click to preview full size, delete, or open containing folder. Auto-refreshes on tab switch.

## Connection Modes (per tab)

- **Local ComfyUI** — default; connects to `http://127.0.0.1:8188` (or any URL)
- **RunPod Serverless** — enter your RunPod API key + endpoint ID; submits jobs via the RunPod async API and downloads base64-encoded results; images embedded in the request for Scene Composer

## Features

- Size presets covering square, portrait, landscape, Full HD, 2K, 4K, and ultrawide resolutions
- Dark purple theme (`#13131f` background, `#6c5ce7` accent)
- ComfyUI workflow JSON integration (auto-patches prompt, size, seed, steps, LoadImage nodes)
- Background generation thread — UI stays responsive during generation
- Settings persisted to `settings.json`; API keys persisted to `api_keys.json` (gitignored)

## Tech Stack

- Python 3.10+
- PyQt6
- Pillow (image resizing + encoding for uploads)
- ComfyUI (local server) or RunPod serverless endpoint

## Files

```
AI_Image_Generator/
├── ai_image_generator.py   — Main application
├── Comfy_Workflows/        — ComfyUI workflow JSON files
│   ├── t2i_*.json          — Text-to-Image workflows
│   └── edit_*.json         — Scene Composer workflows
├── dropped_images/         — Drag-and-drop input staging (with archive/ subfolder)
├── upload_temp/            — Upload staging for local ComfyUI API
├── settings.json           — Persistent tab settings
└── api_keys.json           — RunPod API key (gitignored, never committed)
```

## Workflow File Naming Convention

| Prefix      | Tab             |
|-------------|-----------------|
| `t2i_*.json`  | Text to Image   |
| `edit_*.json` | Scene Composer  |

## Building

```bash
pyinstaller --onefile --windowed ai_image_generator.py
```

Output: `P:\Apps\VibeCoded\AI Image Studio\AI Image Studio.exe`

## Changelog

### v3.0.1
- Fix Connection widget gap: replaced `QStackedWidget` with show/hide widgets so Local mode doesn't reserve RunPod's extra height
- Fix left panel clipping: wrap both tab left columns in `QScrollArea`
- Fix URL field: replaced `QTextEdit` (height-clipping) with `QLineEdit`
- Fix Scene Composer image slots: changed from 4-wide row to 2×2 grid to fit the narrower left panel

### v3.0.0
- Renamed "Image Editor" tab to "Scene Composer"
- Added `ConnectionWidget` per-tab: toggle between Local ComfyUI and RunPod Serverless
- Added `RunPodWorker` (async job submission + polling + base64 image decode)
- Added `RunPodEditorWorker` (embeds reference images as base64 for RunPod upload)
- Added **Library tab**: scrollable 4-column thumbnail grid, preview panel, delete, info
- Added `QLineEdit` stylesheet + scrollbar styling
- Version bump to 3.0.0

### v2.0.0
- Full rewrite; both tabs now ComfyUI API based; FLUX local diffusers removed
- Text to Image tab with workflow picker, size presets, steps, seed
- Image Editor tab with 4 reference image slots, drag & drop, EditorWorker

### v1.x
- Single-tab FLUX local diffusers app (deprecated)
