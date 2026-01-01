# File Copy Manager

A powerful tool for batch copying files with automatic duplicate numbering and flexible folder organization.

## Version 1.2.0

**Yellow & Black Theme** - Easy to distinguish from the red File Rename Mover!

### What's New in v1.2.0
- **File Pattern Filtering**: Support for wildcard patterns (*.jpg, *.png) and multiple patterns
- **Backward Compatible**: Old extension format (.jpg) automatically converts to patterns (*.jpg)
- **Enhanced Pattern Matching**: Uses fnmatch for flexible file matching

### What's New in v1.1.0
- **Dual Progress Bars**: Real-time overall and per-file progress tracking
- **File Size Filtering**: Filter files by minimum/maximum size (B, KB, MB, GB)
- **File Age Filtering**: Copy only files modified within the last X days
- **Enhanced Status Display**: Shows file size and copy time for each file
- **Improved UI**: Tighter, more compact layout for better usability

## Features

### Core Features
- Batch copy files with automatic duplicate handling
- **Real-time progress bars** (overall and per-file)
- **File size and copy time tracking** in status window
- Preserve original folder structure OR organize by date
- Automatic duplicate file numbering (file_001.jpg, file_002.jpg, etc.)
- **Advanced filtering** by file size and age
- Recursive subfolder scanning
- Yellow and black theme for easy visual identification
- Persistent configuration
- Dark theme UI optimized for 1000x870 resolution

### File Filters (New in v1.1.0)

#### Size Filter
- Filter files by minimum and maximum size
- Supports multiple units: B, KB, MB, GB
- Example: Copy only files between 1 MB and 100 MB

#### Date Filter
- Filter by file age (modification date)
- Copy only files modified within the last X days
- Example: Copy only files from the last 30 days

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
3. Enter file pattern(s) to filter (e.g., `*.jpg`, `*.png, *.pdf`, `image*.jpg`)
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

## File Pattern Matching

### Supported Patterns
The application supports flexible file pattern matching:

- **Single pattern**: `*.jpg` - Match all JPG files
- **Multiple patterns**: `*.jpg, *.png, *.pdf` - Match multiple file types
- **Prefix wildcard**: `image*.jpg` - Match files starting with "image"
- **Single character wildcard**: `photo_?.png` - Match photo_1.png, photo_2.png, etc.
- **Legacy format**: `.jpg` - Automatically converts to `*.jpg`

### Pattern Examples
- `*.mp3` - All MP3 files
- `*.jpg, *.png, *.gif` - All image files (JPG, PNG, GIF)
- `report*.pdf` - PDFs starting with "report"
- `data_????.csv` - CSV files with exactly 4 characters after "data_"

## Configuration

Configuration is stored in `config.json` and includes:
- Default source folder
- Default destination folder
- Last used file pattern (automatically migrates old extensions to patterns)
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

### v1.2.0 (January 1, 2026)
- **File Pattern Filtering**: Added wildcard pattern support (*.jpg, *.png)
- **Multiple Patterns**: Support for comma-separated patterns (*.jpg, *.png, *.pdf)
- **Pattern Migration**: Automatic conversion of old extension format to patterns
- **Enhanced Validation**: Updated FileValidator for pattern validation
- Updated UI labels and examples to reflect pattern filtering

### v1.1.0 (December 2025)
- **Dual Progress Bars**: Real-time overall and per-file progress tracking
- **File Size Filtering**: Filter files by minimum/maximum size (B, KB, MB, GB)
- **File Age Filtering**: Copy only files modified within the last X days
- **Enhanced Status Display**: Shows file size and copy time for each file
- **Improved UI**: Tighter, more compact layout for better usability

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
