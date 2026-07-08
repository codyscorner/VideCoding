# Changelog

All notable changes to Bulk File Randomizer are documented in this file.

## [1.1.0] - 2026-07-07

### Added
- **Preview** button — dry-run table showing source filename → new filename for every file that would be processed, without touching the filesystem. If the Seed field is blank, previewing generates and pins a seed so a subsequent run reproduces the exact same names.
- **Move mode** — a Mode dropdown (Copy / Move) next to the recursive-search option; Move mode uses `shutil.move` and removes the source file. Button label, counters, and log messages all switch wording accordingly.
- **Seeded shuffle** — a Seed field (blank = random). The same seed with the same source files and mask always produces the same set of randomized names in the same order.

### Changed
- `renamer.py` refactored so preview and the actual run share one naming function (`generate_batch_names`) driven by a per-call `random.Random` instance — this is what guarantees preview and the real run match exactly, and never touches Python's global random state.

## [1.0.0] - 2026-07-07 (icon refresh)

### Fixed
- Window icon now loads from next to the EXE when running as a frozen PyInstaller build (previously the icon only resolved when running from source).

### Changed
- Updated `app_icon.ico` with a new app icon.

## [1.0.0] - Initial release

- Copy-and-rename a batch of files with randomized sequential numbering.
- Configurable output folder and base filename; persistent config; dark PyQt6 UI.
