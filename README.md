# VideCoding Projects

A collection of utility tools and games developed for file management, image processing, and entertainment.

## 📦 Projects Overview

### 🎬 Desktop Video Browser
**Version:** 1.0.0 | **Status:** Active Development | **Language:** Python

A fast, lightweight desktop video browser with an embedded player for quick file previewing.

**Features:**
- Split-pane layout — file list left, video player right
- Open folder via button or drag-and-drop
- Refresh file list without closing the app (files never locked between plays)
- Arrow key navigation (Up/Down) to step through videos automatically
- Play/Pause (Space), Stop, Fullscreen (F / Esc) keyboard shortcuts
- Toolbar with play/pause/stop/fullscreen buttons
- Live time display (current position / total duration)
- Persists last opened folder and window geometry across sessions
- Dark gray theme
- Standalone EXE via PyInstaller

**Recent Updates (v1.0.0 - Apr 4, 2026):**
- Initial release
- QMediaPlayer + QVideoWidget embedded playback
- Fullscreen with Esc/F exit, arrow-key navigation while fullscreen
- File release on folder change — no file locks

**Tech Stack:** Python, PySide6, QtMultimedia, PyInstaller

**Directory:** `Desktop Video Browser/`

---

### 🗂️ File Rename Mover
**Version:** 2.1.7 | **Status:** Active Development | **Language:** Python

A powerful, object-oriented tool for batch renaming and moving files with advanced features.

**Features:**
- Batch rename and move files with sequential numbering
- Multiple rename patterns (numbering, datetime, prefix, custom)
- Advanced sorting options (name, date modified, date created, size)
- Folder organization (flat, by year, year/month, year/month/day, date, month)
- Counter scanning across all subfolders for proper sequence continuation
- Dark theme UI with red accents
- Persistent configuration
- Settings dialog for default folders
- Standalone executable available (distribution zip included)

**Recent Updates (v2.1.7 - Jan 9, 2026):**
- Fixed config initialization bug
- Fixed counter scanning to search all subfolders for existing files
- Proper icon loading for PyInstaller frozen executables
- Distribution zip package for easy deployment

**Previous Versions:**
- v2.1.4: Filename validation, security protections
- v2.1.3: Standalone executable, MIT License
- v2.0.0: Complete refactoring to object-oriented architecture

**Tech Stack:** Python, Tkinter, PyInstaller

**Directory:** `File Rename Mover/`

---

### 📁 File Copy Manager
**Version:** 1.2.0 | **Status:** Active Development | **Language:** Python

A powerful tool for batch copying files with automatic duplicate numbering and flexible folder organization.

**Features:**
- Batch copy files with automatic duplicate handling
- Real-time dual progress bars (overall and per-file)
- File size and age filtering
- Wildcard pattern matching (*.jpg, *.png, etc.)
- Preserve original folder structure OR organize by date
- Automatic duplicate file numbering
- Yellow and black theme (distinct from File Rename Mover)

**Recent Updates (v1.2.0 - Jan 1, 2026):**
- File pattern filtering with wildcard support
- Multiple patterns support (*.jpg, *.png, *.pdf)
- Automatic migration of old extension format to patterns

**Tech Stack:** Python, Tkinter, PyInstaller

**Directory:** `File Copy Manager/`

---

### 📂 File Rename with Index
**Status:** Legacy | **Language:** Python

Simple command-line script for batch renaming files with sequential numbering.

**Features:**
- Basic file renaming with index numbers
- Specialized version for facial image processing
- Sequential numbering with padding (e.g., 00001, 00002)

**Tech Stack:** Python (os, sys modules)

**Directory:** `FileRenamewithIndex/`

---

### 🖼️ Image Resizer
**Status:** Stable | **Language:** Python

GUI tool for batch resizing images to a standard size.

**Features:**
- Batch resize images to 512x512 pixels
- Support for PNG, JPG, JPEG formats
- Creates separate output folder for resized images
- Simple Tkinter GUI with folder selection
- Real-time feedback listbox

**Tech Stack:** Python, Tkinter, Pillow (PIL)

**Directory:** `Image Resize/`

---

### 🎨 Icon Maker
**Status:** Utility | **Language:** Python

Standalone PNG to ICO converter utility.

**Features:**
- Convert PNG images to ICO format
- Command-line utility
- Simple and lightweight

**Tech Stack:** Python

**File:** `png_to_ico_converter.py`

---

### 📝 Prompt Archiver
**Version:** 1.2.5 | **Status:** Active | **Language:** TypeScript/JavaScript

Desktop application for storing and organizing AI prompts with their outputs.

**Features:**
- Electron-based desktop application
- React frontend with Material-UI components
- Store and organize AI prompts and responses
- Export/archive functionality
- Cross-platform support (Windows, macOS, Linux)
- NSIS installer for Windows
- Portable executable option

**Tech Stack:** Electron, React, Material-UI, TypeScript

**Directory:** `PromptArchiver/`

---

