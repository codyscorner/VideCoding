# File Rename Mover

A powerful, object-oriented tool for batch renaming and moving files with sequential numbering.

## Version 2.0.0

This version represents a complete refactoring into a modular, object-oriented architecture.

## Features

- Batch rename and move files with sequential numbering
- Automatic counter detection (continues from existing files)
- Dark theme UI with red accents
- Persistent configuration
- Settings dialog for default folders
- File validation and error handling

## Project Structure

```
File Rename Mover/
├── main.py                      # Application entry point
├── config.py                    # Configuration management
├── file_operations.py           # File handling logic
├── ui/
│   ├── __init__.py
│   ├── main_window.py          # Main application window
│   ├── settings_dialog.py      # Settings dialog
│   └── styles.py               # Theme management
├── file_rename_mover.py         # Legacy entry point (backward compatibility)
├── config.json                  # User configuration (auto-generated)
├── app_icon.ico                 # Application icon
└── README.md                    # This file
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
- **FileRenamer**: Handles move and rename operations
- **FileOperationResult**: Data class for operation results
- Separated business logic from UI

#### 3. UI Components (`ui/`)
- **MainWindow**: Main application interface
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
4. Enter rename pattern (e.g., `photo`, `document`)
5. Click "Move and Rename"

### File Naming Convention

Files are renamed with the pattern: `{pattern}_{counter}_{extension}`

Example: `photo_000001_.jpg`, `photo_000002_.jpg`, etc.

The counter automatically continues from existing files in the destination folder.

## Configuration

Configuration is stored in `config.json` and includes:
- Default source folder
- Default destination folder
- Last used extension
- Last used rename pattern

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

## Future Enhancement Ideas

- [ ] Preview mode before moving files
- [ ] Undo functionality
- [ ] Multiple rename patterns/rules
- [ ] File filtering by date, size, etc.
- [ ] Custom sorting options
- [ ] Drag-and-drop support
- [ ] Progress bar for large operations
- [ ] Export/import rename rules
- [ ] Command-line interface
- [ ] Batch operation history

## Benefits of the Refactoring

1. **Testability**: Each component can be unit tested independently
2. **Maintainability**: Clear separation makes code easier to understand
3. **Extensibility**: New features can be added without modifying existing code
4. **Reusability**: File operations can be used in other contexts (CLI, web, etc.)
5. **Type Safety**: Better type hints and documentation
6. **Error Handling**: Centralized validation and error management

## Requirements

- Python 3.7+
- tkinter (usually included with Python)

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

[Your License Here]

## Author

[Your Name Here]

## Version History

- **2.0.0** (2025-11-27): Complete refactoring to object-oriented architecture
- **1.2.4**: Last monolithic version
