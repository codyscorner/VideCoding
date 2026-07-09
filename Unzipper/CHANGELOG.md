# Changelog — Unzipper

## v1.3.0 — 2026-07-08

### Added
- **RAR support** via `rarfile` — auto-detects an extraction backend: `unrar` on PATH, WinRAR's `UnRAR.exe`, or 7-Zip's `7z.exe` (standard install paths checked). Logs a warning and skips `.rar` files if no backend is found.
- **Password-protected archive support** (ZIP, 7Z, RAR) — optional password field (tried first) plus a saved password list (`unzipper_passwords.json` next to the app, managed via the "Saved…" dialog). All candidates are tried automatically; a clear error is logged if none work.
- **Test Archives mode** — verifies every archive in the source folder (CRC / full-read check per format) without extracting anything. Destination folder not required.
- **Delete after extraction** (optional checkbox) — archives that extracted without errors are sent to the Recycle Bin (`send2trash`; falls back to permanent delete if unavailable). Failed archives are always kept.
- **Nested archive handling** (optional checkbox) — archives found inside extracted output are extracted too (flat mode: continues the sequential numbering; structured mode: into a subfolder next to the nested archive), then the inner archive file is deleted. Depth-limited to 3 levels.

### Changed
- Extraction now runs on a background `QThread` — the UI stays responsive and action buttons disable while a job runs.
- Extraction engine refactored into UI-independent module-level functions (`run_flat` / `run_structured` / `run_test`) for testability.
- Archive listing is now sorted alphabetically and skips directories whose names look like archives.
- `tarfile` extraction uses the Python 3.12 `filter="data"` safety filter in structured mode.
- Window height increased to fit the new password/options rows.

### Fixed
- 7z flat mode previously extracted with internal paths into the destination and renamed files afterwards, leaving behind empty directory trees and failing on multi-file archives (py7zr requires a reset between successive `extract()` calls). Now extracts to a temp folder and moves files out.

### Build
- `Unzipper.spec`: added `py7zr`, `rarfile`, `send2trash` hiddenimports and the standard shared-venv ML-package excludes list (torch/tensorflow/cv2/numpy/etc.) to keep the EXE small.

## v1.2.0

- Added 7Z support via `py7zr` (graceful skip with warning if not installed)
- Added TAR.GZ / TGZ support via stdlib `tarfile`
- Both flat and structured modes now scan for `.zip`, `.7z`, `.tar.gz`, `.tgz`
- Log lines show archive type prefix: `[ZIP]`, `[7Z]`, `[TAR.GZ]`

## v1.1.0

- Initial release: ZIP-only batch extraction
- Flat mode and Keep Structure mode
- Sequential renaming, duplicate folder suffixing
