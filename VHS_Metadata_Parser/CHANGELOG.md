# Changelog

## v1.2.0 — 2026-07-08
- New **Batch / Search** tab: scan a folder (optionally recursive) for `.mp4`/`.json`/`.txt` metadata files on a background `QThread`, with a live progress status label.
- Summary table per scanned file: filename, width, height, length, frame rate, format, sampler steps/CFG/name, LoRA names, UNET names.
- Live search box filters the batch table by filename, LoRA/model name, sampler, or prompt text — answers "which videos used LoRA X?".
- Diff view: select exactly two rows (Ctrl+Click) and click "Diff Selected" to open a dialog comparing key metadata fields side by side, with differing fields highlighted.
- "Export Summary CSV" writes the currently filtered batch table to a CSV file.
- Double-click a batch row to load that file into the main single-file viewer tabs.
- Added a `summarize_file()` helper and `row_matches_search()` used by both the batch table and search filter.
- `VHS_Metadata_Parser.spec` gained an `excludes` list for shared-venv ML packages (torch, cv2, numpy, etc.) to keep the EXE small.

## v1.1.1 (pre-existing, undocumented)
- Version bump only; no changelog entry existed prior to this file.

## v1.1.0
- Migrated from PyQt5 to PyQt6.
- Dark blue-green theme applied throughout.
- Updated all Qt6 enum flags (ResizeMode, EditTrigger, etc.).

## v1.0.0
- Initial release with PyQt5.
- Tabbed metadata viewer.
- Drag & drop and file browser support.
