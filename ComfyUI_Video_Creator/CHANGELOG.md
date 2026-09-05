# Changelog — ComfyUI Video Creator

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
