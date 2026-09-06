# Changelog — ComfyUI Video Creator

### v1.4.1
- **Fixed: a video you had played could not be deleted until the app was restarted** (`WinError 32 ... being used by another process`). Closing the player only called `stop()`, and on Windows that does not release the file - the media backend keeps the handle until the source is cleared or the player destroyed. Worse, the player window was never destroyed at all: it was parented to the main window and merely hidden on close, so every clip ever opened stayed locked, and starting another video just added a second hidden player on top
  - closing the player now clears its source, detaches the outputs and destroys the player and the window (`WA_DeleteOnClose`); the main window drops its reference the moment it closes
  - deleting a file the player currently holds closes that player first, then deletes - no need to close it yourself
  - the delete retries for up to ~1.2 s while the backend lets go of the handle, so a delete right after a close goes through
  - verified before/after on a real clip: locked while playing, **still locked after `stop()`**, free after the new close, deletable with zero delay
- Quitting the app closes any open player through the same path

### v1.4.0
*Ships everything from 1.3.9 onwards — those builds were interim and never released on their own.*

- **Fixed: deleting a file left its tile behind, and ↻ Refresh didn't clear it.** Two faults, both in the folder scanner:
  - **A rescan never let go of the scan already running.** `refresh()` asked the old loader to stop and waited up to 3 seconds, but a loader sitting in an ffmpeg last-frame extraction can't stop on the spot — and it was still connected to the grid. So it carried on emitting its *previous* listing into the freshly cleared view, deleted files included, and the folder looked like it hadn't been re-read. The loader is now disconnected the moment it's abandoned, so nothing it does afterwards can touch the grid
  - **The video scanner added a tile even when it couldn't make a thumbnail** — a grey placeholder — so a file deleted mid-scan came back as a stuck empty tile. Files that vanish during a scan are now skipped, checked both before and after the (slow) extraction step
- **Deleting in one tab clears the tile in the others.** The Library and the Video → Extend tab usually point at the same folder; the row is dropped from the other views immediately, without either of them rescanning
- Abandoned scans are parked until they actually finish rather than being dropped on the floor — a `QThread` garbage-collected while still running can take the whole app down with it
- The last-frame extraction gets a 30-second timeout (60 for the slow reverse-decode fallback), so a cancelled scan ends promptly instead of blocking on one bad file

### v1.3.14
- **Type-to-filter on the workflow dropdown.** Click the box and start typing: every workflow *containing* what you typed stays in the list, wherever the match falls — `makeout` finds `Video_MiniMax_Makeout on Bed/workflow_segment_01_batch.json`, `segment_03` finds all eleven of them. Case doesn't matter, and the match runs against the whole relative path, so a folder name filters as well as a file name
  - Qt's stock completer only matches from the first character, which is no use when the part you remember sits in the middle of the name
  - clicking the box selects the current entry, so typing replaces it instead of landing mid-word; text that matches nothing snaps back to the selected workflow when you click away
  - the ↻ button, the ⧉ Clone flow and the remembered selection all work exactly as before
- **The LoRA pickers filter the same way**, and there they keep whatever you type — a LoRA that lives on the server but not in your local folder is still accepted

### v1.3.13
- **Delete a file straight from the thumbnail grid**, on the Image → Video and Video → Extend tabs — a bad generation no longer means hunting it down in Explorer. Three ways in:
  - the 🗑 button in the folder row (greyed out until something is selected)
  - right-click a thumbnail → *Delete … (Recycle Bin)*
  - the **Del** key while the grid has focus
- **Deleted files go to the Recycle Bin**, not into thin air — including the Library's existing 🗑 Delete button, which used to remove them permanently. A permanent delete is the fallback only when the shell can't recycle (a network share, a full Bin), and anything that fails is reported by name
- Cached thumbnails for the deleted file (`thumbnails/<stem>.jpg`, `<stem>_last.jpg`, `<stem>_<crc>.jpg`) go with it, so a stale tile can't come back
- The grid drops the row and updates its count without a full folder rescan; the run panel follows the new selection. The Library keeps its single labelled button — the folder-row icon is hidden there rather than doubled up

### v1.3.12
- **Extension clips are marked `EXT`**, right before the timestamp: `<image>_<workflow>_EXT_<YYYYMMDD_HHMMSS>.mp4`. A clip from the Video → Extend tab is now obvious at a glance in the output folder, where before it looked exactly like an Image → Video result. Image runs are unmarked, and the stitched file keeps its own `_extended_<stamp>` name
- The marker is stripped along with the workflow label when the next extension is named, so it appears once and never stacks up

