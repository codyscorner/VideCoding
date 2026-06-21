# Icon Maker

**Version:** 1.0.0 | **Status:** Utility Script | **Language:** Python

A utility script that generates application icons by sending a prompt to ComfyUI, then converting the resulting PNG into a multi-resolution `.ico` file.

## Workflow

1. Sends a text-to-image request to a local ComfyUI instance using a workflow JSON template
2. Saves the generated PNG to `IconMaker/output/<AppName>.png`
3. Converts the PNG to a `.ico` file with sizes 16, 32, 48, and 256 px
4. Copies the `.ico` to the target project folder as `app_icon.ico`

## Files

```
IconMaker/
├── make_icons.py               — Main script
└── qwen_T2Image_2512_API.json  — ComfyUI workflow template
```

## Usage

```bash
python make_icons.py
```

Edit `make_icons.py` to set the app name and prompt before running.
