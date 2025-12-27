# File Copy Manager - Features

## Overview

File Copy Manager is a companion tool to File Rename Mover, designed specifically for **copying** files rather than moving/renaming them. It features a distinctive **yellow and black theme** for easy visual identification.

---

## Core Features

### 1. Batch File Copying
- Copy multiple files at once based on file extension
- Safe operation - originals are never modified or deleted
- Real-time status updates during operation
- Error handling with detailed logging

### 2. Folder Structure Options

#### Preserve Original Structure
When enabled, maintains the exact folder hierarchy from source to destination:
```
Source/
  Photos/
    2024/
      vacation.jpg
  Documents/
    report.pdf

Destination/
  Photos/
    2024/
      vacation.jpg
  Documents/
    report.pdf
```

#### Custom Organization
When preserve mode is disabled, organize files by date:

- **Flat**: All files in one folder
  ```
  Destination/
    file1.jpg
    file2.jpg
  ```

- **By Year**: `2025/file.jpg`
- **By Year/Month**: `2025/12/file.jpg`
- **By Year/Month/Day**: `2025/12/08/file.jpg`
- **By Date**: `2025-12-08/file.jpg`
- **By Month**: `2025-12/file.jpg`

### 3. Duplicate File Handling

#### Number Duplicates (Recommended)
Automatically adds sequential numbers to duplicate files:
```
Original files:
  photo.jpg (in source)
  photo.jpg (already in destination)

Result:
  photo.jpg (original in destination, untouched)
  photo_001.jpg (newly copied)
  photo_002.jpg (if another duplicate exists)
```

#### Skip Duplicates
Leaves existing files untouched and skips copying:
```
photo.jpg exists in destination → Skip copying
```

---

## User Interface

### Yellow & Black Theme
- **Background**: Black (#1a1a1a)
- **Foreground**: Gold (#FFD700)
- **Buttons**: Yellow background with black text
- **Easy Distinction**: Visually different from red File Rename Mover

### Layout
- **Window Size**: 900x700 pixels
- **Scrollable**: Handles all controls without clipping
- **Status Log**: Real-time feedback on operations
- **Persistent Settings**: Remembers last used configuration

---

## Use Cases

### Use Case 1: Complete Backup
**Scenario**: Backup entire photo library to external drive

**Settings**:
- Preserve original folder structure: ✓
- Number duplicates: ✓

**Benefits**:
- Maintains organization
- Can run multiple times safely (duplicates numbered)
- Originals never touched

### Use Case 2: Consolidate by Date
**Scenario**: Collect scattered photos into date-based folders

**Settings**:
- Preserve original folder structure: ✗
- Organize into: By Year/Month
- Number duplicates: ✓

**Benefits**:
- All photos organized chronologically
- Easy to find photos by date
- No duplicates lost

### Use Case 3: Flatten Collection
**Scenario**: Copy all PDFs from nested folders into one folder

**Settings**:
- Preserve original folder structure: ✗
- Organize into: Flat
- Number duplicates: ✓

**Benefits**:
- All files in one place
- Duplicates automatically numbered
- Simple, flat structure

---

## Technical Features

### Safe Operations
- Uses `shutil.copy2` to preserve file metadata (timestamps, permissions)
- Creates destination folders automatically
- Never modifies source files
- Validates inputs before operation

### Performance
- Efficient file scanning (recursive when needed)
- Progress feedback during operations
- Handles large file sets
- Minimal memory usage

### Error Handling
- Validates folder existence
- Checks for invalid extensions
- Reports errors without stopping operation
- Clear error messages

---

## Configuration Persistence

Automatically saves and restores:
- Last used source folder
- Last used destination folder
- Last used file extension
- Preserve structure preference
- Folder organization structure
- Number duplicates preference

Stored in `config.json` in the application directory.

---

## Comparison with File Rename Mover

| Feature | File Rename Mover | File Copy Manager |
|---------|------------------|-------------------|
| **Primary Action** | Move & Rename | Copy Only |
| **File Naming** | Multiple patterns | Keep original |
| **Duplicate Strategy** | Prevent/Error | Number or Skip |
| **Folder Options** | Date-based only | Preserve OR Date-based |
| **Theme Color** | Red & Black | Yellow & Black |
| **Best For** | Organizing files | Backing up files |
| **Safety** | Moves originals | Copies (originals safe) |

---

## Future Enhancement Ideas

- [ ] Preview window showing all copy operations before execution
- [ ] Size-based filtering (only copy files > X MB)
- [ ] Date range filtering (only copy files from date range)
- [ ] Progress bar for large operations
- [ ] Copy operation history/logging to file
- [ ] Verify copied files (checksum comparison)
- [ ] Incremental backup mode (only copy new/changed files)
- [ ] Exclude patterns (don't copy certain files)
- [ ] Command-line interface
- [ ] Batch profiles (save/load copy configurations)

---

## Technical Architecture

### Modules

**config.py** - Configuration Management
- JSON-based persistence
- Default values
- Get/set/update methods

**file_operations.py** - Core Copy Logic
- `FileCopier`: Main copy operations
- `FileScanner`: Directory scanning
- `FileValidator`: Input validation
- Duplicate numbering logic

**folder_organization.py** - Folder Structures
- `FolderOrganizer`: Subfolder creation
- `FolderStructure`: Organization patterns enum
- Preserve mode support

**ui/main_window.py** - Main Interface
- Source/destination selection
- Options configuration
- Status logging
- Operation execution

**ui/styles.py** - Theme Management
- `YellowBlackTheme`: Color scheme
- `ThemeManager`: Theme application
- Consistent styling

---

## Benefits

1. **Safe Backups**: Never lose original files
2. **Flexible Organization**: Choose structure that fits your workflow
3. **Duplicate Protection**: Never overwrite or lose duplicate files
4. **Visual Identity**: Yellow theme makes it easy to find
5. **Simple UI**: Intuitive controls, minimal learning curve
6. **Reliable**: Comprehensive error handling
7. **Fast**: Efficient file operations
8. **Persistent**: Remembers your preferences

---

## Best Practices

### For Backups
- Enable "Preserve original folder structure"
- Enable "Number duplicates"
- Use specific extensions to avoid copying unwanted files

### For Organization
- Disable "Preserve original folder structure"
- Choose appropriate date-based organization
- Enable "Number duplicates" to keep all versions

### For Testing
- Start with small source folder
- Check destination after first run
- Verify duplicates are handled as expected

---

## Version 1.0.0 Release Notes

Initial release includes:
- Complete batch copying functionality
- Two folder organization modes (preserve/custom)
- Automatic duplicate numbering
- Yellow and black theme
- Configuration persistence
- Comprehensive error handling
- Clean, modern UI
- Professional documentation
