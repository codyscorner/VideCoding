# Changelog

All notable changes to File Copy Manager will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.2.0] - 2026-06-28

### Changed
- File type preset dropdown entries sorted alphabetically (Archives, Audio, Code, Data, Documents, Images, Videos) in both the Single Source and Multi Source tabs

---

## [3.1.2] - 2026-06-21

### Fixed
- Preview → Proceed to Copy no longer re-scans the source folder; the file list determined during preview is passed directly to the copy engine, eliminating wasted iteration through files that were already known to be skippable

---

## [3.1.1] - 2026-06-21

### Fixed
- Preview window now respects Incremental backup mode — files already at the destination with matching size and mtime (±2 s) are excluded from the preview list, so only files that would actually be copied are shown

---

## [3.1.0] - 2026-06-21

### Added
- **Preview window** — "Preview" button scans files on a background thread and shows a sortable table (Filename / Size / Full Path) before any copy starts; user can cancel or proceed
- **MD5 checksum verification** — optional "Verify copied files" checkbox computes MD5 hash of source and destination after each copy; mismatches are logged and counted as errors
- **Incremental backup mode** — optional checkbox skips destination files that already match source by size and mtime (±2 s tolerance), avoiding redundant copies
- **Network path retry logic** — copy operations automatically retry up to 3 times with a 1.5 s delay on `OSError`, supporting UNC paths and slow network shares transparently

### Changed
- Copy Options section now includes Incremental and Verify Checksum checkboxes
- `incremental` and `verify_checksum` settings persisted to `config.json`
- `_start_copy` refactored into `_build_copy_options` + `_execute_copy` so the Preview flow can reuse the same copy path
- Status log now surfaces Retry attempts and CHECKSUM FAILED messages

### Technical
- Added `ui/preview_dialog.py` — `PreviewDialog(QDialog)` with sortable QTableWidget
- Added `_compute_checksum()` to `FileCopier` — MD5 in 4 MB chunks
- `FileOperationResult` extended with `checksum_verified: Optional[bool]`
- Preview scan runs on a daemon thread using the existing queue/QTimer pattern

---

## [2.0.1] - 2026-03-29

### Fixed
- Current File Progress bar now accurately shows progress for large files
- Files under 120 MB use fast `shutil.copy2` (progress flashes 0→100 as expected)
- Files 120 MB and over use a 4 MB chunked copy loop with real-time progress callbacks
- Chunked copy respects Cancel button mid-file
- Preserves file metadata (`copystat`) when using chunked copy

## [1.0.1] - 2025-12-08

### Changed
- Updated window size to 1000x870 (matches File Rename Mover for consistency)
- Updated minimum window size to prevent UI clipping
- Fixed browse button visibility issues

## [1.0.0] - 2025-12-08

### Added
- Initial release of File Copy Manager
- Batch file copying with extension filtering
- Preserve original folder structure option
- Custom folder organization options:
  - Flat (all files in one folder)
  - By Year, Year/Month, Year/Month/Day
  - By Date, By Month
- Automatic duplicate file numbering (file_001.jpg, file_002.jpg, etc.)
- Option to skip duplicates instead of numbering
- Yellow and black theme for easy visual distinction from File Rename Mover
- Configuration persistence (remembers last used settings)
- Real-time status logging
- Scrollable UI optimized for 900x700 resolution
- Comprehensive error handling and validation
- Type hints and docstrings throughout codebase

### Technical
- Object-oriented architecture with separation of concerns
- ConfigManager for JSON-based configuration persistence
- FileCopier for copy operations with duplicate handling
- FolderOrganizer for flexible folder structure management
- YellowBlackTheme for distinctive UI appearance
- Uses shutil.copy2 to preserve file metadata

---

## Version Numbering

- **Major** (X.0.0): Breaking changes, major rewrites
- **Minor** (1.X.0): New features, backward compatible
- **Patch** (1.0.X): Bug fixes, minor improvements
