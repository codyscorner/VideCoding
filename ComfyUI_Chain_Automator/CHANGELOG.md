# Changelog — ComfyUI Workflow Chain Automator

### v3.6.1
- **Stitched filenames now carry a batch timestamp** (`photo_20260709_141530.mp4`, one shared stamp per batch run) — re-running a same-named source image after cleaning out a folder can no longer collide with or be mistaken for an earlier batch's video when moving files elsewhere; the zip archive inherits the timestamped name too
- The "hide already-processed images" filter and post-batch grid removal strip the timestamp when matching videos back to source images, so filtering behaves exactly as before

### v3.6.0
- **Live step progress**: the worker now listens on ComfyUI's websocket (`/ws?clientId=...`) and the progress bar advances with every sampler step instead of jumping once per segment; the label shows `Segment k/n — step 12/30`
- **ETA**: once at least one segment has completed this session, the label projects time remaining for the whole chain (`~7m 20s left`), using per-segment wall times from earlier batches where available
- Websocket is best-effort: if it can't connect or drops mid-run, the worker logs it and falls back to the previous HTTP polling loop; quiet stretches (model load) are covered by a history heartbeat so a missed finish can't hang the run
- New dependency: `websocket-client` (optional — polling fallback works without it)
- Build: PyInstaller spec now excludes torch/tensorflow/etc. from the shared venv (smaller EXE); `build_exe.py` no longer overwrites the live `main_config.json` next to the deployed EXE — it only seeds it on first deploy

### v3.5.1
- Cancel now actually stops the job on the ComfyUI server: removes the pending prompt from the queue and POSTs `/interrupt` — previously the prompt kept running (and kept billing on RunPod) after the UI said cancelled
- Fix: cancelling mid-poll no longer tries to download outputs of the half-finished prompt (confusing error instead of "Cancelled")
- Fix: a missing output video no longer silently truncates the batch — every image after the gap would have been stitched to the wrong chain of videos; the run now fails loudly naming the segment
- Fix: Auto Run next-batch handoff moved from `all_done` to the worker's `finished` signal — previously the new worker replaced the still-running old QThread (timing-dependent crash risk)
- Removed dead code: single-mode `worker.py` (unused since batch-only v2.7.0), `CompletionDialog`, `_on_stitch_done`, `_find_local_batch_outputs`
- Daily log no longer recreates the output folder on every log line
- Changelog moved out of PROJECT_SUMMARY.md into this file


### v3.5.0
- **Per-template output subfolders**: the "Final Video Folder" in Settings is now a root folder; the app automatically creates a subfolder named after the active chain template (e.g. `Videos/WAN_Chain_1/`) and writes all stitched videos there
- Switching templates instantly refreshes the starting image grid — images already processed for the current template are hidden; switching to a template with no videos shows all images
- Library tab auto-updates its folder display when you switch templates
- Daily run log is written into the template's subfolder instead of the root
- Zero config changes required — root folder is still set once in Settings

### v3.4.0
- **Video Converter**: select one or more videos in the Library tab and click **🔄 Convert** to re-encode them to a photo-frame-compatible format
  - **AVI — Xvid**: widest digital photo frame support
  - **MP4 — H.264 Baseline**: universal device compatibility (re-encodes at Baseline/Level 3.1 + yuv420p)
  - **MOV — H.264**: QuickTime / Apple device compatibility
- Output folder defaults to the same folder as the source; can be changed per conversion
- Conversion runs in a background thread so the UI stays responsive; Cancel button stops mid-batch

### v3.3.0
- Poll log interval changed from 15 seconds to 1 minute — log now shows elapsed time in minutes (`2m`) instead of seconds to reduce log noise during long RunPod generations

### v3.2.0
- RunPod file-exists recovery: detects output files already present on RunPod before re-downloading
- Library tab shows selection count when multiple videos are selected

### v3.1.0
- **Auto Run mode**: processes all images in the folder automatically N at a time — no confirmation dialogs between batches
  - Configurable batch size spinner (1–50, default 4)
  - **▶▶ Auto Run** button starts the loop; processed images are removed from the grid automatically
  - **⏹ Stop After Batch** button finishes the current batch then stops cleanly
  - Auto mode is disabled when "Show all" is checked (prevents re-processing already-done images)
  - Auto mode stops automatically on error or cancellation
- **Library: Play Selected**: select multiple videos with Ctrl+click or Shift+click, then click **▶ Play Selected** to play them back-to-back in the built-in player (⏮/⏭ navigation, auto-advance on end)

### v3.0.1
- Fix: `_on_stitch_done` signal wiring carried over from single-mode; removed dead handler
- Minor log cleanup

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
