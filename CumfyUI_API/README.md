# ComfyUI Workflow Chain Automator

Automates a chain of ComfyUI segments (up to 10), stitching the outputs into a single final video. Supports both local ComfyUI and RunPod deployments.

## Features

- Chains multiple ComfyUI workflow segments automatically
- Segment count driven by your workflow config — no hardcoded limits (max 10)
- Split-pane UI: image browser on the left, controls on the right
- Background image loading — UI appears instantly, thumbnails load progressively
- 200px letterboxed thumbnails with black padding (no cropping)
- Segment progress dots, per-segment timing, and live log
- RunPod support with automatic image/video upload
- Final video stitched with FFmpeg and archived as a zip

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
