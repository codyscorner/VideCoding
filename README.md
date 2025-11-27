# VideCoding Projects

A collection of utility tools and games developed for file management, image processing, and entertainment.

## 📦 Projects Overview

### 🗂️ File Rename Mover
**Version:** 2.1.3 | **Status:** Active Development | **Language:** Python

A powerful, object-oriented tool for batch renaming and moving files with advanced features.

**Features:**
- Batch rename and move files with sequential numbering
- Multiple rename patterns (numbering, datetime, prefix, custom)
- Advanced sorting options (name, date modified, date created, size)
- Folder organization (flat, by year, year/month, year/month/day, date, month)
- Dark theme UI with red accents
- Persistent configuration
- Settings dialog for default folders
- Standalone executable available

**Recent Updates (v2.1.3 - Nov 27, 2025):**
- Updated window size to 1000x870 for better UI fit
- Built standalone executable with PyInstaller
- Added MIT License
- Updated PyInstaller spec file to use new main.py entry point
- Included comprehensive documentation

**Previous Versions:**
- v2.1.2: Enhanced UI with advanced features
- v2.0.0: Complete refactoring to object-oriented architecture
- v1.2.4: Last monolithic version

**Tech Stack:** Python, Tkinter, PyInstaller

**Directory:** `File Rename Mover/`

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
| File Rename Mover | 2.1.3 | ✅ Active | Python | Nov 27, 2025 |
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
- `PromptArchiver/package.json` - Build and dependency information

---

## 🔗 Quick Links

- [File Rename Mover Documentation](File%20Rename%20Mover/README.md)
- [File Rename Mover Changelog](File%20Rename%20Mover/CHANGELOG.md)
- [Report Issues](https://github.com/codyscorner/VideCoding/issues)

---

**Last Updated:** November 27, 2025
