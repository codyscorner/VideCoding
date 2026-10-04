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
- **RunPod pod control** — Start / Stop Pod button and live spend readout in the header, launch chooser, priority-ordered pod list with GPU ranking, spend limit, idle stop, keep-trying retry and an alert sound (see below)
- **Model check & sync** — before a RunPod run, every model/LoRA file the workflow names is looked for locally and on the pod volume; missing files are uploaded/downloaded and verified first
- **Stops on ComfyUI errors** — a missing model, rejected workflow or failed generation stops the run with the reason instead of grinding through every image
- **Prompt tooltips** — hover any style prompt in the list to read its full text
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

## RunPod Pod Control

Wakes one of your **existing** RunPod pods from inside the app (it never creates or terminates pods). Same feature, and the same code, as the ComfyUI Video Creator and Chain Automator.

- **On launch** the app shows any pod that is already running (use it / start another / stop it) or offers to start one. Turn this off with *Settings > RunPod > Ask on launch*.
- **Start Pod** walks your priority-ordered pod list (GPU model first, then pod order) and uses the first healthy pod; zero-GPU resumes are detected and skipped. The RunPod URL and mode are written for you.
- **Header readout** shows what the pod has cost this session; an optional **spend limit** stops the pod once the current run finishes, and **idle stop** stops it N minutes after the last run.
- **Keep trying** re-sweeps the list every N minutes when every pod is busy; the **alert sound** plays when a pod is found, when it gives up, and when a run finishes.
- **On quit** you are asked whether to stop the connected pod.
- The API key is read from `RUNPOD_API_KEY` or `api_keys.json` (`{"runpod_api_key": "..."}`) next to the EXE — never from the config file. `api_keys.json` is gitignored.

## Model Check & Sync

On a RunPod run the app reads the workflow, finds every model file it names (checkpoints, diffusion models, VAEs, text encoders, CLIP vision, upscalers, ControlNets, LoRAs) and compares your local ComfyUI `models` folder with the pod's network volume through RunPod's S3 API:

- on your PC but not on the pod → uploaded to the matching folder on the volume
- on the pod but not on your PC → a **Model missing locally** box names the file and size, says the pod run can start without it, and offers **Download, then run** (only needed to run the workflow on local ComfyUI — the Flux2 text encoder alone is 35 GB) or **Run on the pod without downloading**; Settings > Models can make the download automatic. The progress dialog shows direction, destination, MB/s and time left
- nowhere → listed, and you choose whether to run anyway
- sizes are verified after every transfer; files whose size differs between the two sides are reported, never overwritten
- Cancel in the progress dialog aborts the file in flight (v1.8.2 — it used to wait for the current file, so a cancelled 35 GB download kept going); every check/sync line is also written to `logs/<today>.txt`

The check runs once per workflow/pod (Auto Run does not re-check every batch). Set it up in **Settings > Models**: the local **Models folder** (the `ComfyUI/models` root) and the S3 fields — *Import from S3 Browser config…* fills profile/endpoint/region/bucket. The check stays off until the endpoint and bucket are filled in. Needs `boto3` (bundled in the EXE) and the `runpod-s3` AWS profile.

## Stop on ComfyUI Errors

If ComfyUI rejects the workflow (e.g. *Value not in list: unet_name* for a model the pod lacks), fails while generating (e.g. out of memory) or finishes without producing an image, the run stops immediately, shows the reason in a dialog and the log, and plays the alert sound. Connection hiccups are tolerated, but three images in a row failing stops the run too.

## Prompt Weighting

Add an optional weight to a prompt block's separator to bias random selection: `---- PROMPT START x3 -----` makes that prompt 3x more likely to be picked than a default (1x) prompt. Weighting only affects the **Random** order mode (not Sequential or Evens → Odds). Weights show next to each prompt in the list as `[3x]`.

## Per-Image Pinning

Double-click any thumbnail in the Randomizer grid to pin a specific style to that image — it always uses that prompt instead of the random/sequential pick, shown with a 📌 badge. Pins are session-based (cleared on app restart) and can be removed from the same pin dialog. Pinned images are still skipped by "Skip already-processed" once they've been run.

## Prompt Usage Log

Every successful generation appends a row to `prompt_log.csv` in the output folder: timestamp, output filename, prompt index, weight, note (e.g. `pinned`), and a preview of the prompt text used. Useful for auditing which prompt produced which output.

