# Changelog — ComfyUI Video Creator

### v1.3.7
- **Negative prompt is now a pop-out, not a box on the main window.** WAN 2.2 and other video workflows need a negative prompt, but it is boilerplate that hardly ever changes — so it collapses to a single row: the label, a one-line preview of the current text, and a **⤢ Edit** button that opens the same large editing window the positive prompt uses. The full text is still sent to ComfyUI, saved by "Save to workflow", and recorded in history exactly as before
- The whole Prompts pane therefore goes to the positive prompt, which is what gets rewritten every run. On a workflow with both prompts the positive editor went from roughly 60px to ~315px on a tall window (~170px on a 1080p screen) — a single-prompt MiniMax graph already had the pane to itself and gains a little too
- Options + LoRAs take at most 40% of the splitter (was 50%); that pane scrolls, and the splitter stays draggable and remembered per tab

### v1.3.6
- Progress bar no longer runs backwards near the end of a job. ComfyUI's post-sampling nodes (VAE decode, video save) emit step counts of their own; those were being folded back into the sampler count, so the bar dropped from e.g. 77% to 66% and the label flipped back to "Step 6/6". They now fill their own slice of the bar — the label reads "Saving video... 40/81" — and the bar only ever moves forward, reaching 100% when the finished file has been downloaded

### v1.3.5
- History dialog filters: **Workflow** (current workflow by default, "All workflows", or any other workflow that has history — with entry counts; entries from other workflows show their workflow name) and **Date** (All dates, or Year / Month / Day with a second dropdown listing only the periods that have entries, with counts). Text search applies on top of both. Delete removes the entry from whichever workflow file it belongs to

### v1.3.4
- Image → Video and Video → Extend tabs open with the thumbnail pane two columns wide so the prompt and settings panel gets the room; drag the divider or resize the window for more thumbnails

### v1.3.3
- The player now auto-closes at the end of the video everywhere, including playback from a tab's Results list (v1.3.2 only did it for the Library)
- "Save to workflow" log line now lists everything it wrote (prompts, LoRAs, steps, megapixels, length)

### v1.3.2
- Library playback closes the player automatically when the last selected video finishes (single video or playlist) — no more dismissing a window sitting on the final frame. Playback from a tab's Results list still stays open

### v1.3.1
- New app icon: crimson rounded tile with a white play triangle and film-strip perforations, generated with Z-Image Turbo on the RunPod ComfyUI (source kept as `app_icon_source.png`; `make_icon.py` rebuilds the multi-size `.ico` from it with rounded transparent corners). Embedded in the EXE and used by the window, taskbar, Start Menu and desktop shortcut

### v1.3.0
- **Steps control** in Options (next to Seed): shows the sampler step count found in the workflow (`KSampler`, `KSamplerAdvanced`, `BasicScheduler`…) and applies the value you set to every sampler node on each run — bump it for quality, drop it for quick tests, without opening the workflow. WAN 2.2 hi/lo `KSamplerAdvanced` pairs keep their split point proportional (8 steps split at 4 → 12 steps split at 6); a boundary at or past the old count still means "to the end". Hidden for workflows with no step input (e.g. fixed 4-step Turbo samplers)
- **Megapixels control** (same row as Length/Duration): shows the `megapixels` value of the workflow's `ImageScaleToTotalPixels` / `ResolutionSelector` nodes and applies what you set to all of them per run — small for quick tests, large for production. Hidden when the workflow has no numeric `megapixels` input (fixed width/height WAN graphs)
- Steps and Megapixels are written by "Save to workflow", recorded in every history entry, shown in the "Next run →" summary and the Library's Produced-by pane, and restored by "Use prompt + settings"
- The progress bar's step total now reflects the patched step count

