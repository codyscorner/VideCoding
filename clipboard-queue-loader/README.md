# Clipboard Queue Loader

A desktop utility for sequentially copying prompts to your clipboard. Designed for AI image generation workflows where you need to apply many different prompts to images one at a time.

## Use Case

When working with AI art tools like OpenArt.ai, Midjourney, or similar platforms:
1. You have a list of prompts (e.g., 100 different scenarios)
2. You need to paste each prompt one-by-one into the web interface
3. This tool makes that workflow fast and trackable

## Features

- **Copy & Next** - One click copies the current prompt and advances to the next
- **Auto-paste** - Automatically switches to previous window and pastes (Alt+Tab + Ctrl+V)
- **Select All First** - Optionally sends Ctrl+A before pasting to replace existing prompt
- **Stay on Top** - Keep the window floating above your browser
- **Used Tracking** - Visual indicators show which prompts you've already used
- **Progress Display** - Always know where you are: "Prompt 23 of 100"
- **Auto-Save State** - Close the app, reopen later, pick up where you left off
- **Save/Load Files** - Export prompt lists for reuse

## Installation

### Option 1: Run the Executable (Windows)
Download `ClipboardQueueLoader.exe` from the `dist` folder and run it directly.

### Option 2: Run with Python
```bash
pip install PyQt6
python main.py
```

## Usage

### Basic Workflow
1. Paste your prompts into the text area (one per line)
2. Click **Load List**
3. Enable **Stay on Top** to keep the window visible
4. In your AI tool, prepare your image
5. Click **COPY & NEXT** (or press Enter)
6. Paste (Ctrl+V) into the prompt field
7. Repeat

### Automated Workflow (Recommended)
1. Paste your prompts and click **Load List**
2. Enable **Stay on Top**, **Auto-paste**, and **Select all first**
3. Click in the prompt field of your AI tool
4. Switch to the Clipboard Queue app and press **Enter**
5. The app will: switch back to your AI tool, select all, and paste the new prompt
6. Press Enter again for the next prompt

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Enter` / `Space` | Copy & Next |
| `Left Arrow` | Previous prompt |
| `Right Arrow` | Next prompt |
| `Ctrl+S` | Save prompts to file |
| `Ctrl+O` | Load prompts from file |
| `Ctrl+L` | Load list from text area |
| `Esc` | Close app |

## Options

- **Auto-paste** - Switches to previous window and pastes automatically
- **Select all first** - Sends Ctrl+A before paste to replace existing text
- **Auto-advance** - Automatically move to the next prompt after copying
- **Skip used** - Navigation skips prompts you've already copied

## Files

- `main.py` - Main application source
- `dist/ClipboardQueueLoader.exe` - Standalone Windows executable
- `clipboard_queue_state.json` - Auto-generated session state (created at runtime)

## Building the Executable

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "ClipboardQueueLoader" main.py
```

## Version

1.2.0 — Migrated from tkinter to PyQt6, dark teal/cyan theme

## License

MIT
