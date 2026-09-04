# Changelog — ComfyUI Workflow Editor

## v1.2.0 — 2026-09-04

### Added
- **Every node gets its own section.** The form is no longer limited to five hardcoded
  node types — each node in the workflow is rendered as a collapsible card with all of
  its editable settings, grouped under category headings (Prompts, LoRAs, Sampling,
  Image / Video / Latent, Loaders, Output, Other, Notes) and colour-coded by category.
- **Both ComfyUI file formats.** API format (`{id: {class_type, inputs}}`) and the UI /
  graph format saved by the frontend (`{nodes: [...], links: [...]}`). For the UI format,
  positional `widgets_values` get names from a built-in table covering the core nodes
  (KSampler, KSamplerAdvanced, loaders, LoRA loaders, WanImageToVideo, VHS_VideoCombine,
  rgthree LoRA stack, …); unknown node types fall back to `Value 1..N`.
- **Editor chosen by value type** — checkbox for booleans, spin boxes for ints/floats
  (ranges and steps tuned by field name: cfg, denoise, strength, width/height, shift…),
  editable drop-downs for known-choice strings (sampler, scheduler, control_after_generate,
  upscale method, weight dtype…), plain text for seeds (which exceed 32-bit), a text area
  for prompts / notes / expressions, and a line edit for everything else.
- **Connections shown read-only.** Inputs wired to another node are listed at the bottom
  of the card as `input ← Source node [id]`, so it's clear why e.g. `steps` isn't editable.
- Bypassed / muted nodes (UI format) carry a BYPASSED / MUTED badge.
- Nodes whose paragraph field is a prompt (e.g. `MiniMaxH3ImageToVideo.prompt`) are
  promoted into the Prompts group; negative prompts are still tinted red.
- Toolbar **Find node** filter (Ctrl+F) matching title / type / #id, and a
  **Show all nodes** toggle (remembered in settings) — nodes with no editable
  fields are hidden by default to keep big graphs readable.
- **View** menu: Expand all (Ctrl+Shift+E) / Collapse all (Ctrl+Shift+C).
- Status bar reports format, node count and editable-field count.

### Changed
- `workflow.py` now holds the format-aware document model (`parse_workflow`,
  `WorkflowDoc`, `NodeInfo`, `Field`); `ui/node_section.py` holds the card widget and
  editor factory. `main_window.py` shrank to window chrome + file I/O.
- Whole floats stored as ints in the JSON (`cfg: 1`, `denoise: 1`) get a float editor and
  are written back as ints while they stay whole, so untouched files don't churn.
- Float noise such as `8.000000000000002` is rounded on save.

### Removed
- The old fixed sections (Prompts / LoRA Strengths / KSampler / Video Settings) — all of
  that is covered by the generic per-node cards.

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
