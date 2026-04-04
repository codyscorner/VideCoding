# Video Browser — Project Plan

## 1. Project Overview

A Windows desktop application built with Python + PySide6, featuring:

- A file list panel (left) showing video files from a selected directory
- A video preview/player panel (right)
- A dark gray theme for a modern, professional look
- Packaged as a standalone EXE using PyInstaller

This app is designed to be fast, lightweight, and easy to extend.

---

## 2. Tech Stack

### Language & Framework

- Python 3.10+
- PySide6 (Qt for Python)
- QtMultimedia for video playback

### Why This Stack

- Deep existing experience with PySide6
- Qt's multimedia stack is stable and easy to integrate
- Claude Code excels at Python correctness and refactoring
- Gemini excels at UI planning and multi-step reasoning
- Packaging to EXE is straightforward

---

## 3. Project Structure

```
video_browser/
│
├── app.py
├── ui/
│   ├── main_window.py
│   ├── file_list_panel.py
│   ├── video_player_panel.py
│   └── dark_theme.qss
│
├── core/
│   ├── file_loader.py
│   └── settings.py
│
├── assets/
│   └── icons/
│       └── app.ico
│
├── build/
│   └── build_exe.bat
│
└── PLAN.md
```

---

## 4. Core Features (MVP)

### 4.1 File List Panel

- Displays all video files in a directory
- Supports drag-and-drop folder loading
- Uses `QListWidget` or `QTreeView`
- Emits signal when a file is selected

### 4.2 Video Player Panel

- Uses `QMediaPlayer` + `QVideoWidget`
- Supports play/pause/stop
- Auto-loads selected file
- Handles unsupported formats gracefully

### 4.3 Dark Gray Theme

A custom Qt stylesheet (`dark_theme.qss`) defining:

- Dark gray window background
- Slightly lighter panels
- High-contrast text
- Blue accent color for selection
- Modern flat UI look

### 4.4 Settings

- Last opened folder
- Window geometry
- Playback preferences

### 4.5 EXE Packaging

- PyInstaller one-file build
- Custom icon
- Build script in `/build/build_exe.bat`

---

## 5. Extended Features (Phase 2)

- Thumbnail previews
- Video metadata (duration, resolution, codec)
- Keyboard shortcuts
- Dark/light theme toggle
- Multi-folder watch list
- Tagging system
- SQLite mini-database for indexing
- Video trimming or frame capture

---

## 6. Development Workflow Using Claude + Gemini

### Claude Code (VS Code Extension)

Use Claude for:

- Implementing PySide6 classes
- Fixing bugs
- Refactoring
- Writing clean, correct Python
- Improving signals/slots
- Debugging PyInstaller issues

### Gemini

Use Gemini for:

- UI/UX brainstorming
- Multi-step architectural planning
- Reviewing design decisions
- Generating mockups
- Exploring alternative layouts
- Documentation drafts

### Recommended Workflow

1. Ask Gemini: *"Design a clean UI layout for a dark-themed file list + video preview app."*
2. Paste Gemini's layout into VS Code.
3. Ask Claude Code: *"Implement this layout in PySide6 using my project structure."*
4. Iterate quickly with Claude for correctness and structure.

This gives you maximum leverage from both subscriptions.

---

## 7. Milestones

| Milestone | Goal |
|-----------|------|
| **1 — Project Setup** | Create folder structure, add `dark_theme.qss`, create `app.py` with theme loading |
| **2 — UI Layout** | Implement main window with splitter, add file list panel, add video player panel |
| **3 — Core Logic** | Directory loading, file selection → video playback, settings persistence |
| **4 — Packaging** | PyInstaller config, build EXE, test on clean Windows VM |
| **5 — Enhancements** | Thumbnails, metadata, themes |

---

## 8. Dark Theme (`dark_theme.qss`)

```css
QWidget {
    background-color: #2b2b2b;
    color: #e0e0e0;
    font-size: 14px;
}

QListWidget, QTreeView {
    background-color: #333333;
    border: 1px solid #444444;
}

QListWidget::item:selected, QTreeView::item:selected {
    background-color: #3d6aff;
    color: white;
}

QSplitter::handle {
    background-color: #444444;
}

QPushButton {
    background-color: #3a3a3a;
    border: 1px solid #555555;
    padding: 6px;
}

QPushButton:hover {
    background-color: #4a4a4a;
}

QPushButton:pressed {
    background-color: #2a2a2a;
}

QMenuBar, QMenu {
    background-color: #2b2b2b;
    color: #e0e0e0;
}

QMenu::item:selected {
    background-color: #3d6aff;
}
```

---

## 9. Build Script

`build/build_exe.bat`:

```bat
pyinstaller --noconsole --onefile --icon=assets/icons/app.ico app.py
```

---

## 10. Future Expansion Ideas

- AI-powered video tagging
- Automatic scene detection
- Frame extraction
- Batch renaming
- Playlist support
- GPU-accelerated preview
