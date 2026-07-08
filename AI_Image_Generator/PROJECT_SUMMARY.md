# AI Image Studio

**Version:** 3.1.0 | **Status:** Active | **Language:** Python

A four-tab PyQt6 desktop application for AI image generation via ComfyUI (local or RunPod serverless).

## Tabs

- **Text to Image**: Text-to-image generation using any ComfyUI `t2i_*.json` workflow. Supports size presets (512×512 through Super UltraWide), steps, seed, output folder, and a batch queue for running multiple prompts unattended.
- **Scene Composer**: Multi-reference-image composition. Drop up to 4 source images, describe the scene, and a ComfyUI `edit_*.json` workflow blends them together.
- **Variations**: Img2img — feed any image back in with a strength (denoise) slider and optional prompt using an `i2i_*.json` workflow. Low strength = subtle variation, high = mostly new image.
- **Library**: Scrollable thumbnail grid of all generated images from all output folders. Preview, favorite (★), filename filter + favorites-only filter, prompt recall, A/B compare, send-to-Variations, delete, open folder. Auto-refreshes on tab switch.

## Connection Modes (per tab)

- **Local ComfyUI** — default; connects to `http://127.0.0.1:8188` (or any URL)
- **RunPod Serverless** — enter your RunPod API key + endpoint ID; submits jobs via the RunPod async API and downloads base64-encoded results; images embedded in the request for Scene Composer

## Features

- Size presets covering square, portrait, landscape, Full HD, 2K, 4K, and ultrawide resolutions
- Dark purple theme (`#13131f` background, `#6c5ce7` accent)
- ComfyUI workflow JSON integration (auto-patches prompt, size, seed, steps, denoise, LoadImage nodes)
- Background generation thread — UI stays responsive during generation
- **Batch queue** (Text to Image): add multiple prompt jobs, run sequentially; failed jobs are skipped and counted, the queue continues
- **Generation history**: every generation records its prompt, workflow, size, steps, and resolved seed to `generation_history.json` (last 500); the Library shows the prompt for any selected image and **Recall Prompt** restores everything to the originating tab
- **Favorites**: star images in the Library (persisted in settings); gold ★ on cards and a favorites-only filter
- **A/B compare**: pick image A, pick image B, view side-by-side with dimensions/size/date captions
- Settings persisted to `settings.json`; API keys persisted to `api_keys.json` (gitignored)

## Tech Stack

- Python 3.10+
- PyQt6
- Pillow (image resizing + encoding for uploads)
- ComfyUI (local server) or RunPod serverless endpoint

## Files

```
AI_Image_Generator/
├── ai_image_generator.py       — Main application
├── Comfy_Workflows/            — ComfyUI workflow JSON files
│   ├── t2i_*.json              — Text-to-Image workflows
│   ├── edit_*.json             — Scene Composer workflows
│   └── i2i_*.json              — Variations (img2img) workflows
├── dropped_images/             — Drag-and-drop input staging (with archive/ subfolder)
├── upload_temp/                — Upload staging for local ComfyUI API
├── settings.json               — Persistent tab settings (gitignored)
├── generation_history.json     — Last 500 generations for prompt recall (gitignored)
└── api_keys.json               — RunPod API key (gitignored, never committed)
```

## Workflow File Naming Convention

| Prefix      | Tab             |
|-------------|-----------------|
| `t2i_*.json`  | Text to Image   |
| `edit_*.json` | Scene Composer  |
| `i2i_*.json`  | Variations      |

## Building

```bash
pyinstaller --onefile --windowed ai_image_generator.py
```

Output: `P:\Apps\VibeCoded\AI Image Studio\AI Image Studio.exe`

## Changelog

### v3.1.0 — 2026-07-07
- **Batch queue** (Text to Image): Add to Queue / Run Queue / remove / clear; jobs run sequentially with per-job status; failures are skipped and counted at the end
- **Generation history + prompt recall**: all three generating tabs log prompt/workflow/size/steps/resolved-seed per image to `generation_history.json`; Library shows the prompt and "↩ Recall Prompt" restores settings to the originating tab and switches to it
- **Variations tab** (img2img): new `i2i_*.json` workflow convention; source image slot (drag & drop or sent from Library), optional prompt, strength slider mapped to KSampler denoise (0.05–1.00), size/steps/seed, Local + RunPod support
- **Favorites in Library**: ☆/★ toggle button, gold star on thumbnail cards, "★ Favorites only" filter checkbox; persisted in settings
- **A/B compare in Library**: "⇆ Set A" then "⇆ Compare with A" opens a resizable side-by-side dialog with dimensions/file size/date under each image
- Library now also scans the Variations output folder; added "🔄 Variations" button to send any Library image to the Variations tab
- Random seeds are now resolved before submission so history records the actual seed used

### v3.0.2
- Fix preview panel cut off: lower left scroll area minimum width (370→280) so stretch ratio (1:2) can give preview adequate space
- Lower preview label minimum size (400×400→200×200) so it doesn't resist shrinking
- Lower window minimum size (1200×820→800×600) so Qt layout engine can apply stretch factors correctly at smaller sizes

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

## Future Enhancements

- [x] Generation history with prompt recall (click a Library image to restore its prompt/settings) — v3.1.0
- [x] Batch queue: line up multiple prompts and walk away — v3.1.0
- [x] Favorites/rating in the Library tab — v3.1.0 (favorite toggle; numeric rating not needed)
- [x] Img2img variations tab (feed a Library image back in with strength slider) — v3.1.0
- [x] Side-by-side A/B compare of two generations — v3.1.0
