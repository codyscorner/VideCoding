# ComfyUI Workflow Chain Automator

Automates a chain of ComfyUI segments (up to 10), stitching the outputs into a single final video. Supports both local ComfyUI and RunPod deployments.

## Features

- Chains multiple ComfyUI workflow segments automatically
- Segment count driven by your workflow config — no hardcoded limits (max 10)
- **Batch mode**: run N images simultaneously — one model load per segment, N outputs (uses `LoadImageListFromDir //Inspire`)
- Dual workflow sets: `workflow_segment_XX_batch.json` in chain subfolder
- Split-pane UI: image browser (with sort) on the left, controls on the right
- Background image loading — UI appears instantly, thumbnails load progressively
- 200px letterboxed thumbnails with black padding (no cropping)
- Starting image sort: Name A→Z / Z→A, Newest First, Oldest First
- Segment progress dots, per-segment timing, and live log
- Daily log file (`ComfyUI_Chain_Log_mm_dd_yyyy.txt`) written to final video folder — run separator, per-image list, segment times, zip info
- RunPod support — batch images uploaded via ComfyUI upload API, videos downloaded automatically
- FFmpeg local last-frame extraction (`-sseof -0.1`) for smooth segment transitions
- Final video stitched with FFmpeg and archived as a zip
- Built-in video player with playlist — plays all batch results back-to-back after completion
- Completion sound (optional, configurable in Settings)
- Library tab with video browser, sort options, and delete

## Requirements

- Python 3.11+
- PyQt6
- requests
- FFmpeg on PATH (or configured in Settings)

Install dependencies:
```
pip install PyQt6 requests pyinstaller
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

### v3.0.0
- Starting Images sort combo: Name A→Z, Name Z→A, Newest First, Oldest First
- Daily log file: `ComfyUI_Chain_Log_mm_dd_yyyy.txt` written to final video folder each run
  - 80-char separator header between runs with date/time and image count
  - Each starting image listed on its own line
  - Logs segment times, zip archive names, total time; filters out poll-noise lines
- Unified all naming to "ComfyUI Workflow Chain Automator" / `ComfyUI_Chain_Automator`
- Source folder renamed from `CumfyUI_API` to `ComfyUI_Chain_Automator`

### v2.9.0
- Completion sound: optional audio cue on batch finish (configurable in Settings)
- Fix: total batch elapsed time now reflects full run including stitching

### v2.7.4
- Smart same-stem image filtering: images sharing a stem with an existing video are excluded from the Starting Images grid

### v2.7.3
- Auto-number output filename on collision (e.g. `photo_1.mp4`) to prevent overwriting

### v2.7.2
- Fix output filename collision when multiple images share the same stem

### v2.7.1
- Fix playlist not advancing correctly in batch playback
- Batch-only cleanup: removed unused single-mode code paths

### v2.7.0
- Batch-only mode: removed single/batch toggle — all runs are batch mode
- Chain folder dropdown: auto-detects segment count from `*_batch.json` files in selected folder

### v2.6.1
- Log: total batch elapsed time printed as final log line after stitching completes
- Log: append mode with rolling 50-batch history — older runs automatically trimmed on each new run

### v2.6.0
- Batch mode: Single/Batch toggle in UI; batch runs N images through all 7 segments in one pass using `LoadImageListFromDir //Inspire`
- Dual workflow sets: `workflow_segment_XX_batch.json` files in `{Chain}_Batch/` subfolder keep single and batch workflows separate
- RunPod batch upload: images uploaded directly into ComfyUI's input directory per segment via upload API
- FFmpeg local frame extraction with `-sseof -0.1` for smooth segment transitions (no full video upload between segments)
- Playlist video player: after batch completes, prompts to play all results back-to-back with ⏮⏭ navigation and auto-advance
- Settings: Batch Processing section with local dir, RunPod dir, and RunPod input dir fields
- Poll loop error detection: surfaces ComfyUI execution errors immediately instead of looping silently

### v2.5.1
- Fix: chain folder not persisted on startup when `active_chain_folder` was absent from config, causing worker to load workflows from root instead of selected subfolder
- Fix: segment dot double-click editor built wrong path when a chain folder was active

### v2.5.0
- Generate tab: IMG_* workflow picker, positive/negative prompts, seed control, two drag-and-drop reference image slots, gallery with Send to Chain / Delete / Clear buttons, Generate and Generate+Run Chain one-shot modes
- Chain tab: filtered image grid hides images that already have a video (Show all toggle), Chain folder dropdown lists Video_* subfolders, segment count auto-detected from folder contents
- Library tab: Delete button with confirmation to remove bad videos without leaving the app
- Worker: loads workflow JSON from the selected chain folder; node ID template falls back for extra segments

### v2.4.0
- Chain folder dropdown: select Video_* workflow folders; segment count auto-detected from workflow_segment_*.json files inside the folder
- Filtered image grid: hides images whose stem matches an existing library video

### v2.1.0
- Background image loading — window appears instantly, grid fills progressively
- Progress bar shows image loading status with count

### v2.0.0
- Split-pane layout: image grid left, controls right (1600×760 default)
- Thumbnails enlarged to 200px with black letterbox padding
- Segment count is dynamic — reads from workflow config, no hardcoded value
- Worker log messages use actual segment count
- Selection shown as accent border (no background fill)
- Scrollbar padding fix

### v1.1.0
- RunPod support
- EXE build via PyInstaller

### v1.0.0
- Initial release: 7-segment local chain automator
