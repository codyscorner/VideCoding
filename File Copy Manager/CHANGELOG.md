# Changelog

All notable changes to File Copy Manager will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
