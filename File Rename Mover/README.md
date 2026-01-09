# File Rename Mover

A powerful, object-oriented tool for batch renaming and moving files with sequential numbering.

## Version 2.1.7

Enhanced version with advanced rename patterns, sorting options, folder organization features, and improved security.

## Features

### Core Features
- Batch rename and move files with sequential numbering
- Automatic counter detection (continues from existing files)
- Dark theme UI with red accents (1000x870 optimized window)
- Persistent configuration
- Settings dialog for default folders
- File validation and error handling

### Advanced Features (v2.1+)
- **Multiple Rename Patterns**:
  - Sequential numbering
  - DateTime-based naming (multiple formats)
  - Prefix mode (keep original names)
  - Custom patterns with placeholders

- **Sorting Options**:
  - Sort by name, date modified, date created, or size
  - Ascending or descending order

- **Folder Organization**:
  - Flat structure (all files in one folder)
  - Organize by year, year/month, year/month/day
  - Organize by date or month

- **Standalone Executable**: No Python installation required

## Project Structure

```
File Rename Mover/
├── main.py                      # Application entry point (v2.1+)
├── config.py                    # Configuration management
├── file_operations.py           # File handling logic
├── rename_patterns.py           # Rename pattern strategies
├── sorting.py                   # File sorting logic
├── folder_organization.py       # Folder structure management
├── ui/
│   ├── __init__.py
│   ├── main_window_v2.py       # Enhanced main window (v2.1+)
│   ├── main_window.py          # Legacy main window
│   ├── settings_dialog.py      # Settings dialog
│   └── styles.py               # Theme management
├── dist/
│   └── FileRenameMover.exe     # Standalone executable
├── FileRenameMover.spec         # PyInstaller build configuration
├── file_rename_mover.py         # Legacy entry point (backward compatibility)
├── config.json                  # User configuration (auto-generated)
├── app_icon.ico                 # Application icon
├── LICENSE                      # MIT License
├── README.md                    # This file
├── CHANGELOG.md                 # Version history details
└── FEATURES_v2.1.md            # Detailed feature documentation
```

## Architecture Overview

### Object-Oriented Design

The application follows SOLID principles and is organized into several key components:

#### 1. Configuration Management (`config.py`)
- **ConfigManager**: Handles loading, saving, and managing user preferences
- JSON-based persistence
- Default configuration with validation

#### 2. File Operations (`file_operations.py`)
- **FileValidator**: Validates file paths, extensions, and patterns
- **FileScanner**: Scans directories and finds files
- **FileRenamer**: Handles move and rename operations with pattern support
- **FileOperationResult**: Data class for operation results
- Separated business logic from UI

#### 3. Rename Patterns (`rename_patterns.py`)
- **PatternFactory**: Creates pattern strategies
- **NumberingPattern**: Sequential numbering (001, 002, etc.)
- **DateTimePattern**: Date/time-based naming with multiple formats
- **PrefixPattern**: Add prefix while keeping original names
- **CustomPattern**: User-defined patterns with placeholders

#### 4. Sorting (`sorting.py`)
- **FileSorter**: Sorts files by various criteria
- **SortBy**: Enum for sort criteria (name, date, size)
- **SortOrder**: Enum for sort direction (ascending, descending)

#### 5. Folder Organization (`folder_organization.py`)
- **FolderOrganizer**: Manages destination folder structure
- **FolderStructure**: Enum for organization patterns
- Supports year, month, date-based folder hierarchies

#### 6. UI Components (`ui/`)
- **MainWindowV2**: Enhanced main application interface (v2.1+)
- **MainWindow**: Legacy main window
- **SettingsDialog**: Settings configuration dialog
- **ThemeManager**: Theme and styling management
- **DarkRedTheme**: Current theme implementation

### Design Patterns Used

1. **Separation of Concerns**: UI, business logic, and configuration are separate
2. **Dependency Injection**: Components receive dependencies through constructors
3. **Callback Pattern**: Status updates via callbacks
4. **Data Classes**: Structured result objects
5. **Strategy Pattern**: Theme system allows easy theme switching

## Usage

### Running the Application

#### Option 1: Standalone Executable (Recommended)
```bash
# Windows - No Python required!
dist\FileRenameMover.exe
```

#### Option 2: From Source
```bash
python main.py
```

Or for backward compatibility:
```bash
python file_rename_mover.py
```

### Basic Workflow

1. Select a source folder (where files currently are)
2. Select a destination folder (where to move files)
3. Enter file extension to filter (e.g., `.jpg`, `.png`)
4. Enter base name (e.g., `photo`, `document`)
5. Choose rename pattern (numbering, datetime, prefix, custom)
6. Select sorting options (optional)
7. Choose folder organization structure (optional)
8. Click "Move and Rename"

### File Naming Examples

#### Sequential Numbering (Default)
- `photo_000001.jpg`, `photo_000002.jpg`, etc.

#### DateTime Pattern
- `photo_20251127.jpg` (YYYYMMDD format)
- `photo_2025_11_27.jpg` (YYYY_MM_DD format)
- `photo_20251127_143052.jpg` (YYYYMMDD_HHMMSS format)
- With counter: `photo_20251127_001.jpg`

