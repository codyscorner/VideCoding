# Unzipper  V-1.3.0

A lightweight Windows desktop app for batch-extracting ZIP, 7Z, RAR, and TAR.GZ archives, built with Python and PyQt6.

---

## Features

- **Flat Unzip** — extracts every file from all archives in a folder into a single destination folder, renaming files sequentially (`Filename_000001.mp4`, `_000002.mp4`, …)
- **Structured Unzip** — extracts each archive into its own subfolder, preserving the internal folder structure. Duplicate folder names are automatically suffixed (`FolderName_000001`, etc.)
- **Test Archives** — verify every archive's integrity without extracting anything
- **ZIP support** — stdlib `zipfile`
- **7Z support** — `py7zr` (optional; skips with a warning if not installed)
- **RAR support** — `rarfile` (optional; needs WinRAR or 7-Zip installed — auto-detected)
- **TAR.GZ / TGZ support** — stdlib `tarfile`
- **Password-protected archives** — password field + saved password list (managed in-app, stored in `unzipper_passwords.json`); every candidate is tried automatically
- **Delete after extraction** — optional; successfully extracted archives go to the Recycle Bin
- **Nested archive handling** — optional; archives inside archives are extracted too (up to 3 levels deep)
- **Background extraction** — runs on a worker thread, UI stays responsive
- **Archive type prefix in log** — `[ZIP]`, `[7Z]`, `[RAR]`, `[TAR.GZ]`
- **Color-coded status log** — green for success, red for errors, yellow for warnings
- **Dark forest green UI** — clean modern PyQt6 theme

---

## Download

Grab the latest `.exe` from the [`dist/`](dist/) folder — no Python install needed.

---

## Usage

1. Run `Unzipper.exe` (or `python unzipper.py`)
2. Set the **Source Folder** containing your archives
3. Set the **Destination Folder** where files will be extracted
4. *(Flat mode only)* Enter a base **Filename** — files will be numbered from that name
5. *(Optional)* Enter a **Password** for encrypted archives, or manage the saved password list via **Saved…**
6. *(Optional)* Tick **Delete archives after successful extraction** and/or **Extract nested archives**
7. Click **Unzip — Flat**, **Unzip — Keep Structure**, or **Test Archives**

---

## Modes Explained

| Mode | What it does |
|------|-------------|
| **Flat** | All files from all archives land in one folder, renamed `<Filename>_000001`, `_000002`, … |
| **Keep Structure** | Each archive gets its own subfolder; internal paths are preserved |
| **Test Archives** | Reads/CRC-checks every archive without writing any files |

---

## Build from Source

```bash
pip install pyinstaller
pyinstaller Unzipper.spec
# Output: dist/Unzipper.exe
```

The spec file carries the shared-venv ML-package excludes list — build with the spec, not a bare `pyinstaller unzipper.py`, or the EXE balloons.

---

## Requirements (source)

- Python 3.12+
- `PyQt6`
- `py7zr` (optional — required for `.7z` support)
- `rarfile` (optional — required for `.rar` support; also needs WinRAR or 7-Zip installed)
- `send2trash` (optional — Recycle Bin delete; falls back to permanent delete)

```bash
pip install PyQt6 py7zr rarfile send2trash
```

## Version History

### v1.3.0
- Password-protected archive support (password field + saved password list)
- RAR support via `rarfile` (WinRAR / 7-Zip backend auto-detected)
- Test Archives mode (verify without extracting)
- Optional delete-after-extraction (Recycle Bin)
- Nested archive handling (archive-in-archive, up to 3 levels)
- Extraction moved to a background thread; 7z flat-mode extraction bug fixed
- See [CHANGELOG.md](CHANGELOG.md) for details

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

- [x] Password-protected archive support (prompt or saved password list) — v1.3.0
- [x] RAR support via `rarfile` — v1.3.0
- [x] Test-only mode (verify archives without extracting) — v1.3.0
- [x] Delete archive after successful extraction (optional) — v1.3.0
- [x] Nested archive handling (zip inside zip) — v1.3.0

---

## License

MIT
