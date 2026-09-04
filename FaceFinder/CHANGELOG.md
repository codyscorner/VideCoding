# FaceFinder Changelog

## v1.4.2 — 2026-08-29

### Fixed
- **"Failed to paste from clipboard: QMetaObject.invokeMethod() call failed"** — status messages were pushed to the results list via `QMetaObject.invokeMethod(..., "addItem", ...)`, which isn't an invokable slot in PyQt6. Replaced with proper `pyqtSignal`s. The paste itself had actually succeeded; only the status line after it blew up.
- **Progress bar/label now update live during a search** — `_update_progress()` was a no-op stub; it now emits a signal, so "Scanned: N/M" and the bar advance in real time.
- **Multiple pasted screenshots now become multiple references** — each paste saved to the same `facefinder_clipboard_ref.png`, so a second pasted screenshot silently collapsed into the first. Pastes now get unique timestamped filenames.
- **Stale saved references are dropped at startup** — pasted screenshots live in %TEMP% and can vanish between sessions; missing files are now removed from the saved list (with a note in Results) instead of hard-erroring when Search is clicked.

## v1.4.1 — 2026-08-29

### Fixed
- **Splash screen never closed** — the PyInstaller splash was built into the EXE but the app never called `pyi_splash.close()`, so it stayed on top of the main window forever. It now closes as soon as the main window is shown.
- **Window too small — controls clipped** — default size was 750×650, which squeezed the Search Options group (checkbox/slider hint cut off) and hid buttons. Default is now 900×980 with a 760×850 minimum so all sections are fully visible.
- **Window now opens centered on the screen** instead of wherever the OS drops it, and is raised to the front on startup so it isn't buried behind other windows.
- **Splash showed stale v1.0.0** — added `make_splash.py`, which regenerates `splash.png` with the version read from `main.py`. Run it before building.

### Build
- Added the shared-venv heavy ML excludes (`torch`, `tensorflow`, `cv2`, `scipy`, `pandas`, `matplotlib`, …) to `FaceFinder.spec` so unused packages stop inflating the EXE.
- Removed leftover `tkinter`/`tkinterdnd2` bundling from the spec — the app has been pure PyQt6 since v1.2.0.

## v1.4.0 — 2026-07-08
- Multiple reference images per search — a match against any reference counts
- Move/Copy selected matches to a folder from the results viewer
- Saved search profiles (references + tolerance + recursive + folder under a name)

## v1.3.0
- Export results to CSV (File Name, Full Path, File Size, Modified Date)
- Copy All Paths button in results viewer

## v1.2.0
- Migrated from tkinter to PyQt6; dark gold/amber theme
- QPixmap thumbnail grid in results viewer
- Native PyQt6 drag-drop; clipboard paste preserved

## v1.0.0 — January 2026
- Initial release: face recognition search, parallel processing, tolerance slider, yellow/black theme
