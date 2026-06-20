# ComfyUI Style Randomizer

Batch-process a folder of images through a single ComfyUI i2i workflow, randomly assigning a style prompt from a curated list to each image. Mirrors the look and feel of the ComfyUI Chain Automator.

## Features

- Load thousands of images from an input folder with thumbnail preview
- Maintain a prompt list of any size in a single `.txt` file — each prompt can span multiple lines
- Randomly assigns one prompt per image on every run
- Supports **Local** and **RunPod** ComfyUI endpoints
- Skip already-processed images (resume interrupted runs)
- **Library tab** — browse, view full-size, and delete output images
- Auto-detects workflow nodes: `LoadImage`, `PrimitiveStringMultiline`, `CLIPTextEncode`, `KSampler`
- Dark theme UI consistent with the Chain Automator

## Prompt File Format

Use a single `.txt` file with prompts separated by `---- PROMPT START -----` on its own line. Each prompt can span multiple lines for better readability:

```
---- PROMPT START -----
photorealistic portrait, golden hour lighting,
shallow depth of field, cinematic grade

---- PROMPT START -----
oil painting style, impressionist brushstrokes,
vibrant palette, textured canvas

---- PROMPT START -----
cyberpunk neon, dark city background, glowing edges
```

Click **Edit** next to the Prompts File field to open the built-in editor. It shows a live count of detected prompts as you type.

## Usage

1. Run `ComfyUI_Style_Randomizer.exe` (or `python main.py`)
2. Set **Input Folder** → folder containing your source images
3. Set **Output Folder** → where styled images will be saved
4. Set **Workflow JSON** → your ComfyUI i2i workflow exported as API JSON
5. Set **Prompts File** → your `.txt` file of style prompts
6. Optionally enable **Skip already-processed images** for resume support
7. Click **Start** — each image gets a randomly chosen style; the log shows which prompt was picked

### Local vs RunPod

Click **⚙ Settings** to toggle between Local (default `http://127.0.0.1:8000`) and RunPod mode. In RunPod mode, paste your pod proxy URL (e.g. `https://YOUR-POD-ID-8000.proxy.runpod.net/`). The active URL is always shown in the status bar.

### Library Tab

Click **🖼 Library** to browse your output images:
- **Sort** by newest, oldest, name, or file size
- **Double-click** any thumbnail to open the full-size viewer with keyboard navigation (← →)
- **Ctrl+click / Shift+click** to select multiple images
- **👁 View** — open selected images in the viewer
- **🗑 Delete** — permanently delete selected images (confirmation required)
- **↻ Refresh** — reload after a batch finishes

## Workflow Requirements

Your ComfyUI workflow must be exported in **API format** (enable Dev Mode in ComfyUI → Export API). The app auto-detects:

| Node | What gets patched |
|------|-------------------|
| `LoadImage` | Injected with the current source image |
| `PrimitiveStringMultiline` or first non-negative `CLIPTextEncode` | Injected with the randomly chosen style prompt |
| `KSampler` / any node with `seed` or `noise_seed` | Randomized each image |

## Changelog

### v1.1.0
- Added **Library tab** — output image browser with sort, multi-select, full-size viewer (keyboard navigable), and delete
- Fixed Cancel button not re-enabling Start after cancellation

### v1.0.0
- Initial release: batch i2i processing with random prompt assignment, Local/RunPod support, skip-existing resume, in-app prompt editor
