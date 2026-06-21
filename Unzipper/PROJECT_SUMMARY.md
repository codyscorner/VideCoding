# Unzipper  V-1.1.0

A lightweight Windows desktop app for batch-extracting ZIP files, built with Python and PyQt6.

---

## Features

- **Flat Unzip** — extracts every file from all ZIPs in a folder into a single destination folder, renaming files sequentially (`Filename_000001.mp4`, `_000002.mp4`, …)
- **Structured Unzip** — extracts each ZIP into its own subfolder (named after the ZIP), preserving the internal folder structure. Duplicate folder names are automatically suffixed (`FolderName_000001`, etc.)
- **Color-coded status log** — green for success, red for errors, blue for progress info
- **Dark forest green UI** — clean modern PyQt6 theme

---

## Download

Grab the latest `.exe` from the [`dist/`](dist/) folder — no Python install needed.

---

## Usage

1. Run `Unzipper.exe` (or `python unzipper.py`)
2. Set the **Source Folder** containing your `.zip` files
3. Set the **Destination Folder** where files will be extracted
4. *(Flat mode only)* Enter a base **Filename** — files will be numbered from that name
5. Click **Unzip — Flat** or **Unzip — Keep Structure**

---

## Modes Explained

| Mode | What it does |
|------|-------------|
| **Flat** | All files from all ZIPs land in one folder, renamed `<Filename>_000001`, `_000002`, … |
| **Keep Structure** | Each ZIP gets its own subfolder; internal paths are preserved |

---

## Build from Source

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "Unzipper" unzipper.py
# Output: dist/Unzipper.exe
```

---

## Requirements (source)

- Python 3.10+
- `PyQt6`

```bash
pip install PyQt6
```

---

## License

MIT
