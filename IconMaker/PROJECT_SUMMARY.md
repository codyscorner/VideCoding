# Icon Maker

**Version:** 1.0.0 | **Status:** Active | **Language:** Python

Generates application icons by sending prompts to a local ComfyUI instance, then converting the resulting PNGs into multi-resolution `.ico` files. Wraps the headless `make_icons.py` logic in a PyQt6 GUI.

## Workflow

1. User selects apps to process from a checkbox list
2. GUI submits text-to-image requests to ComfyUI using a workflow JSON template
3. Saves generated PNGs to `IconMaker/output/<AppName>.png`
4. Converts each PNG to a `.ico` file with sizes 16, 32, 48, and 256 px
5. Copies the `.ico` to the target project folder as `app_icon.ico`

## Files

```
IconMaker/
├── main.py                     — PyQt6 GUI wrapper (v1.0.0)
├── make_icons.py               — Headless logic: APPS list, ComfyUI helpers
└── qwen_T2Image_2512_API.json  — ComfyUI workflow template
```

## Usage

```bash
python main.py
```

Requires ComfyUI running locally (default: `http://127.0.0.1:8000`). Configure the URL and output folder in the GUI config row.

## Notes

- No EXE build — this is a dev tool requiring a local ComfyUI instance
- `make_icons.py` remains usable as a headless script (edit `NEW_APPS` set to control which apps run)
- Requires `Pillow` for ICO conversion

## Version History

### v1.0.0
- PyQt6 GUI wrapper around `make_icons.py`
- App selector: QListWidget with checkboxes, Select All / Deselect All
- Config row: ComfyUI URL and output folder (pre-filled from script defaults)
- Generate button, progress label, append-only log
- QThread worker — UI stays responsive during generation
- Dark theme: BG `#0d0d1a`, accent `#5e4bdb`