## Changelog

### v1.8.1
- Fix: Settings > RunPod showed empty GPU/pod lists (the list fetch was never started); lists and account balance now load when Settings opens

### v1.8.0
- **Stop on ComfyUI errors** — a rejected workflow (missing model etc.), an execution error or an image-less result stops the whole run with ComfyUI's own reason (node + message), an error dialog and the alert sound; three consecutive non-ComfyUI failures (network) also stop it. Previously every image failed one by one
- **Model check & sync with the pod volume** — `model_sync.py` copied from the Video Creator; Settings > Models tab; runs before RunPod runs and re-rolls, once per workflow/pod, with Sync / Run anyway / Cancel choices and a verified transfer progress dialog. boto3 is back in the EXE

### v1.7.0
- **RunPod pod control ported from the Video Creator** — header Start/Stop Pod button + spend readout, launch chooser, GPU/pod priority order, spend limit, idle stop, keep-trying retry, alert sound, quit-time stop prompt. New files `runpod_api.py`, `alerts.py`, `ui/pod_worker.py`, `ui/pod_control.py` are copies (no shared code — port future pod fixes to every app)
- **Settings is tabbed** (Server & Paths / RunPod / AI Scene Generator) so the pod lists fit a 1080p screen
- A run past the pod's spend limit is refused (Auto Run stops cleanly) and the pod stops when the current run ends
- Alert sound when a Start run or Auto Run finishes (not on Cancel)
- **Prompt list tooltips** — hovering a style prompt shows its full text, wrapped; tooltip styled to match the dark theme

### v1.6.3
- **Daily processing log** — every run now also writes to `logs/YYYY-MM-DD.txt` next to the EXE (created automatically), with a run-start header (image/prompt counts), one line per image recording the filename and the full prompt used, and a Done/Cancelled footer with elapsed time. Uses the same frozen-EXE-aware base directory as `csr_config.json`, so it always lands next to the EXE regardless of PyInstaller's working directory quirks.
- Fixed a settings-persistence gap — editing the Input Folder field now saves immediately instead of only on app close or Start

### v1.6.2
- **Total elapsed time** logged when a batch run finishes ("Done! N images processed in Xm Ys.") or is cancelled ("Cancelled. (Xm Ys)")
- **Longer prompt previews in the log** — the chosen-prompt preview shown per image went from 60 to 255 characters, so longer style prompts aren't cut off mid-thought

### v1.6.1
- **Scenario field** in the AI scene generator — an optional fixed shot/subject template (e.g. `"Close-up, upper body in frame. A couple set in <scene description>."`) kept word-for-word across every generated prompt; only the `<scene description>` placeholder varies per generation, driven by the Idea field. Persisted in config so it's only typed once. Leave blank for the old free-form behavior.

### v1.6.0
- **Generate Scenes with AI** — the Edit Prompts dialog now has a built-in scene generator: type a scene/theme idea, pick a provider (Anthropic, Google Gemini, Groq, or OpenRouter) and model, set a count (1-30), and it generates that many distinct style-prompt variations directly into the editor in the app's own `---- PROMPT START -----` format — no more writing them by hand or in an outside chat tool
- **⚙ Settings** now has an "AI Scene Generator — API Keys" section (one key per provider, same as Prompt Enhancer)
- Fixed Cancel/Save/Pin buttons showing clipped text (e.g. "ance" instead of "Cancel") in the prompt editor and pin dialogs — fixed-width buttons were narrower than their padding+text needed

### v1.5.0
- **Prompt weighting** — optional `x<N>` weight suffix on the prompt separator biases random selection
- **Per-image prompt pinning** — double-click a thumbnail to pin a specific style; shown with a 📌 badge
- **Re-roll button** (Library tab) — re-process a single output image with a new random style (excludes the previously used prompt when possible); requires the source image to still be in the input folder
- **Prompt-used metadata log** — `prompt_log.csv` written to the output folder recording which prompt was used for each output

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

- [x] Per-image prompt override: click a thumbnail, pin a specific prompt
- [x] Prompt weighting: mark some prompts as more likely
- [x] "Re-roll" button on a finished image to re-run with a new random prompt
- [x] Prompt-used metadata sidecar/CSV so you know which prompt made which output
