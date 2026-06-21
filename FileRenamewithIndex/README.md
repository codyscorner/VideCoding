# File Rename with Index

A Python script that batch-renames all files in a folder to a sequential `ComfyUI_Video_#####` format, sorted alphabetically. Designed for renaming ComfyUI video output files.

## How It Works

1. Reads all files in the target folder
2. Sorts them alphabetically
3. Renames each file to `ComfyUI_Video_00001.ext`, `ComfyUI_Video_00002.ext`, etc.
4. Preserves original file extensions

## Usage

Edit the `folder_path` at the bottom of `rename_files.py` to point to your target folder, then run:

```bash
python rename_files.py
```

Or double-click `run_rename.bat` to run with the default path.

### Facial variant

`rename_files_Facials.py` / `run_rename_Facial.bat` — same logic, intended for a different output folder.

## Requirements

```
Python 3.x (standard library only)
```
