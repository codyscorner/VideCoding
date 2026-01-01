# File Copy Manager v1.1.0 - Changelog

## Release Date
January 1, 2026

## New Features

### 1. Progress Bars and Real-time Feedback
- **Overall Progress Bar**: Shows the total progress of all files being copied
- **Current File Progress Bar**: Displays progress for the individual file being copied
- **Progress Label**: Real-time status showing current file being processed (e.g., "Processing 5/20: example.jpg")
- Visual feedback helps users track copy operations, especially for large batches

### 2. File Filtering Options
- **Size Filter**: Filter files by minimum and maximum size
  - Supports multiple units: Bytes, KB, MB, GB
  - Can set minimum only, maximum only, or both
  - Example: Copy only files between 1 MB and 50 MB

- **Date Filter**: Filter files by age
  - Specify files modified within the last X days
  - Useful for copying recent files only
  - Example: Copy only files modified in the last 30 days

- Both filters can be enabled/disabled independently
- Filter settings are saved in configuration for next use

### 3. Enhanced Status Window
- **File Size Display**: Each copied file now shows its size in human-readable format
  - Automatically formats as B, KB, MB, GB, TB, or PB
  - Example: "Copied: photo.jpg (2.45 MB, 0.12s)"

- **Copy Time Display**: Shows how long each file took to copy
  - Displayed in seconds with 2 decimal places
  - Helps identify slow copies or performance issues

- **Filter Statistics**: Displays how many files were filtered out
  - Example: "Filtered out 15 files based on filter criteria"

## Technical Improvements

### Code Changes
- Added `progress_callback` parameter to `FileCopier` class
- Enhanced `FileOperationResult` dataclass with `file_size` and `copy_time` fields
- New `_apply_filters()` method for efficient file filtering
- New `_format_file_size()` method for human-readable size formatting
- Progress tracking integrated into file copy loop
- Filter configuration persistence in config.json

### UI Enhancements
- New progress section with two progress bars
- New filter options section with collapsible inputs
- Filter inputs only visible when filters are enabled
- Improved visual feedback during operations
- Window remains responsive during copy operations

### Performance
- Filters applied before copying to avoid unnecessary operations
- Efficient file size and date checking
- Progress updates use `update_idletasks()` for smooth UI

## Files Modified
- `main.py`: Updated version to 1.1.0
- `ui/main_window.py`: Added progress bars, filter UI, and progress callbacks
- `file_operations.py`: Added filtering logic, size/time tracking, progress support
- `config.py`: (No changes, but stores new filter settings)
- `FileCopyManager.spec`: Created PyInstaller spec file

## Build
- Created standalone executable: `FileCopyManager.exe`
- Located in: `dist/FileCopyManager.exe`
- Single-file executable with no external dependencies
- Console disabled for clean Windows application

## Configuration
New configuration keys added:
- `enable_size_filter`: Boolean
- `min_size`: String (numeric value)
- `max_size`: String (numeric value)
- `size_unit`: String (B, KB, MB, GB)
- `enable_date_filter`: Boolean
- `days_old`: String (numeric value)

## Usage Examples

### Example 1: Copy Recent Large Files
1. Select source and destination folders
2. Enter file extension (e.g., `.mp4`)
3. Enable "Filter by file size"
   - Min: 100 MB
   - Max: (leave empty for no limit)
4. Enable "Filter by file age"
   - Modified within last: 7 days
5. Click "Copy Files"

### Example 2: Copy Small Images Only
1. Select folders and enter `.jpg` extension
2. Enable "Filter by file size"
   - Min: 0
   - Max: 5 MB
3. Click "Copy Files"

## Known Issues
None reported

## Future Enhancements
Potential features for future versions:
- Multi-extension support (e.g., `.jpg,.png,.gif`)
- Preview mode (show what will be copied without copying)
- Pause/Resume functionality
- Speed limiting for network copies
- Custom filter expressions
- File hash verification
- Batch queue management

## Upgrade Notes
- Fully backward compatible with v1.0.1
- Existing config.json files will work without modification
- New filter settings start disabled by default
- No breaking changes
