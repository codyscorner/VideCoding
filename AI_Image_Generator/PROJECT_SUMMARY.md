# AI Image Studio

**Version:** 2.0.0 | **Status:** Active | **Language:** Python

A two-tab PyQt6 desktop application for AI image generation via ComfyUI.

## Tabs

- **FLUX Tab**: Text-to-image generation using FLUX models via a local ComfyUI instance. Supports size presets (512×512 through 4K UHD and ultrawide), aspect ratio selection, and drag-and-drop workflow JSON loading.
- **Scene Composer**: Planned tab for composing multi-element scenes (in progress — requires ComfyUI API rewrite).

## Features

- Size presets covering square, portrait, landscape, Full HD, 2K, 4K, and ultrawide resolutions
- Aspect ratio picker (1:1, 16:9, 9:16, 4:3, 3:4, etc.)
- Resolution tiers: 1K, 2K, 4K
- Dark purple theme (`#13131f` background, `#6c5ce7` accent)
- ComfyUI workflow JSON integration
- Background generation thread — UI stays responsive

## Tech Stack

- Python 3.10+
- PyQt6
- ComfyUI (local server)

## Files

```
AI_Image_Generator/
├── ai_image_generator.py   — Main application
├── Comfy_Workflows/        — ComfyUI workflow JSON files
├── dropped_images/         — Drag-and-drop input staging
├── upload_temp/            — Upload staging for ComfyUI API
└── settings.json           — Persistent settings
```

## Building

```bash
pyinstaller --onefile --windowed ai_image_generator.py
```
