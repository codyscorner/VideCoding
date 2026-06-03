# ComfyUI Workflow Chain Automator — Plan

## Goal

Automate a 7-workflow video generation pipeline in ComfyUI where each workflow:
1. Takes the output video from the previous workflow
2. Extracts the **last frame** of that video
3. Uses that frame as the image input for the WAN 2.2 I2V (Image-to-Video) model
4. Runs the next workflow via the ComfyUI API
5. Waits for completion, then repeats for the next step
6. After all 7 segments complete, **stitches them into one final video** using FFmpeg concat (no audio)

Prompts and LoRAs are pre-written in each workflow — only the video/image input node needs to be updated dynamically.

- **Segment 1** — has a **Load Image** node. User picks the starting PNG/JPG from `input\`.
- **Segments 2–7** — have a **Load Video (Upload)** node feeding into a **Select Images** node (from comfyui-videohelpersuite). The `Select Images` node extracts a specific frame from the video batch. The script uploads the previous segment's output `.mp4` and patches the `Load Video (Upload)` node's `video` field with the uploaded filename. The `Select Images` node's `indexes` field is set to `-1` to select the last frame.

---

## Local Folder Structure

| Purpose | Path |
|---|---|
| Starting images to pick from | `C:\AI\CumfyUI\input\` |
| Video output per segment | `C:\AI\CumfyUI\output\video\Merge\Segment_1_00001.mp4`, `Segment_2_00001.mp4`, ... |
| Workflow API JSON files | `C:\AI\CumfyUI\Workflow_API\` |

**Segment naming convention:** each workflow writes its output video into its own `Segment_?` subfolder.  
When chaining, the script looks in `Segment_N` for the latest video, extracts the last frame, and feeds it into workflow N+1.

---

## How the ComfyUI API Works

ComfyUI exposes a local REST API at `http://127.0.0.1:8000` (confirmed from server settings).

Key endpoints:
- `POST /prompt` — queue a workflow for execution
- `GET /history/{prompt_id}` — poll for completion and get output file paths
- `POST /upload/image` — upload an image (last frame PNG) before queuing
- `GET /queue` — check queue status
- WebSocket `ws://127.0.0.1:8188/ws?clientId=...` — real-time progress events

Workflow API format: each workflow is exported from ComfyUI as an **API JSON** (`Save (API Format)` button). Nodes are referenced by their numeric string ID (e.g. `"6"`, `"42"`).

---

## Architecture

```
ComfyUI_Chain_Automator/
│
├── main.py                   ← entry point (QApplication + MainWindow)
├── config.py                 ← ConfigManager (JSON load/save)
├── worker.py                 ← QThread worker: chain logic, API calls, frame extraction
├── main_config.json          ← paths, workflow list, node IDs
│
├── ui/
│   ├── __init__.py
│   ├── main_window.py        ← MainWindow (PyQt6)
│   └── styles.py             ← dark theme stylesheet + COLORS dict
│
└── temp/                     ← temp PNGs for extracted last frames (auto-cleaned)
```

Workflow JSONs live in ComfyUI's own folder: `C:\AI\CumfyUI\Workflow_API\`

### GUI Layout

```
┌──────────────────────────────────────────────────┐
│  ComfyUI Workflow Chain Automator          v1.0.0 │
├──────────────────────────────────────────────────┤
│  Starting Image                                   │
│  [Dropdown / list of images in input\]  [Browse] │
│  [Thumbnail preview of selected image]            │
├──────────────────────────────────────────────────┤
│  Segment Progress                                 │
│  ● Segment 1  ○ Segment 2  ○ ... ○ Segment 7    │
│  [████████████░░░░░░░░] Segment 2/7 — Queued...  │
├──────────────────────────────────────────────────┤
│  Log                                              │
│  [scrollable text area]                           │
│    [Segment 1] Complete → Segment_1\out_001.mp4  │
│    [Segment 2] Extracting last frame...           │
│    [Segment 2] Uploading frame...                 │
│    [Segment 2] Queued (id: abc123), polling...    │
├──────────────────────────────────────────────────┤
│         [▶ Start Chain]    [✕ Cancel]             │
└──────────────────────────────────────────────────┘
```

