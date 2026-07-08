# Changelog

All notable changes to Image Resizer are documented here.

## [1.3.0] - 2026-07-08

### Added
- Drag-and-drop: drop a folder or file onto the window to set the input folder.
- Resize mode dropdown replacing the old "preserve aspect ratio" / "add padding" checkboxes:
  - Fit (Pad to Canvas) — previous default behavior
  - Fit (No Padding) — previous "preserve ratio" without padding
  - Fill (Crop to Aspect) — new: scales to cover the target size and center-crops to exact dimensions
  - Stretch (Ignore Aspect) — previous non-ratio-preserving behavior
- "Sharpen after downscale" option (unsharp mask applied to the resized image).
- "Preserve EXIF metadata" option (copies EXIF from source to output where the format supports it).
- "Skip images already at/below target size" option — copies the file through unchanged instead of upscaling.

### Changed
- Settings file migrates old `preserve_ratio`/`use_padding` booleans to the new `resize_mode` value automatically on first load.

## [1.2.0] - prior

- Resolution presets for I2V workflows, padding color picker, persistent settings.
