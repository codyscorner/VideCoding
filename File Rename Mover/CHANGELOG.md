# Changelog

All notable changes to File Rename Mover will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.1] - 2025-11-27

### Fixed
- Fixed SortBy enum conversion bug that caused "not a valid SortBy" error when using date_created or date_modified sorting
- Fixed folder path separators to use Windows backslashes (\\) instead of forward slashes (/) in UI examples
- Improved same-folder operation handling to properly distinguish between rename and move operations

### Added
- Added duplicate file checking to prevent overwriting existing files
- Added skip logic for files that already have the target name
- Enhanced status logging to show "Renamed:" vs "Moved:" for clarity

### Changed
- Improved error messages for file operation failures
- Better path handling for Windows-specific operations

## [2.1.0] - 2025-11-27

### Added
- **Custom Sorting Options**
  - Sort by: Name, Date Modified, Date Created, Size
  - Sort order: Ascending or Descending
- **Multiple Rename Patterns**
  - Numbering Pattern (simple sequential)
  - DateTime Pattern (various date/time formats)
  - Prefix Pattern (keep original names with prefix)
  - Custom Pattern (user-defined with placeholders)
- **Folder Organization**
  - Flat (no subfolders)
  - By Year (YYYY/)
  - By Year/Month (YYYY/MM/)
  - By Year/Month/Day (YYYY/MM/DD/)
  - By Date (YYYY-MM-DD/)
  - By Month (YYYY-MM/)
- New modules: `sorting.py`, `rename_patterns.py`, `folder_organization.py`
- Enhanced main window (main_window_v2.py) with all new controls
- Scrollable interface for better usability
- Live preview of rename patterns and folder structures
- Configuration persistence for all new settings

### Changed
- Window size increased to 900x750 to accommodate new features
- Enhanced FileRenamer class with pattern and sorting support
- Extended ConfigManager with new preference fields

## [2.0.0] - 2025-11-27

### Added
- Complete refactoring to object-oriented architecture
- Modular project structure with separate concerns
- `config.py` - Configuration management with JSON persistence
- `file_operations.py` - File handling business logic
  - FileValidator - Input validation
  - FileScanner - Directory scanning
  - FileRenamer - Move and rename operations
- `ui/` package for UI components
  - `main_window.py` - Main application window
  - `settings_dialog.py` - Settings dialog
  - `styles.py` - Theme management system
- Theme management with ThemeManager and DarkRedTheme
- Comprehensive error handling and validation
- Type hints and docstrings throughout codebase
- Preview functionality (generate_preview method)

### Changed
- Reorganized from single 445-line file to modular architecture
- Improved separation of UI and business logic
- Enhanced configuration system with defaults
- Better code maintainability and testability

### Maintained
- Backward compatibility with v1.2.4 configurations
- Original dark red theme and UI aesthetics
- All existing functionality preserved

## [1.2.4] - Previous Release

### Features
- Basic file rename and move functionality
- Sequential numbering with 6-digit counters
- Configuration persistence (source/dest folders, extension, rename pattern)
- Dark red theme UI
- Settings dialog for default folders
- Status logging
- Counter continuation from existing files

---

## Version Numbering

- **Major** (X.0.0): Breaking changes, major rewrites
- **Minor** (2.X.0): New features, backward compatible
- **Patch** (2.1.X): Bug fixes, minor improvements