### Worker Thread Flow (`worker.py` — `QThread`)

```
STARTUP:
  - Signals: log(str), segment_done(int), finished(), error(str)

For segment 1:
  1. Load Workflow_API JSON for segment 1
  2. Patch the Load Image node ["image"] with the user-selected starting image filename
     (file already in ComfyUI input\ — no upload needed)
  3. POST to /prompt → get prompt_id
  4. Poll /history/{prompt_id} until complete → emit log updates
  5. Retrieve output video path from Segment_1\ folder → emit segment_done(1)

For segments 2 → 7:
  1. Load Workflow_API JSON for segment N
  2. Find the output video in Segment_{N-1}\ (newest .mp4 by mtime)
  3. Upload that .mp4 to ComfyUI via POST /upload/video (multipart)
  4. Patch the Load Video (Upload) node ["video"] with the uploaded filename
     (Select Images node already has indexes = -1, so last frame is auto-selected)
  5. POST to /prompt → get prompt_id
  6. Poll /history/{prompt_id} until complete → emit log updates
  7. Retrieve output video path from Segment_N\ folder → emit segment_done(N)

emit finished()

STITCH:
  1. Collect the output video from each Segment_1\ through Segment_7\ in order
  2. Write a FFmpeg concat list file to temp\concat_list.txt:
       file 'C:/AI/CumfyUI/output/video/Merge/Segment_1/video.mp4'
       file 'C:/AI/CumfyUI/output/video/Merge/Segment_2/video.mp4'
       ...
  3. Run: ffmpeg -f concat -safe 0 -i concat_list.txt -c copy final_output.mp4
  4. Save final_output.mp4 to C:\AI\CumfyUI\output\video\Merge\ with a timestamped name
  5. emit stitch_done(final_path)
```

---

## Config (`main_config.json`)

```json
{
  "comfyui_url": "http://127.0.0.1:8000",
  "input_dir": "C:/AI/CumfyUI/input",
  "output_base_dir": "C:/AI/CumfyUI/output/video/Merge",
  "workflow_dir": "C:/AI/CumfyUI/Workflow_API",
  "workflows": [
    {
      "segment": 1,
      "json_file": "workflow_segment_01.json",
      "input_node_id": "97",
      "input_type": "image"
    },
    {
      "segment": 2,
      "json_file": "workflow_segment_02.json",
      "input_node_id": "126",
      "input_type": "video"
    },
    {
      "segment": 3,
      "json_file": "workflow_segment_03.json",
      "input_node_id": "133",
      "input_type": "video"
    },
    {
      "segment": 4,
      "json_file": "workflow_segment_04.json",
      "input_node_id": "133",
      "input_type": "video"
    },
    {
      "segment": 5,
      "json_file": "workflow_segment_05.json",
      "input_node_id": "139",
      "input_type": "video"
    },
    {
      "segment": 6,
      "json_file": "workflow_segment_06.json",
      "input_node_id": "139",
      "input_type": "video"
    },
    {
      "segment": 7,
      "json_file": "workflow_segment_07.json",
      "input_node_id": "139",
      "input_type": "video"
    }
  ]
}
```

