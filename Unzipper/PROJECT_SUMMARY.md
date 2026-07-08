# Unzipper  V-1.2.0

A lightweight Windows desktop app for batch-extracting ZIP, 7Z, and TAR.GZ archives, built with Python and PyQt6.

---

## Features

- **Flat Unzip** — extracts every file from all archives in a folder into a single destination folder, renaming files sequentially (`Filename_000001.mp4`, `_000002.mp4`, …)
- **Structured Unzip** — extracts each archive into its own subfolder, preserving the internal folder structure. Duplicate folder names are automatically suffixed (`FolderName_000001`, etc.)
- **ZIP support** — stdlib `zipfile`
- **7Z support** — `py7zr` (optional; skips with a warning if not installed)
- **TAR.GZ / TGZ support** — stdlib `tarfile`
- **Archive type prefix in log** — `[ZIP]`, `[7Z]`, `[TAR.GZ]`
- **Color-coded status log** — green for success, red for errors, yellow for warnings
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
- `py7zr` (optional — required for `.7z` support)

```bash
pip install PyQt6 py7zr
```

## Version History

### v1.2.0
- Added 7Z support via `py7zr` (graceful skip with warning if not installed)
- Added TAR.GZ / TGZ support via stdlib `tarfile`
- Both flat and structured modes now scan for `.zip`, `.7z`, `.tar.gz`, `.tgz`
- Log lines show archive type prefix: `[ZIP]`, `[7Z]`, `[TAR.GZ]`

### v1.1.0
- Initial release: ZIP-only batch extraction
- Flat mode and Keep Structure mode
- Sequential renaming, duplicate folder suffixing

---

## Future Enhancements

- [ ] Password-protected archive support (prompt or saved password list)
- [ ] RAR support via `rarfile`
- [ ] Test-only mode (verify archives without extracting)
- [ ] Delete archive after successful extraction (optional)
- [ ] Nested archive handling (zip inside zip)

---

## License

MIT
