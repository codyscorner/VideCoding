# VHS Metadata Parser  V-1.3.1

A desktop app for parsing and displaying ComfyUI workflow metadata embedded in MP4 files, JSON, or TXT files.

---

## Features

- **Drag & drop** MP4, JSON, or TXT files onto the window
- **8 tabbed views**: Video Settings, Prompts, Models, Sampler, Other Settings, Workflow, Raw JSON, Batch / Search
- **Workflow-agnostic parsing**: WAN 2.x (`WanImageToVideo` + `KSamplerAdvanced`) and MiniMax H3 (`MiniMaxH3ImageToVideo` + `SamplerCustomAdvanced` / turbo sampler / turbo LoRA) both fully populate the tabs; links between nodes are followed back to their literal values (primitives, `ComfyMathExpression` frame-count formulas, resize nodes)
- **Prompt Sections** table: every prompt is split into readable parts — `[Shot N] At 00:00.000` shots, `Shot N · Dialogue` (`<d>…</d>` lines), `Camera:`, `overall_soundscape:`, `non_diegetic_music:`, any `Label:` block, or JSON keys — with the source node shown for each
- **Other Settings** tab: every literal node input that the dedicated tabs did *not* consume (resolution selectors, megapixel scalers, save/pingpong flags, `low_vram`, unused `KSamplerSelect`, …) so important settings from unfamiliar node types are never hidden; filter box + "show link-only nodes" toggle
- **Batch mode**: scan a folder (optionally recursive) and see a summary table (dimensions, sampler, LoRA, UNET, etc.) for every file
- **Search across a folder**: live filter over the batch table by filename, LoRA/model name, sampler, or prompt text (e.g. "which videos used LoRA X?")
- **Diff view**: select two rows in the batch table and compare their key metadata fields side by side, differing fields highlighted
- **Export summary CSV**: dump the (filtered) batch table to CSV
- **Copy workflow JSON** to clipboard for direct import into ComfyUI
- **Save workflow** to a `.json` file
- **Export Models, Sampler & Other Settings CSV** for the currently loaded single file
- **Dark blue-green theme** — easy on the eyes

---

## Supported File Types

| Type | Description |
|------|-------------|
| `.mp4` | Extracts embedded ComfyUI `{"prompt"...}` JSON block |
| `.json` | Direct ComfyUI metadata JSON |
| `.txt`  | JSON saved as plain text |

---

## Usage

1. Run `vhs_metadata_parser.py` or the compiled `.exe`
2. Drag & drop a file onto the window, or use **File > Open**
3. Browse the tabs to inspect prompts, models, sampler settings, and more
4. Use the **Workflow** tab to copy or save the workflow JSON for ComfyUI import

---

## Requirements

```bash
pip install PyQt6
```

---

## Building Executable

```bash
pip install pyinstaller
pyinstaller VHS_Metadata_Parser.spec
```

---

## Version History

### v1.3.1
- Rebuild release: the v1.3.0 EXE was built before the follow-up fixes landed. This build includes the MP4-header width/height/duration fallback (new **MP4 Header** row), the drop-zone / Video Settings layout fixes, the resizable and auto-collapsing Negative prompt pane, `run.bat`, and the optional command-line file argument.

### v1.3.0
- MiniMax H3 support: `MiniMaxH3ImageToVideo` prompt/width/height/length, `SamplerCustomAdvanced` (seed from `RandomNoise`, steps/scheduler/denoise from `BasicScheduler`, sampler from `KSamplerSelect` or the custom sampler node's title, CFG from a CFGGuider or "N/A (Basic Guider)"), `MiniMaxH3TurboLoRA` in the LoRA table, both VAEs, audio detection
- Link resolution: node inputs that point at other nodes are followed to primitives / same-named literals / `ComfyMathExpression` results (safe whitelisted evaluation), so e.g. MiniMax length resolves to `362` frames instead of `['105:107', 1]`
- Prompt detection is generic across node types (`prompt`, `text`, `positive`, `negative`, `custom_prompts`, …) with de-duplication; linked prompts (CLIPTextEncode ← PromptCycler) now resolve to text instead of showing a link list
- New **Prompt Sections** table on the Prompts tab (shots, dialogue, camera, soundscape, music, JSON keys)
- New **Other Settings** tab listing every un-consumed literal node input, with filter and link-only toggle; also appended to the single-file CSV export
- Video Settings gains Duration (s) and Audio rows; Sampler table gains a Denoise column; LoRA table gains a Loader column; batch diff/CSV gain Duration + Audio
- Models: generic detection via `clip_name*`, `vae_name`, `unet_name`, `ckpt_name`, `lora_name` (any loader node); Model Sampling covers every `ModelSampling*` node
- Bare API-format prompt JSON (no `{"prompt": …}` wrapper) now loads

### v1.2.0
- New **Batch / Search** tab: scan a folder for `.mp4`/`.json`/`.txt` metadata files (background thread, progress status), summary table of key settings per file
- Live search box filters the batch table by filename, LoRA/model name, sampler, or prompt text
- Diff view: select two rows and compare key metadata fields side by side in a dialog, differing fields highlighted
- Export batch summary to CSV
- Double-click a batch row to load that file into the main viewer tabs
- `VHS_Metadata_Parser.spec` now excludes shared-venv ML packages to keep the EXE small

### v1.1.0
- Migrated from PyQt5 to PyQt6
- Dark blue-green theme applied throughout
- Updated all Qt6 enum flags (ResizeMode, EditTrigger, etc.)

### v1.0.0
- Initial release with PyQt5
- Tabbed metadata viewer
- Drag & drop and file browser support

## Future Enhancements

- [x] Batch mode: parse a folder, table of key settings per file
- [x] Diff view: compare workflow metadata of two files
- [x] Search across a folder ("which videos used LoRA X?")
- [x] Export summary CSV
- [x] MiniMax H3 / SamplerCustomAdvanced workflows
- [x] Prompt section breakdown (shots, dialogue, camera, soundscape)
- [x] "Other Settings" catch-all for un-parsed node inputs
