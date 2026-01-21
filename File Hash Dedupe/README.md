# File Hash Dedupe

A desktop application that finds and moves duplicate files based on content hash (MD5).

## Features

- **Fast Parallel Hashing**: Uses 16 parallel workers for high-speed file hashing
- **Content-Based Detection**: Identifies duplicates by file content, not just filename
- **Safe Operation**: Moves duplicates to a `Dupes` subfolder (doesn't delete)
- **Recursive Scanning**: Option to scan subdirectories
- **Progress Tracking**: Real-time progress bar and status log
- **Dark Green Theme**: Modern dark-themed interface

## Usage

1. **Select Source Folder**: Browse to the folder to scan for duplicates
2. **Configure Options**: Check "Search subfolders recursively" if needed
3. **Click "Find Duplicates"** to begin processing

### Output

- First occurrence of each unique file stays in place (primary)
- All duplicates are moved to `Source Folder/Dupes/`
- Review the Dupes folder and delete when satisfied

## Requirements

- Python 3.10+

## Installation

No additional dependencies required - uses Python standard library only.

## Building Executable

```bash
pip install pyinstaller
pyinstaller --onedir --windowed --name FileHashDedupe main.py
```

## Version

1.0.0
