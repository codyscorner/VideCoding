# Changelog

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
