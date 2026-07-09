# ComfyUI Workflow Chain Automator

Automates a chain of ComfyUI segments (up to 10), stitching the outputs into a single final video. Supports both local ComfyUI and RunPod deployments.

## Features

- Chains multiple ComfyUI workflow segments automatically
- Segment count driven by your workflow config — no hardcoded limits (max 10)
- **Batch mode**: run N images simultaneously — one model load per segment, N outputs (uses `LoadImageListFromDir //Inspire`)
- Dual workflow sets: `workflow_segment_XX_batch.json` in chain subfolder
- Split-pane UI: image browser (with sort) on the left, controls on the right
- Background image loading — UI appears instantly, thumbnails load progressively
- Persistent image thumbnail cache (`thumbnails` subfolder in the image folder, auto-synced) — large folders load in seconds; switching chain templates re-filters in place with no rescan
- 200px letterboxed thumbnails with black padding (no cropping)
- Starting image sort: Name A→Z / Z→A, Newest First, Oldest First
- Segment progress dots, per-segment timing, and live log
- **Live step progress** via ComfyUI websocket — progress bar advances with each sampler step and shows an ETA once a segment has completed (falls back to HTTP polling if the websocket is unavailable)
- Cancel interrupts the job on the ComfyUI server (no orphaned RunPod generations)
- Daily log file (`ComfyUI_Chain_Log_mm_dd_yyyy.txt`) written to final video folder — run separator, per-image list, segment times, zip info
- RunPod support — batch images uploaded via ComfyUI upload API, videos downloaded automatically
- FFmpeg local last-frame extraction (`-sseof -0.1`) for smooth segment transitions
- Final video stitched with FFmpeg and archived as a zip
- Built-in video player with playlist — plays all batch results back-to-back after completion
- Completion sound (optional, configurable in Settings)
- Library tab with video browser, sort options, multi-select, **Play Selected** playlist, and delete
- **Auto Run mode**: processes an entire folder of images automatically, N at a time, with no pop-ups between batches; configurable batch size; graceful **Stop After Batch** button

## Requirements

- Python 3.11+
- PyQt6
- requests
- websocket-client (live step progress; app falls back to polling without it)
- FFmpeg on PATH (or configured in Settings)

Install dependencies:
```
pip install PyQt6 requests websocket-client pyinstaller
```

## Usage

**Run from source:**
```
python main.py
```

**Standalone EXE** (built with PyInstaller):
```
dist\ComfyUI_Chain_Automator.exe
```

The EXE looks for `main_config.json` in the same folder as the executable.

## Configuration

Edit `main_config.json` or use the ⚙ Settings button in the app.

| Key | Description |
|-----|-------------|
| `comfyui_url` | Local ComfyUI server URL |
| `runpod_url` | RunPod proxy URL |
| `mode` | `local` or `runpod` |
| `input_dir` | Folder containing starting images |
| `workflow_dir` | Folder containing workflow JSON files |
| `workflows` | Array of segment definitions (see below) |
| `final_video_dir` | Output folder for stitched video |
| `zip_output_dir` | Output folder for zip archives |
| `ffmpeg_path` | Path to ffmpeg executable |
| `batch_dir_local` | Local folder for staging batch images (local mode) |
| `batch_dir_runpod` | RunPod path for batch output reference |
| `runpod_input_dir` | Absolute path to ComfyUI's input folder on RunPod |

### Workflow segment definition

```json
{
  "segment": 1,
  "json_file": "workflow_segment_01.json",
  "input_node_id": "97",
  "input_type": "image"
}
```

- `input_type`: `image` (segment 1) or `video` (segments 2+)
- `input_node_id`: The ComfyUI node ID that receives the input

## Building the EXE

```
python build_exe.py
```

Output: `dist\ComfyUI_Chain_Automator.exe`

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the full version history.
