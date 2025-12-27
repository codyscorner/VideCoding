# File Copy Manager

A powerful tool for batch copying files with automatic duplicate numbering and flexible folder organization.

## Version 1.0.1

**Yellow & Black Theme** - Easy to distinguish from the red File Rename Mover!

## Features

### Core Features
- Batch copy files with automatic duplicate handling
- Preserve original folder structure OR organize by date
- Automatic duplicate file numbering (file_001.jpg, file_002.jpg, etc.)
- Yellow and black theme for easy visual identification
- Persistent configuration
- Dark theme UI optimized for 1000x870 resolution

### Copy Options

#### Preserve Folder Structure
- Keep the original folder hierarchy from source to destination
- Automatically creates necessary subfolders
- Perfect for backing up entire directory trees

#### Custom Folder Organization
When not preserving structure, organize files by:
- **Flat**: All files in destination folder
- **By Year**: `2025/file.jpg`
- **By Year/Month**: `2025/12/file.jpg`
- **By Year/Month/Day**: `2025/12/08/file.jpg`
- **By Date**: `2025-12-08/file.jpg`
- **By Month**: `2025-12/file.jpg`

#### Duplicate Handling
- **Number duplicates**: Automatically adds `_001`, `_002`, etc. to duplicate filenames
- **Skip duplicates**: Leave existing files untouched

## Project Structure

```
File Copy Manager/
├── main.py                      # Application entry point
├── config.py                    # Configuration management
├── file_operations.py           # File copying logic
├── folder_organization.py       # Folder structure management
├── ui/
│   ├── __init__.py
│   ├── main_window.py          # Main window UI
│   └── styles.py               # Yellow/Black theme
├── config.json                  # User configuration (auto-generated)
├── LICENSE                      # MIT License
└── README.md                    # This file
```

## Usage

### Running the Application

#### From Source
```bash
python main.py
```

### Basic Workflow

1. Select a source folder (where files currently are)
2. Select a destination folder (where to copy files)
3. Enter file extension to filter (e.g., `.jpg`, `.png`, `.pdf`)
4. Choose copy options:
   - Preserve folder structure (or use custom organization)
   - Number duplicates (or skip them)
5. Click "Copy Files"

### Example Use Cases

#### Use Case 1: Backup with Structure Preservation
**Goal:** Backup entire photo library maintaining folder structure

**Settings:**
- Preserve original folder structure: ✓
- Number duplicates: ✓

**Result:**
```
Destination/
  Vacation 2024/
    photo1.jpg
    photo2.jpg
  Family Events/
    wedding.jpg
```

#### Use Case 2: Consolidate by Date
**Goal:** Collect all photos into date-based folders

**Settings:**
- Preserve original folder structure: ✗
- Organize into: By Year/Month
- Number duplicates: ✓

**Result:**
```
Destination/
  2025/
    12/
      photo_001.jpg
      photo_002.jpg
    11/
      photo_003.jpg
```

#### Use Case 3: Flatten All Files
**Goal:** Copy all files to single folder with duplicate numbering

**Settings:**
- Preserve original folder structure: ✗
- Organize into: Flat
- Number duplicates: ✓

**Result:**
```
Destination/
  document.pdf
  document_001.pdf
  photo.jpg
  photo_001.jpg
```

## Configuration

Configuration is stored in `config.json` and includes:
- Default source folder
- Default destination folder
- Last used extension
- Preserve structure preference
- Folder organization structure
- Number duplicates preference

## Architecture

### Object-Oriented Design

The application follows SOLID principles:

#### 1. Configuration Management (`config.py`)
- **ConfigManager**: Handles loading, saving, and managing preferences
- JSON-based persistence

#### 2. File Operations (`file_operations.py`)
- **FileValidator**: Validates file paths and extensions
- **FileScanner**: Scans directories recursively or flat
- **FileCopier**: Handles copy operations with duplicate management
- **FileOperationResult**: Data class for operation results

#### 3. Folder Organization (`folder_organization.py`)
- **FolderOrganizer**: Manages destination folder structure
- **FolderStructure**: Enum for organization patterns
- Supports preserve mode and date-based hierarchies

#### 4. UI Components (`ui/`)
- **MainWindow**: Main application interface
- **ThemeManager**: Theme and styling management
- **YellowBlackTheme**: Yellow and black color scheme

## Differences from File Rename Mover

| Feature | File Rename Mover | File Copy Manager |
|---------|------------------|-------------------|
| **Operation** | Move & Rename | Copy |
| **Theme** | Red & Black | Yellow & Black |
| **Naming** | Multiple patterns | Keep original names |
| **Duplicates** | Prevent | Number automatically |
| **Structure** | Date-based only | Preserve OR date-based |
| **Use Case** | Organize files | Backup files |

## Requirements

### For Running from Source
- Python 3.7+
- tkinter (usually included with Python)
- No external dependencies required

## Benefits

1. **Safe Operations**: Copy (not move) means originals are preserved
2. **Flexible Organization**: Choose structure that fits your needs
3. **Automatic Numbering**: Never lose files due to duplicates
4. **Easy to Distinguish**: Yellow theme makes it visually distinct
5. **Fast**: Efficient file operations with progress feedback

## License

MIT License - See LICENSE file for details.

## Author

**Cody's Corner** - [@codyscorner](https://github.com/codyscorner)

## Contributing

Contributions with AI assistance by Claude (Anthropic)

## Version History

### v1.0.1 (December 8, 2025)
- Updated window size to 1000x870 (matches File Rename Mover)
- Fixed browse button visibility issues

### v1.0.0 (December 8, 2025)
- Initial release
- Batch file copying with duplicate numbering
- Preserve folder structure option
- Multiple folder organization patterns
- Yellow and black theme
- Configuration persistence

## Related Projects

- **File Rename Mover** - Companion tool for moving and renaming files with patterns