#### Prefix Pattern
- `photo_original_name1.jpg`, `photo_original_name2.jpg`

#### Custom Pattern
- Template: `{year}_{month}_{counter}` → `2025_11_001.jpg`
- Available placeholders: `{counter}`, `{date}`, `{time}`, `{datetime}`, `{year}`, `{month}`, `{day}`, `{original}`

### Folder Organization Examples

- **Flat**: All files in destination folder
- **By Year**: `2025/photo_001.jpg`
- **By Year/Month**: `2025/11/photo_001.jpg`
- **By Year/Month/Day**: `2025/11/27/photo_001.jpg`
- **By Date**: `2025-11-27/photo_001.jpg`
- **By Month**: `November/photo_001.jpg`

## Configuration

Configuration is stored in `config.json` and includes:
- Default source folder
- Default destination folder
- Last used extension
- Last used base name
- Rename pattern type
- DateTime format preference
- Sorting preferences (sort by, order)
- Folder organization structure
- Custom pattern template
- Include counter preference

## Adding New Features

The modular architecture makes it easy to add new features:

### Example: Adding a New File Operation

1. Add method to `FileRenamer` class in `file_operations.py`
2. Add UI controls in `MainWindow` in `ui/main_window.py`
3. Wire up event handler to call the new method

### Example: Adding a Preview Feature

```python
# Already implemented in FileRenamer class!
preview = file_renamer.generate_preview(
    source_folder,
    extension,
    rename_pattern,
    dest_folder
)
# Returns list of (original_name, new_name) tuples
```

### Example: Adding a New Theme

1. Create new theme class in `ui/styles.py` inheriting from `Theme`
2. Define colors and fonts
3. Implement `apply_to_style()` method
4. Add to `ThemeManager.THEMES` dictionary

## Completed Features (v2.1.3)

- [x] Multiple rename patterns (numbering, datetime, prefix, custom)
- [x] Custom sorting options (name, date, size)
- [x] Folder organization by date/time hierarchies
- [x] Standalone executable distribution
- [x] Advanced pattern configuration
- [x] Real-time example preview

## Future Enhancement Ideas

- [ ] Preview mode showing all changes before execution
- [ ] Undo functionality
- [ ] File filtering by date range, size range
- [ ] Drag-and-drop support
- [ ] Progress bar for large operations
- [ ] Export/import rename rules/presets
- [ ] Command-line interface
- [ ] Batch operation history/logging
- [ ] Duplicate file detection
- [ ] Regex-based pattern matching

## Benefits of the Refactoring

1. **Testability**: Each component can be unit tested independently
2. **Maintainability**: Clear separation makes code easier to understand
3. **Extensibility**: New features can be added without modifying existing code
4. **Reusability**: File operations can be used in other contexts (CLI, web, etc.)
5. **Type Safety**: Better type hints and documentation
6. **Error Handling**: Centralized validation and error management

## Requirements

### For Standalone Executable
- Windows 10 or later
- No additional requirements!

### For Running from Source
- Python 3.7+
- tkinter (usually included with Python)
- No external dependencies required

### For Building Executable
- PyInstaller 6.0+
```bash
pip install pyinstaller
pyinstaller --clean --noconfirm FileRenameMover.spec
```

## Development

### Running Tests (when implemented)

```bash
python -m pytest tests/
```

### Code Style

- Follow PEP 8
- Use type hints
- Document classes and methods with docstrings
- Keep functions focused and small

## License

MIT License - See [LICENSE](LICENSE) file for details.

## Author

**Cody's Corner** - [@codyscorner](https://github.com/codyscorner)

## Contributing

Contributions with AI assistance by Claude (Anthropic)

## Version History

### v2.1.7 (January 9, 2026)
- Fixed config initialization bug (ConfigManager._load calling save before _config existed)
- Fixed counter scanning to search all subfolders for existing files
- Proper icon loading for PyInstaller frozen executables
- Distribution zip package for easy deployment

### v2.1.4 (December 8, 2025)
- Fixed filename formatting (removed trailing underscore)
- Fixed preview generation to use current pattern strategy
- Added comprehensive filename validation and sanitization
- Added security protections (path traversal, invalid characters, reserved names)
- Improved error messages and validation

### v2.1.3 (November 27, 2025)
- Updated window size to 1000x870 for optimal UI layout
- Built standalone executable with PyInstaller
- Added MIT License
- Updated build configuration
- Enhanced documentation

### v2.1.2 (November 27, 2025)
- Added multiple rename patterns (numbering, datetime, prefix, custom)
- Implemented advanced sorting options
- Added folder organization features
- Enhanced UI with pattern preview
- Added custom pattern support with placeholders

### v2.0.0 (November 27, 2025)
- Complete refactoring to object-oriented architecture
- Modular design with separation of concerns
- Enhanced maintainability and extensibility

### v1.2.4 (Earlier)
- Last monolithic version

## Additional Documentation

- [CHANGELOG.md](CHANGELOG.md) - Detailed version history
- [FEATURES_v2.1.md](FEATURES_v2.1.md) - Feature documentation
- [LICENSE](LICENSE) - MIT License terms
