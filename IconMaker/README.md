# Icon Maker

A Python script that batch-generates AI app icons for all projects in this repository using ComfyUI, then converts them to `.ico` format and copies them into each project folder as `app_icon.ico`.

## How It Works

1. Loads a ComfyUI text-to-image workflow (`qwen_T2Image_2512_API.json`)
2. For each app, submits a custom prompt to a local ComfyUI server
3. Waits for the image to generate
4. Saves the PNG to `output/<AppName>.png`
5. Converts the PNG to a multi-size `.ico` (16, 32, 48, 256 px) at `output/<AppName>.ico`
6. Copies the `.ico` into the project folder as `app_icon.ico`

## Requirements

```
Python 3.x
Pillow
ComfyUI running locally on http://127.0.0.1:8000
```

```bash
pip install Pillow
```

## Usage

1. Start ComfyUI on port 8000
2. Run the script:

```bash
python make_icons.py
```

Generated icons are saved to `output/` and distributed to each project folder automatically.

## Configuration

Edit the top of `make_icons.py` to change:

- `COMFY_URL` — ComfyUI server address
- `COMFY_OUTPUT` — ComfyUI output directory
- `ICO_SIZES` — icon sizes to include in the `.ico` file
- `APPS` list — add or modify app entries and their prompts
