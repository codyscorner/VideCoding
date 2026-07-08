# ComfyUI Style Randomizer

Batch-process a folder of images through a single ComfyUI i2i workflow, randomly assigning a style prompt from a curated list to each image. Mirrors the look and feel of the ComfyUI Chain Automator.

## Features

- Load thousands of images from an input folder with fast thumbnail preview (cached on first load)
- Maintain a prompt list of any size in a single `.txt` file — each prompt can span multiple lines
- Randomly assigns one prompt per image on every run
- Supports **Local** and **RunPod** ComfyUI endpoints
- Skip already-processed images (resume interrupted runs)
- **Processed filter** — hides already-done images by default; toggle **Show all** to see them with a green ✓ badge; remaining/done count shown after load
- **Library tab** — browse, view full-size, and delete output images; thumbnail cache makes reloads instant
- **Image viewer** — full screen toggle, slideshow mode (4 s auto-advance, spacebar to skip), keyboard ← → navigation, ESC to stop/exit
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

### v1.4.0
- **Prompt order modes** — dropdown in the bottom bar lets you choose how styles are assigned per image:
  - **Random** (default) — each image gets a randomly chosen style, no consecutive repeat in Auto Run
  - **Sequential** — styles assigned in order (1, 2, 3… cycling); Auto Run advances the cursor each batch
  - **Evens → Odds** — even-numbered styles run first (2, 4, 6…), then odd (1, 3, 5…); Auto Run follows the same sequence
- All three modes work in both regular Start and Auto Run

### v1.3.0
- **Auto Run mode** — process all images unattended N at a time: set batch size (1–50), click **▶▶ Auto Run**, and the app automatically selects the next batch and starts it when each batch finishes; processed images are removed from the grid between batches; **⏹ Stop After Batch** lets you halt after the current batch completes
- Auto Run is disabled when "Show all" is checked (no unprocessed images to iterate)
- **No-consecutive-repeat prompt selection** — in Auto Run mode, all images in a batch share one randomly chosen style; the next batch is guaranteed to pick a different style (with 2 prompts they strictly alternate; with N prompts the previous style is excluded from the next draw)
- Regular Start still randomizes a different style per image as before

### v1.2.1
- Version number now displayed in window title bar
- Log window clears automatically on each new Start

### v1.2.0
- **Thumbnail caching** — input folder and library both generate a `thumbnails/` cache on first load; subsequent loads are dramatically faster (especially for large folders)
- **Processed filter** — already-processed images hidden by default; **Show all** checkbox reveals them with a green ✓ badge; status bar shows "Remaining: X | Done: Y"
- **Image viewer** — full screen toggle, 4-second slideshow mode, keyboard ← → navigation, spacebar to skip during slideshow, ESC to stop/exit, end-of-slideshow slide
- Cancel now refreshes the input grid immediately

### v1.1.0
- Added **Library tab** — output image browser with sort, multi-select, full-size viewer (keyboard navigable), and delete
- Fixed Cancel button not re-enabling Start after cancellation

### v1.0.0
- Initial release: batch i2i processing with random prompt assignment, Local/RunPod support, skip-existing resume, in-app prompt editor

## Future Enhancements

- [ ] Per-image prompt override: click a thumbnail, pin a specific prompt
- [ ] Prompt weighting: mark some prompts as more likely
- [ ] "Re-roll" button on a finished image to re-run with a new random prompt
- [ ] Prompt-used metadata sidecar/CSV so you know which prompt made which output
