# ComfyUI Video Creator

Version: 1.4.1

Single-shot ComfyUI API workflow runner with a dark red theme. Pick an image (or a video to extend), pick a workflow JSON, press Run, and the finished video lands in a local folder — from a local ComfyUI or a RunPod pod.

This is a **separate app from the ComfyUI Workflow Chain Automator**. It shares no code with it, so changes to one never affect the other.

## Features

- **Image → Video tab** — thumbnail grid of a chosen image folder (sort by name/date; thumbnails cached in `<folder>/thumbnails`), workflow dropdown, prompt editor, Run
- **Video → Extend tab** — thumbnail grid of a chosen video folder. The selected video feeds the workflow as either:
  - its **last frame** (extracted with ffmpeg) into a `LoadImage` node or a folder loader — works with any image-to-video workflow, or
  - the **whole file** into a `LoadVideo` / `VHS_LoadVideo` node (MiniMax H3 reference workflows etc.)

  Auto-detected from the workflow, with a manual override. Optionally the new clip is **appended to the source video** (`<name>_extended_<stamp>.mp4`). With Append ticked the clip is generated at the source video's own frame size, and the workflow about to run is retuned to save in the source's codec (`video/h265-mp4` → `video/h264-mp4`, checked against the server's own option list; the file on disk is untouched), and the stitch normalizes size, fps, SAR, pixel format and audio format for both parts — a clip of a different shape is padded, never stretched, and a silent clip gets matching silence rather than muting the whole file
- **Delete from the grid** — every thumbnail browser can delete: the 🗑 button in the folder row, right-click → Delete, or the Del key. Files (and their cached thumbnails) go to the **Recycle Bin**, so a bad generation is one click away from gone without opening Explorer. A file the built-in player is showing is closed first, then deleted
- **Workflow dropdown** — every API-format `.json` under the Workflows folder (subfolders included). **Type any part of a name to filter it** — matching runs anywhere in the relative path, not just from the start, so `makeout` narrows 77 workflows to 2. Batch-style workflows using `LoadImageListFromDir //Inspire` also work: the single image is staged into a fresh run folder and the loader pointed at it
- **⧉ Clone workflow** — copy the selected workflow to a new name (and any subfolder) and switch to the copy, so you can experiment without touching a workflow that already works. Optionally seeds the clone with the prompts, LoRAs and settings currently on screen, and optionally copies its prompt history
- **Prompt editor** built from the workflow (CLIPTextEncode positive/negative, MiniMax H3 prompt, PrimitiveStringMultiline); edits apply per run, or "Save to workflow" writes them into the JSON. Each prompt has an **⤢ Expand** button for a large separate editor window, and the Prompts / Options split is draggable
- **LoRA picker** — one row per LoRA node in the workflow (`LoraLoaderModelOnly`, rgthree `Lora Loader Stack`, `MiniMaxH3TurboLoRA`…): editable dropdown of LoRA files from your LoRAs folder (or fetched from the connected server with ⇣ Server) plus strength spinner(s). A "Next run →" line always shows the LoRAs, seed and length about to be used
- **Prompt history with settings** — every run appends prompts + seed + length + LoRAs/strengths + mode + source to the workflow's `<name>.prompt_history.json` (shared with the Chain Automator) and attaches the result file name when done. 📜 History searches entries and reloads the prompt alone or prompt + settings
- **Seed** random-per-run or fixed; **Steps** applied to every sampler node (WAN hi/lo splits rescaled proportionally); **Megapixels** applied to every `megapixels` input (`ImageScaleToTotalPixels` etc.); **Length / Duration** control when the workflow exposes one
- Extend-tab thumbnails show each video's **last frame**, the extension's starting point
- **Library tab** — finished videos (Output folder by default): sort, multi-select, Play (playlist), Delete, Open Folder, **Send to Extend**, and a *Produced by* pane with the prompt/LoRAs/seed/length behind the selected video (from the prompt history)
- **Local or RunPod** server with separate URLs, "Test connection", and automatic download of the result to the Output folder
- Live step progress over the ComfyUI websocket (polling fallback), Cancel that interrupts the server, built-in video player, run log

## Requirements

- Python 3.11+
- PyQt6, requests, websocket-client, Pillow
- ffmpeg — configured in Settings, or an `ffmpeg.exe` next to the EXE, or on PATH

```
pip install PyQt6 requests websocket-client pillow pyinstaller
```

## Usage

**From source:** `run.bat` (or `python main.py`)

**EXE:** `P:\Apps\VibeCoded\ComfyUI Video Creator\ComfyUI_Video_Creator.exe`

1. ⚙ Settings → choose Local/RunPod and the URL, set the Images, Videos, Workflows and Output folders, press *Test connection*.
2. Image → Video: click an image, pick a workflow, adjust the prompt/seed/length, **Create Video**.
3. Video → Extend: click a video, pick a workflow, choose the input mode (Auto is fine), tick *Append the new clip*, **Extend Video**.
4. Results appear in the Results list — double-click to play, or Open Folder.
5. Library: review everything in the Output folder, play a selection back-to-back, delete misses, or send a clip back to Extend.

## Configuration

`video_creator_config.json` sits next to the EXE (next to `main.py` from source) and is written by the Settings dialog.

| Key | Description |
|-----|-------------|
| `mode` | `local` or `runpod` |
| `comfyui_url` / `runpod_url` | Server URL for each mode |
| `image_dir` / `video_dir` | Folders shown on the two tabs |
| `workflow_dir` | Folder scanned (recursively) for workflow `.json` files |
| `output_dir` | Where finished videos are downloaded |
| `loras_dir` | ComfyUI `models/loras` folder that fills the LoRA dropdowns |
| `library_dir` | Folder shown on the Library tab (blank = the Output folder) |
| `staging_dir_local` | Local folder for staging an image for folder-loader workflows (blank = app `temp`) |
| `runpod_input_dir` | Absolute path of ComfyUI's `input` folder on the pod (folder-loader workflows) |
| `ffmpeg_path` | Optional explicit ffmpeg path |
| `video_input_mode` | `auto`, `last_frame` or `upload_video` |
| `extend_stitch` | Append the new clip to the source video |

Workflows must be **API exports** (Workflow > Export (API) in ComfyUI); the normal UI save format is rejected with a message.

## Output naming

`<source stem>_<workflow>_<YYYYMMDD_HHMMSS>.mp4` — `<workflow>` is the workflow's subfolder name when it lives in one, otherwise the file stem. A clip made on the Video → Extend tab carries `_EXT` just before the timestamp (`<stem>_<workflow>_EXT_<stamp>.mp4`) so extensions stand out in the output folder. Stitched extensions are `<source stem>_extended_<stamp>.mp4`. When the source is a video the app first strips the workflow label and timestamp an earlier run appended, so a chain of extensions keeps one stable base name instead of growing by ~50 characters a pass; names this app didn't write (a camera-style `IMG_20260101_120000.mp4`) are left alone. Every name is capped to keep the full path under 250 characters.

## Building the EXE

```
build.bat
```

Builds with the repo `.venv`, deploys `ComfyUI_Video_Creator.exe`, `app_icon.ico` and `ffmpeg.exe` to `P:\Apps\VibeCoded\ComfyUI Video Creator\` and refreshes the Start Menu shortcuts. Bump `VERSION` in `main.py` (and this README + CHANGELOG) before every build.

## Project layout

| File | Purpose |
|------|---------|
| `main.py` | Entry point, version, icon/config discovery |
| `config.py` | Portable config next to the EXE |
| `workflow_tools.py` | Load/validate API workflows, detect input/prompt/seed/length/output nodes, patch them |
| `comfy_client.py` | Upload, queue, websocket/poll wait, history, download, interrupt |
| `run_worker.py` | Background thread for one run: feed source → queue → wait → download → optional stitch |
| `media_tools.py` | ffmpeg discovery, last frame, thumbnails, probe, concat |
| `file_ops.py` | Recycle-Bin delete (shell `SHFileOperation`) + thumbnail-cache cleanup |
| `ui/` | Dark red theme, thumbnail browsers, run panel, clone dialog, settings dialog, video player, main window |

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
