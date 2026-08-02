# Changelog — ComfyUI Workflow Chain Automator

### v3.7.4
- **Library "Settings" button**: select a single video and view the prompt, sampler, video, and model settings used to generate it, one tab per chain segment
- **`prompts.txt` in every batch zip**: each per-image zip archive now includes a plain-text summary of every segment's prompts/sampler/video settings, so they can be checked in Notepad without opening any file individually
- Fixed a gap where the final stitched video carried no generation metadata at all — ffmpeg's concat re-encode strips the ComfyUI metadata VHS_VideoCombine embeds in each segment clip; `_stitch()` now extracts every segment's prompt graph before the source clips are discarded, re-embeds them into the final video via an ffmpeg ffmetadata file (avoids the command-line length limit a multi-segment JSON blob could hit as a raw `-metadata` argument), and hands them off to `_zip_segments()` for the text summary
- New `metadata_parser.py` — shared byte-scan extraction (same technique as the standalone VHS_Metadata_Parser tool), a read-only `SegmentMetadata` view for pulling prompts/sampler/video/model settings out of a segment's prompt graph (used by the Settings dialog), and `build_prompts_text()` for the zip's plain-text summary
- Only applies to videos stitched from now on — videos created before this update have no embedded metadata to show

### v3.7.3
- **Exact per-segment step totals read from the workflow JSON**: before queueing each segment the worker counts the sampler nodes and their *executed* steps (KSamplerAdvanced honors `start_at_step`/`end_at_step`, so WAN 2.2's hi/lo pair with steps=4 counts as 2+2) and multiplies by the images in the batch — new `segment_plan` signal carries (passes, total steps)
- Step bar now fills once across the whole segment showing cumulative progress (`Step 5/16` for 4 images × 4 steps) instead of refilling per sampler pass; segment bar and ETA use the same exact fraction, accurate from segment 1 (no more learning from the first segment)
- Workflows with no readable sampler nodes fall back to the previous behavior (per-pass step bar, pass count learned from the first completed segment)

### v3.7.2
- **Per-chain processed registry**: each completed batch records its images in `thumbnails/processed_chains.json` inside the image folder, keyed by chain folder name — so the app remembers what each chain has processed even after the finished videos are moved out of the chain's output folder
- Filtering hides an image if it has a video in the active chain's output folder **or** appears in that chain's registry; other chains are unaffected, so the same images stay available to process with every other workflow
- 'Show all' still reveals everything, so a registry-hidden image can always be re-run deliberately
- Registry snapshot is taken at batch start (image folder, chain, selection), so switching chains while a batch runs records against the right chain

### v3.7.1
- **Separate step progress bar** below the segment bar: fills with the current sampler step (step 1/2 → 50%, step 2/2 → 100%) and resets when a new sampler pass starts, so the within-step motion has its own bar
- **Segment bar no longer bounces backwards**: each sampler pass in a segment restarts ComfyUI's raw step counter, which used to yank the segment bar back mid-segment; the bar now counts passes (learned from the first completed segment) and only ever moves forward
- ETA projection uses the same forward-only in-segment fraction, so the time-left estimate no longer oscillates within a segment

### v3.7.0
- **Image thumbnails are now cached on disk** in a `thumbnails` subfolder inside the image folder (same pattern as the Library's video thumbnails); each load does a quick sync — generates thumbs for new/changed images (mtime compare), deletes thumbs whose source image is gone — so a 1000-image folder loads in seconds instead of re-decoding every picture
- **Switching chain folders no longer rescans the image folder** — the grid keeps its loaded thumbnails and just shows/hides images to match the new template (hidden = already has a video for that chain); switching templates back and forth is instant
- 'Show all' and post-batch refresh use the same in-place show/hide instead of reloading; processed images are hidden (not removed), so switching templates brings them back without a rescan
- Auto Run selects its next batch from visible images only
- Changing the image folder itself still reloads the grid (new folder, new thumbnails); each folder keeps its own `thumbnails` cache

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
