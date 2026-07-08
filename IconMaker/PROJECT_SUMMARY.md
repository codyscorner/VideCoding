# Icon Maker

**Version:** 1.1.0 | **Status:** Active | **Language:** Python

Generates application icons by sending prompts to a local ComfyUI instance, then converting the resulting PNGs into multi-resolution `.ico` files. Wraps the headless `make_icons.py` logic in a PyQt6 GUI.

## Workflow

1. User selects apps to process from a checkbox list, and sets Candidates/Padding/Corner Radius options
2. GUI submits text-to-image requests to ComfyUI using a workflow JSON template (one request per candidate, per app)
3. If more than one candidate was generated, a picker dialog shows thumbnails to choose from before continuing
4. Saves the chosen PNG to `IconMaker/output/<AppName>.png`
5. Converts it to a `.ico` file with sizes 16, 32, 48, and 256 px, applying padding/rounding if configured
6. Copies the `.ico` to the target project folder as `app_icon.ico`
7. Appends the prompt + seed used to `IconMaker/output/prompt_history.json`

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

### v1.1.0
- Prompt history: every generated icon's prompt/seed/timestamp is appended per-app to `output/prompt_history.json`; "View History" button prints an app's past runs to the log
- Candidates per app (1-4, spinbox): generates that many images per app with different seeds; if more than one, a modal `CandidatePickerDialog` grid lets you pick the best before it's converted and copied — extra candidate PNGs are deleted after picking
- Padding % / Corner Radius % spinboxes: `build_ico_image()` shrinks the source onto a transparent canvas and/or applies a rounded-rectangle alpha mask before saving the `.ico`
- "Scan for Missing Icons" button: `find_projects_missing_icon()` lists project folders (containing `.py` files) that aren't in `APPS` and don't yet have an `app_icon.ico`
- Internal: `IconWorker` now blocks on a `threading.Event` while emitting `request_pick` (queued cross-thread signal) so the picker dialog runs on the main thread without redesigning the worker as async

### v1.0.0
- PyQt6 GUI wrapper around `make_icons.py`
- App selector: QListWidget with checkboxes, Select All / Deselect All
- Config row: ComfyUI URL and output folder (pre-filled from script defaults)
- Generate button, progress label, append-only log
- QThread worker — UI stays responsive during generation
- Dark theme: BG `#0d0d1a`, accent `#5e4bdb`

## Future Enhancements

All planned enhancements shipped in v1.1.0.
