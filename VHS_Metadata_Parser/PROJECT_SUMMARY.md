# VHS Metadata Parser  V-1.2.0

A desktop app for parsing and displaying ComfyUI workflow metadata embedded in MP4 files, JSON, or TXT files.

---

## Features

- **Drag & drop** MP4, JSON, or TXT files onto the window
- **7 tabbed views**: Video Settings, Prompts, Models, Sampler, Workflow, Raw JSON, Batch / Search
- **Batch mode**: scan a folder (optionally recursive) and see a summary table (dimensions, sampler, LoRA, UNET, etc.) for every file
- **Search across a folder**: live filter over the batch table by filename, LoRA/model name, sampler, or prompt text (e.g. "which videos used LoRA X?")
- **Diff view**: select two rows in the batch table and compare their key metadata fields side by side, differing fields highlighted
- **Export summary CSV**: dump the (filtered) batch table to CSV
- **Copy workflow JSON** to clipboard for direct import into ComfyUI
- **Save workflow** to a `.json` file
- **Export Models & Sampler CSV** for the currently loaded single file
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