### v1.3.11
- **Extend output names stop growing with every pass.** Each run used to bolt its workflow and timestamp onto the whole previous file name, so extending an extension produced `<image>_<workflow A>_<stamp>_<workflow B>_<stamp>.mp4` (131 characters after one pass) and a chain of four or five runs would blow past the 260-character path limit Windows enforces. A video source now sheds what an earlier run appended and keeps only its own base name, so five chained extensions all land at the same length:
  - `grandfinals..._Video_MiniMax_Makeout_on_Bed_20260905_134013.mp4` → run through the Cumshot workflow → `grandfinals..._workflow_Cumshot_after_MO_on_bed_20260905_160000.mp4`
  - `_extended_<stamp>` is stripped the same way, so extending a stitched file works too
  - only names this app wrote are trimmed: a trailing timestamp is removed only when a known workflow label (or `extended`) sits in front of it, so a camera-style `IMG_20260101_120000.mp4` keeps its name intact
  - image sources are untouched — nothing compounds there
- **Every output name is capped to fit a 250-character path.** In a deep output folder the base name is shortened as far as needed; the workflow label, timestamp and extension are never cut, so files stay identifiable and the run can't fail on a path error

### v1.3.10
- **The Extend tab now checks the source video's codec against what the workflow is about to save.** The log opens every video run with `Source: 704x736 24fps h264`, and:
  - with *Append the new clip* ticked, the workflow **about to run** is retuned to match — `Output format: video/h265-mp4 -> video/h264-mp4 to match the source video (h264)`. Only the in-memory copy is touched; the workflow file on disk is never rewritten (use ⧉ Clone for that)
  - the replacement keeps the container and the encoder family, so `video/nvenc_hevc-mp4` becomes `video/nvenc_h264-mp4`, not plain h264
  - the options are read from the server that will run the job (`/object_info`), so a format that pod doesn't have is never written into the graph. If it has no match, the run says so instead of failing
  - with Append unticked it just notes the mismatch and changes nothing
  - a frame-rate difference (24 fps workflow, 16 fps source) is reported too, but never changed — that would alter the clip's speed
- **The stitched file keeps the source's codec family.** Extending an h265 video used to produce an h264 `_extended.mp4` several times the size; hevc sources are now written with libx265 (crf 20, `hvc1` tag), everything else with libx264 (crf 18)
- `probe()` reports the video codec, so `VideoProps` now carries `vcodec`

### v1.3.9
- **Fixed: "Append the new clip" failed with `ffmpeg concat failed ... Media type mismatch`.** When both clips carried audio (every MiniMax H3 clip does), the filter graph handed ffmpeg all the video streams and then all the audio streams. `concat` wants each segment's streams together — video, audio, video, audio — so it refused to link the graph and no `_extended.mp4` was written. The streams are now interleaved per segment
- **The new clip is generated at the source video's frame size when Append is ticked.** The Megapixels box was shrinking the extension (a 704x736 source produced a 640x672 clip at 0.40 MP), so the join needed an upscale. The source's own size is used instead — the log says `Appending - matching the source's 704x736: megapixels 0.494 (was 0.4)`, the run summary reads `MP: source video's size`, and the Megapixels box is left alone for every other run
- Stitching is harder to break in general:
  - a clip whose aspect ratio differs is fitted inside the first clip's frame and padded with black instead of being stretched
  - audio is resampled to one common format (48 kHz stereo), so clips recorded at different rates still join
  - a clip with no audio track gets matching silence, instead of the whole stitch losing its sound
  - odd frame sizes are rounded down to even, which libx264 requires
  - when ffmpeg still refuses, the error now lists each part's size, fps, duration and audio state plus the filter graph, so the cause is readable from the dialog

### v1.3.8
- **⧉ Clone button next to the workflow dropdown.** Copy the selected workflow under a new name and start editing the copy — the workflow you like is left exactly as it was. The dialog takes the new name (pre-filled with `<name> copy`; a name already in use is refused rather than silently overwritten), the destination subfolder of the Workflows folder (the original's folder by default), and two options:
  - *Start from the prompts, LoRAs and settings shown in the panel* (on by default) — whatever is on screen, saved or not, is written into the clone. Off makes a byte-for-byte copy of the file on disk
  - *Copy the prompt history too* — off by default; the original's history stays readable from 📜 History either way
- The clone becomes the tab's selected workflow the moment the dialog closes, is remembered across restarts, and appears in the other tab's dropdown too — without disturbing that tab's own selection or unsaved edits

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
