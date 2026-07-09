# Changelog

All notable changes to Video Converter are documented in this file.

## 2026-07-08 — v1.1.0

### Added
- Per-file progress percent parsed from ffmpeg's stderr output, shown in the Status column
- Custom preset editor (codec, CRF/bitrate, width) with saved custom presets
- Trim on convert (Start/End time fields, `-ss`/`-t`)
- Recursive folder scan option ("Include subfolders" checkbox)
- Parallel conversions with a configurable worker cap (1-8)

### Changed
- `ConversionWorker` now runs jobs through a `ThreadPoolExecutor`; overall progress reflects completed jobs rather than started jobs

## 2026-07-07

### Added
- `app_icon.ico` committed to the repo — the icon was already referenced by `main.py` and `build_exe.py` but the asset itself was missing from version control.