### v1.2.0
- **Library tab** (modeled on the Chain Automator's): thumbnail grid of finished videos — the Output folder by default, or any folder (Settings > Folders > Library, or the … button on the tab) — with sort, multi-select, **Play** (selected videos back-to-back as a playlist, double-click plays one), **Delete** (with confirmation; removes cached thumbnails too), **Open Folder**, **Refresh**, and **Send to Extend**, which switches to the Video → Extend tab with that video selected as the source (switching the Extend folder if the video lives elsewhere)
- Library details pane: file size, resolution, fps, duration, audio yes/no, and a **Produced by** box showing the prompt, LoRAs/strengths, seed and length the video was generated with — looked up by result file name across every workflow's prompt history
- The Library refreshes itself when a run finishes
- Build script deploys even while the app is running: the in-use EXE is renamed aside (`ComfyUI_Video_Creator.old.exe`) and the new one copied in; the next launch picks it up

### v1.1.0
- **LoRA picker**: every LoRA node in the selected workflow (`LoraLoaderModelOnly`, `LoraLoader`, rgthree `Lora Loader Stack`, `MiniMaxH3TurboLoRA`) gets a row with an editable dropdown of LoRA files and its strength spinner(s). The list comes from the LoRAs folder (new Settings > Folders > LoRAs) or, with ⇣ Server, from the connected ComfyUI (`/models/loras`) so RunPod mode shows what the pod actually has. Changes apply per run; "Save to workflow" writes them into the JSON
- **Prompt history with settings**: every run (and every Save to workflow) appends an entry to the workflow's `<name>.prompt_history.json` — the same sidecar file the Chain Automator uses — recording the prompts, seed, length/duration, every LoRA + strength, mode, video input mode and source file; the result file name is attached when the run finishes. Exact repeats of the previous entry are not duplicated. New 📜 History dialog: search, preview, **Use prompt** or **Use prompt + settings** (restores LoRAs, strengths, seed and length), delete
- **Bigger prompt area**: the right panel is now a draggable vertical splitter — Prompts above, Options + LoRAs below (scrolls when short on room); the split position is remembered per tab. Each prompt has an **⤢ Expand** button that opens it in a large separate editor window
- A "Next run →" summary line under the workflow status always shows the LoRAs/strengths, seed and length the next run will use
- **Extend tab thumbnails now show each video's last frame** (the extension's starting point) with a hint under the sort box; cached as `<stem>_last.jpg` so they never clash with the Chain Automator's first-frame cache, and regenerated when the video changes
- Log and Results now sit side by side under the progress bar to give the prompts more vertical room

### v1.0.0
- Initial release. Standalone single-shot ComfyUI API workflow runner, deliberately separate from the Chain Automator so the two can evolve without affecting each other
- **Image → Video tab**: thumbnail grid of a chosen image folder (sortable, cached thumbnails shared with the Chain Automator's cache layout), pick a workflow, run
- **Video → Extend tab**: thumbnail grid of a chosen video folder; the selected video feeds the workflow either as its last frame (into a `LoadImage` / folder-loader node) or as the whole file (into a `LoadVideo` / `VHS_LoadVideo` node) — auto-detected, with a manual override. Optional "append the new clip to the source video" produces `<name>_extended_<stamp>.mp4` via ffmpeg concat (normalized size/fps, audio kept when both parts have it)
- **Workflow dropdown** lists every `.json` under the Workflows folder (subfolders included, prompt-history files skipped); UI-format exports are rejected with a message telling you to use Workflow > Export (API)
- Batch-style workflows that read a folder (`LoadImageListFromDir //Inspire`) work too: the single image is staged into a fresh run folder (uploaded to `input/VideoCreator/<run>` on RunPod, copied to a local staging folder otherwise) and the loader is pointed at it
- Prompt editor auto-built from the workflow: CLIPTextEncode positive/negative, MiniMax H3 `prompt`, PrimitiveStringMultiline; edits apply per run, "Save to workflow" writes them back into the JSON; adjustable text size
- Seed: random per run or fixed (with 🎲); Length/Duration control when the workflow exposes `WanImageToVideo.length` or an H3 "Float (duration)" node
- Local and RunPod modes with separate URLs and a "Test connection" button; results are always downloaded to the configured Output folder and named `<source>_<workflow>_<stamp>.mp4`
- Live websocket step progress (cumulative across multi-sampler WAN hi/lo passes, plus post-sampler decode/encode/save phases) with HTTP-polling fallback; Cancel interrupts the job on the server
- Built-in video player for results, Open Folder shortcuts, run log (`video_creator_run.log`, last 50 runs) next to the EXE
- Dark red theme; config `video_creator_config.json` lives next to the EXE; `ffmpeg.exe` shipped next to the EXE (configured path → app-local → PATH)
