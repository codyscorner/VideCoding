# VibeCoding — Daily Progress Tracker
**Session Date:** 2026-06-21
**Current Branch:** master (all PRs merged)

---

## Context Window Instructions
When starting a new context window, read this file first. It tells you exactly what has been done, what's next, and any decisions already made. Update this file at the end of every task before switching context.

---

## Overall Priority List (from upgrade review session)

### 🔴 High Priority
- [x] ~~Add PROJECT_SUMMARY.md to all projects~~ ✅ commit `adc2beb`
- [x] ~~Delete `WinFolderMover/` duplicate~~ ✅ commit `ed5bc3d`
- [x] ~~Rewrite main README.md as centralized project index~~ ✅ commit `304842d`
- [x] ~~**Build Desktop Video Browser**~~ ✅ v1.1.0 — PR #10 (`feature/desktop-video-browser`)
- [x] ~~**ScreenSnap P1 tools**~~ ✅ Ellipse, Freehand, Highlight — PR #11 (`feature/screensnap-p1`)
- [x] ~~**Build ImageConverter**~~ ✅ v1.0.0 — PR #12 (`feature/image-converter`)

### 🟡 Medium Priority
- [x] ~~**AI Image Studio**~~ ✅ v3.0.2 — Scene Composer + RunPod support + Library tab — EXE at `P:\Apps\VibeCoded\AI Image Studio\`
- [x] ~~**Style Randomizer**~~ ✅ v1.3.0 — Auto Run mode — EXE at `P:\Apps\VibeCoded\ComfyUI Style Randomizer\`
- [x] **File Rename Mover** — v3.3.0 — progress bar (QThread worker + cancel) + drag-and-drop folder selection — EXE at `P:\Apps\VibeCoded\File Rename Mover\`
- [x] **FileFinder** — v1.1.0 — wildcard/regex search modes, file type filter, date range filter, max size filter, export CSV — EXE at `P:\Apps\VibeCoded\FileFinder\`
- [x] **FaceFinder** — v1.3.0 — Export CSV + Copy All Paths — PR #19 (`feature/facefinder-export-bulkcopy`)

### 🟢 Low Priority
- [ ] **JPG2PNG_Converter** — merge into ImageConverter when built
- [ ] **IconMaker** — wrap script in small PyQt6 GUI
- [ ] **Unzipper** — add 7z and tar.gz support alongside ZIP

---

## Decisions Made This Session
- `WinFolderMover/` (v1.0.0) confirmed for deletion — `Win Folder Mover/` (v1.0.2) is canonical
- Each project task below should be done on its **own feature branch**, PR'd to master separately
- File Copy Manager changes (preview_dialog.py + ui changes) — merged to master via PR #7/8/9
- All work from this session is now on master

---

## Task Log

### ✅ DONE — PROJECT_SUMMARY.md for all projects
- Renamed README/plan docs to PROJECT_SUMMARY.md across 25 projects
- Created new PROJECT_SUMMARY.md from scratch for 8 projects with no docs
- Committed: `adc2beb` — pushed to `feature/style-randomizer-v1.2.1`

### ✅ DONE — Style Randomizer v1.3.0
- Auto Run mode: batch size spinner (1–50), ▶▶ Auto Run + ⏹ Stop After Batch buttons
- All images in a batch share one style; next batch guaranteed different style (no consecutive repeat, 2 prompts alternate)
- Regular Start unchanged: random style per image
- Processed images auto-removed from grid between auto batches
- QSpinBox dark-theme text color fix; Start button lambda signal fix
- EXE deployed to `P:\Apps\VibeCoded\ComfyUI Style Randomizer\`
- PR #14 on `feature/style-randomizer-autorun`

### ✅ DONE — ImageConverter v1.0.0
- Batch-converts images between PNG, JPG, WebP, BMP, TIFF
- Quality slider for lossy formats (JPG/WebP)
- Output folder picker with "same as source" default
- Skip same-format files, recursive subfolders, delete originals options
- JPEG alpha-flattening (RGBA → white-background RGB)
- EXE built + deployed to `P:\Apps\VibeCoded\Image Converter\`
- Supersedes JPG2PNG_Converter
- PR #12 on `feature/image-converter`

### ✅ DONE — ScreenSnap P1 tools
- Added EllipseLayer (drag-to-draw ellipse, proper ellipse hit-test)
- Added FreehandLayer (free-draw path, round caps, accumulated on MouseMove)
- Added HighlightLayer (semi-transparent yellow fill rectangle)
- Wired all three into AnnotationCanvas with live drag preview
- Added toolbar buttons + keyboard shortcuts: E=ellipse, F=freehand, H=highlight
- 34 tests still passing — PR #11 open on `feature/screensnap-p1`

---

## How to Pick Up in a New Context Window

1. Read this file
2. Check `git status` and `git log --oneline -5` to confirm current state
3. Pick the next unchecked item from the priority list above
4. Create a new branch: `git checkout -b feature/<project-name>-<description>`
5. Do the work, commit, push, PR to master
6. Check the item off in this file and save before switching context

---

## Per-Project Notes (add notes here as you work)

### WinFolderMover cleanup
- Delete entire `P:\AI\VideCoding\WinFolderMover\` folder (not `Win Folder Mover\`)
- WinFolderMover v1.0.0 is strictly older — Win Folder Mover v1.0.2 has all the same features plus more
- After delete: `git rm -r WinFolderMover/` + commit

### Desktop Video Browser
- Full plan in `Desktop Video Browser/PROJECT_SUMMARY.md`
- Stack: Python + PySide6 + QtMultimedia
- MVP: file list panel (left) + video player (right) + dark gray theme
- EXE via PyInstaller
- Output: `P:\Apps\VibeCoded\Desktop Video Browser\`

### Style Randomizer — Auto Run mode
- Reference: `ComfyUI_Chain_Automator/main.py` — Auto Run mode added in v3.1.0
- Port the pattern: batch size spinner, Auto Run button, Stop After Batch button, auto-remove processed images from grid
- Currently on branch `feature/style-randomizer-v1.2.1`

### ImageConverter
- Plan: batch convert images between formats (JPG, PNG, WebP, BMP, TIFF, AVIF)
- Stack: Python + PyQt6 + Pillow
- Key feature: format picker, quality slider per format, source/dest folders, progress bar
- Consider merging JPG2PNG_Converter into this when done
