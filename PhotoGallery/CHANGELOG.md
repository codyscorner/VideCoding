# Changelog

## v1.4.0 — 2026-07-19

### Added
- **Keyboard browse mode**: Up/Down move the filmstrip highlight without changing the main viewer (and now work even when the filmstrip doesn't have focus); Space loads the highlighted thumbnail into the viewer; Left/Right go to previous/next image and now also work while the filmstrip has focus.

### Fixed
- Window/taskbar icon missing in the built EXE: bundled `app_icon.ico` is unpacked to `_internal` by PyInstaller 6, but the app looked next to the EXE. Resources now load from the correct folder (config/ratings still live next to the EXE).
- `build.bat` now uses the shared venv and deploys the build to `P:\Apps\VibeCoded\PhotoGallery\` (robocopy mirror, preserving config/ratings) like the other apps.

## v1.3.0 — 2026-07-19

### Added
- **Resizable filmstrip**: the thumbnail panel is no longer fixed-width — drag the splitter to widen it and thumbnails scale up to fill (64–320 px). The chosen width is saved to config (`filmstrip_width`) and restored on next launch.

### Changed
- Thumbnails are now generated at 320 px source resolution (was 120) so they stay sharp at larger display sizes; filmstrip badges scale with the thumbnail.

## v1.2.0 — 2026-07-08

Roadmap sweep release — implements all five Future Enhancements items.

### Added
- **Rating & flagging with filter**: press 1-5 to rate the current image (0 clears), F to toggle a flag. Ratings persist to `photo_gallery_ratings.json` next to the app. New "Show" filter dropdown (All / Flagged / ★1+ … ★5) live-filters the filmstrip. Star/flag badges are drawn on filmstrip thumbnails and shown in the actions bar.
- **Basic edit ops — rotate, crop, save**: R / Shift+R rotation (existing view-only feature) can now be saved to disk. New Crop button: drag a rectangle on the image, then Save (overwrite, with confirm) or Save As. Edits preserve EXIF and ICC profile; JPEG saved at quality 95.
- **Compare mode**: Compare button arms compare, then clicking another thumbnail opens a side-by-side dialog of the two images.
- **Delete to Recycle Bin**: Delete button or Del key sends the current file to the Recycle Bin (via `send2trash`) after confirmation, removes it from the strip, and advances.
- **Video thumbnails**: videos (.mp4, .avi, .mkv, .mov, .wmv, .m4v, .webm) now appear in the filmstrip with a first-frame thumbnail and a ▶ badge. Selecting a video shows its first frame; Enter or double-click opens it in the default player. Slideshow skips videos.

### Changed
- New second toolbar row (actions bar): filter dropdown, rating display, Compare, Crop, Save, Save As, Delete.
- `PhotoGallery.spec`: added `cv2`/`numpy`/`send2trash` hiddenimports and the standard ML-package excludes list.

### Fixed
- Filter/scan no longer leaves stale edit state (pending crop, armed compare) when the image list changes.

## v1.1.0

- Include-subfolders scanning, image info bar (EXIF), rotate view keys, dark theme polish.

## v1.0.0

- Initial release: filmstrip sidebar, full-resolution viewer, slideshow mode, config persistence.