- `input_type: "image"` → patches `inputs["image"]`, no upload (file already in ComfyUI `input\`)
- `input_type: "video"` → uploads the `.mp4` via `/upload/video`, patches `inputs["video"]`

> **Note:** `input_node_id` values above are placeholders — fill in after inspecting each exported API JSON (search for `"LoadImage"` or `"VHS_LoadVideo"` to find the node ID).

---

## Key Implementation Details

### Final Stitch
After all 7 segments complete, FFmpeg concat merges them in order into one file. Since there's no audio, `-c copy` is used — it's lossless and near-instant (no re-encode). Output saved to:
```
C:\AI\CumfyUI\output\video\Merge\final_YYYYMMDD_HHMMSS.mp4
```
FFmpeg concat list written to `temp\concat_list.txt`, then cleaned up after.

### Segment 1 — Starting Image (Load Image node)
The GUI populates a dropdown from all images in `C:\AI\CumfyUI\input\` on startup. Selecting one shows a thumbnail preview. The filename is patched directly into the Load Image node — no upload needed since the file is already in ComfyUI's `input\` folder.

### Segments 2–7 — Uploading the Previous Video (Load Video Upload node)
The previous segment's output `.mp4` is uploaded via `POST /upload/video` with `multipart/form-data` (comfyui-videohelpersuite endpoint).  
Returns `{ "name": "filename.mp4", "subfolder": "", "type": "input" }`.  
The returned `name` is patched into the `Load Video (Upload)` node's `video` input field.  
The connected `Select Images` node already has `indexes = -1` in the workflow JSON (selects the last frame) — no patching needed there.

### Patching the Workflow JSON
Each patch targets one node by its ID and updates one field in `inputs`:
- Segment 1: `workflow[image_node_id]["inputs"]["image"] = "filename.png"`
- Segments 2–7: `workflow[video_node_id]["inputs"]["video"] = "filename.mp4"`

The JSON is patched in memory — the original file on disk is never modified.

### Polling for Completion
Poll `GET /history/{prompt_id}` every 3 seconds. When the prompt_id key appears in the response, the job is done. Output video path is found inside:
```
response[prompt_id]["outputs"][video_save_node_id]["videos"][0]["filename"]
```
Fallback: scan `Segment_N\` for the newest `.mp4` by modified time.

---

## Dependencies

| Library | Purpose |
|---|---|
| `PyQt6` | GUI framework (dark theme, QThread worker, signals) |
| `requests` | HTTP calls to ComfyUI API |
| `json` | Load and patch workflow files |
| `uuid` | Unique client_id for API session |
| `pathlib` | Clean cross-platform path handling |
| `ffmpeg` (subprocess) | Final stitch of all 7 segments into one video |

Install: `pip install PyQt6 requests`  
FFmpeg needed for the final stitch — must be on system PATH. Segments 2–7 upload raw `.mp4` directly; ComfyUI handles frame extraction internally via `Select Images`.

---

## Phases

### Phase 1 — Core Worker Logic
- [ ] `worker.py`: QThread with chain logic, FFmpeg last-frame extraction, API calls, polling
- [ ] `config.py`: ConfigManager (JSON load/save)
- [ ] End-to-end test of worker with 2 segments (no GUI yet)

### Phase 2 — GUI
- [ ] `ui/styles.py`: dark theme (color palette TBD with user)
- [ ] `ui/main_window.py`: image picker dropdown + thumbnail, segment progress indicators, log area, Start/Cancel buttons
- [ ] `main.py`: QApplication entry point
- [ ] Wire worker signals → GUI updates (log lines, segment dots, progress bar)

### Phase 3 — Full Config + Test
- [ ] `main_config.json` with correct JSON filenames for all 7 segments
- [ ] Identify and fill in real `image_node_id` values from each exported API JSON
- [ ] Test full 7-segment chain end-to-end

### Phase 4 — Polish
- [ ] Error handling: ComfyUI unreachable, job failed, no video found in output folder
- [ ] Cancel button stops the worker mid-chain cleanly
- [ ] Clean up temp folder after stitch completes
- [ ] `build_exe.py` (PyInstaller) if desired

---

## Open Questions / Decisions Needed

1. ~~**Workflow 1 starting image**~~ ✅ Confirmed — Load Image node for segment 1 (user picks PNG/JPG from `input\`).
2. ~~**FFmpeg needed**~~ ✅ Not needed — segments 2–7 upload the raw `.mp4`; `Select Images` node handles last-frame extraction inside ComfyUI.
3. ~~**Workflow JSON filenames**~~ ✅ Confirmed — `workflow_segment_01.json` through `workflow_segment_07.json`
4. ~~**Node IDs**~~ ✅ Confirmed from API JSON inspection:
   - Segment 1: `LoadImage` → node `97`, field `image`
   - Segments 2–3: `VHS_LoadVideo` → node `126` / `133`, field `video`
   - Segments 4: `VHS_LoadVideo` → node `133`, field `video`
   - Segments 5–7: `VHS_LoadVideo` → node `139`, field `video`
