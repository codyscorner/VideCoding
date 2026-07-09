# Changelog

All notable changes to Video Drop Player are documented in this file.

## 2026-07-08 — v1.4.0

### Added
- Remember last position per file (resumes on next play; skipped for videos barely started or already finished), persisted to `video_drop_player_config.json`
- A-B loop for a section (`[` sets loop start, `]` sets loop end and activates the loop, `L` clears it)
- Screenshot current frame (`C` key, saved as PNG to a `Screenshots` subfolder next to the source video)
- Delete-current-file hotkey (`Delete`, confirmation prompt, sends to Recycle Bin via `send2trash`, works in both video and image mode)

### Changed
- Noted in docs that playback speed control (`S` key) already existed prior to this pass

## Earlier
- See git history prior to 2026-07-08 for v1.0.0 - v1.3.2 changes (no changelog was kept before this release).
