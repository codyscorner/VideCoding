# Changelog — ComfyUI Workflow Editor

## v1.1.0 — 2026-09-04

### Added
- **Drag and drop to open.** Drop a `.json` workflow anywhere on the window to load it.
  - `dragEnterEvent` / `dragMoveEvent` only accept the drag when it carries at least one
    local `.json` file that exists on disk, so the cursor shows the correct feedback.
  - Dropping several files opens the first `.json` and says so in the status bar.
  - Empty-state screen now shows the hint "or drag a .json file anywhere onto this window".

### Changed
- Opening a workflow (via dialog or drop) now prompts to save when the current one has
  unsaved edits — previously changes were silently discarded on Open.
- File loading extracted from `open_file()` into `MainWindow.load_path(path)` so the
  dialog and the drop path share one code path.
- `load_path()` rejects JSON that is not an object of nodes (e.g. a top-level list)
  with a clear error instead of loading an empty form.

### Fixed
- Form fields (prompt boxes, spin boxes, combos) no longer swallow file drops and paste
  the dropped path in as text — `_disable_child_drops()` clears `acceptDrops` on the form
  widgets and their viewports after each rebuild, so the drop reaches the window.

## v1.0.0

- Initial release: form editor for ComfyUI workflow JSON (prompts, LoRA strengths,
  KSampler settings, WAN frame counts), with everything else passed through on save.