### 🎮 Lunar Lander
**Status:** Game | **Language:** HTML/JavaScript

Classic Lunar Lander game implemented in HTML5.

**Features:**
- Browser-based game
- Physics simulation
- HTML5 canvas rendering

**Tech Stack:** HTML5, JavaScript

**Directory:** `Lunar Lander/`

---

### 🚀 Missile Command Game
**Status:** Game | **Language:** HTML/JavaScript

Classic Missile Command arcade game recreation.

**Features:**
- Browser-based arcade game
- HTML5 canvas for graphics
- Interactive gameplay

**Tech Stack:** HTML5, JavaScript

**Directory:** `MissileCommandGame/`

---

## 🛠️ Installation & Requirements

### Python Projects
```bash
# Most Python projects require:
pip install -r requirements.txt

# For Image Resizer specifically:
pip install pillow

# For File Rename Mover:
pip install pyinstaller  # For building executables
```

### Prompt Archiver
```bash
cd PromptArchiver
npm install
npm start  # Development mode
npm run dist  # Build executable
```

### Games
Simply open the HTML files in a modern web browser.

---

## 📊 Project Status Summary

| Project | Version | Status | Language | Last Updated |
|---------|---------|--------|----------|--------------|
| Desktop Video Browser | 1.0.0 | ✅ Active | Python | Apr 4, 2026 |
| File Rename Mover | 2.1.7 | ✅ Active | Python | Jan 9, 2026 |
| File Copy Manager | 1.2.0 | ✅ Active | Python | Jan 1, 2026 |
| Prompt Archiver | 1.2.5 | ✅ Active | TypeScript/JS | Nov 2025 |
| Image Resizer | - | ✅ Stable | Python | Sep 2025 |
| File Rename with Index | - | 📦 Legacy | Python | Sep 2025 |
| Lunar Lander | - | 🎮 Complete | HTML/JS | Nov 2025 |
| Missile Command | - | 🎮 Complete | HTML/JS | Nov 2025 |
| Icon Maker | - | 🔧 Utility | Python | Sep 2025 |

---

## 🎯 Usage Examples

### File Rename Mover
```bash
# Run from source
python main.py

# Or use standalone executable
FileRenameMover.exe
```

### Image Resizer
```bash
python image_resizer.py
```

### File Rename with Index
```bash
python rename_files.py
```

### Prompt Archiver
```bash
cd PromptArchiver
npm start
```

---

## 🔄 Recent Activity

### April 4, 2026
- **Desktop Video Browser v1.0.0**: Initial release — PySide6 video browser with embedded player, keyboard navigation, fullscreen, drag-and-drop, and dark theme

### January 9, 2026
- **File Rename Mover v2.1.7**: Fixed config init bug, counter scanning for subfolders, icon loading
- Distribution zip package for easy deployment

### January 1, 2026
- **File Copy Manager v1.2.0**: Added wildcard pattern filtering, multiple patterns support

### December 8, 2025
- **File Rename Mover v2.1.4**: Filename validation, security protections

### November 27, 2025
- **File Rename Mover v2.1.3**: UI adjustments, standalone executable, MIT License added
- Created comprehensive documentation

### November 22-23, 2025
- Added Lunar Lander game
- Updated Missile Command game
- General repository maintenance

### November 9, 2025
- Prompt Archiver updates and improvements

### September 28, 2025
- Initial repository setup
- Added Image Resizer, File Rename tools
- Icon Maker utility added

---

## 📄 License

This repository is licensed under the MIT License. See individual project directories for specific licensing information.

- **File Rename Mover**: MIT License
- **Prompt Archiver**: MIT License
- Other projects inherit the repository license unless otherwise specified

---

## 👨‍💻 Author

**Cody's Corner** ([@codyscorner](https://github.com/codyscorner))

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the issues page or submit pull requests.

---

## 🌟 Highlights

### Most Active Project
**File Rename Mover** - Continuous development with regular updates and feature additions

### Most Complex Project
**Prompt Archiver** - Full-stack Electron application with React frontend and cross-platform distribution

### Most Versatile
**File Rename Mover** - Supports multiple rename patterns, sorting options, and folder organization schemes

---

## 📚 Documentation

Each project contains its own documentation:
- `File Rename Mover/README.md` - Detailed architecture and usage guide
- `File Rename Mover/CHANGELOG.md` - Version history
- `File Rename Mover/FEATURES_v2.1.md` - Feature documentation
- `File Copy Manager/README.md` - File copy tool documentation
- `PromptArchiver/README.md` - Prompt archiver documentation

---

## 🔗 Quick Links

- [File Rename Mover Documentation](File%20Rename%20Mover/README.md)
- [File Copy Manager Documentation](File%20Copy%20Manager/README.md)
- [File Rename Mover Changelog](File%20Rename%20Mover/CHANGELOG.md)
- [Report Issues](https://github.com/codyscorner/VideCoding/issues)

---

**Last Updated:** April 4, 2026
