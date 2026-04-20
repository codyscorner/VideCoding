# VHS Metadata Parser  V-1.1.0

A desktop app for parsing and displaying ComfyUI workflow metadata embedded in MP4 files, JSON, or TXT files.

---

## Features

- **Drag & drop** MP4, JSON, or TXT files onto the window
- **6 tabbed views**: Video Settings, Prompts, Models, Sampler, Workflow, Raw JSON
- **Copy workflow JSON** to clipboard for direct import into ComfyUI
- **Save workflow** to a `.json` file
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

### v1.1.0
- Migrated from PyQt5 to PyQt6
- Dark blue-green theme applied throughout
- Updated all Qt6 enum flags (ResizeMode, EditTrigger, etc.)

### v1.0.0
- Initial release with PyQt5
- Tabbed metadata viewer
- Drag & drop and file browser support
