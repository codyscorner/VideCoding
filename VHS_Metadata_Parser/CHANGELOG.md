# Changelog

## v1.3.0 — 2026-09-04
- **MiniMax H3 workflows now parse fully** (test file: `Test_files/MiniMax_H3_00008-audio.mp4`). Previously the Prompts tab was empty and Video/Sampler tabs showed `N/A` because the parser only knew `CLIPTextEncode`, `WanImageToVideo` and `KSamplerAdvanced`.
- `MetadataParser` rewritten around `_take()` / `_resolve()`: every input is read through a helper that follows `[node_id, slot]` links back to a literal (same-named input on the source node, a `value` primitive, a `ComfyMathExpression` evaluated with a whitelisted namespace, or a prompt-text input) and records the (node, input) pair as *consumed*.
- Prompt extraction is generic: any node input named `prompt`, `text`, `positive`, `negative`, `positive_prompt`, `negative_prompt`, `custom_prompts`, `string`, `text_positive`, `text_negative`. Literal strings first, then links, de-duplicated by text. Fixes `CLIPTextEncode.text` linked from `PromptCycler` showing as `['126', 0]`.
- New `parse_prompt_sections()` + **Prompt Sections** table (Source / Section / Content) on the Prompts tab: `[Shot N] At mm:ss.mmm` → `Shot N @ mm:ss.mmm`, `<d>…</d>` → `Shot N · Dialogue`, `Camera:` / `overall_soundscape:` / `non_diegetic_music:` / any `Label:` or `snake_case_key:` → own row, JSON prompts → one row per key. Negative prompts tinted red, dialogue rows tinted cyan. Raw positive/negative boxes kept below in a splitter.
- New **Other Settings** tab (after Sampler): `get_other_settings()` lists every literal node input that no extractor consumed — Node ID / Node Type / Title / Setting / Value — with a text filter and a "show nodes that have no literal settings" toggle. Also appended as a section to the Models/Sampler CSV export (menu + buttons renamed to "Export Models, Sampler & Other Settings").
- Video settings: any `*ToVideo` / `*LatentVideo` node supplies width/height/length/batch_size; `VHS_VideoCombine` supplies `has_audio` (names the audio source node); `duration_s = length / frame_rate`. `ImageResizeKJv2` / `ImageScale` / `ImageResize+` fill in width/height only when the primary value is unresolved. UI rows added: Duration (s), Audio.
- Sampler: handles `KSampler*` (seed or noise_seed, denoise) and `SamplerCustomAdvanced` / `SamplerCustom` (seed via `RandomNoise`, steps/scheduler/denoise via `BasicScheduler`, sampler via `KSamplerSelect` or the linked sampler node's title such as "MiniMax-H3 Turbo Sampler (4-step)", CFG via CFGGuider else "N/A (Basic Guider)"). Denoise column added.
- Models: detection by input name (`clip_name`, `clip_name1..3`, `vae_name`, `unet_name`, `ckpt_name`, `lora_name` with `strength_model` or `strength`), so `MiniMaxH3TurboLoRA` and checkpoint loaders appear. LoRA table gains a Loader column. Model Sampling covers all `ModelSampling*` nodes (non-`shift` literals are joined as `k=v`).
- `parse_file()` accepts bare API-format prompt JSON (dict of `{id: {class_type, inputs}}`) and resets state between loads.
- Batch: `summarize_file()` rows gain `duration_s` / `has_audio`; Diff dialog and batch CSV include Duration (s) and Audio.
- Fix: prompt-section rows are re-fitted when the tab is shown / columns resized (rows were sized before layout and came out huge); `&` in button/menu labels escaped so it is not eaten as a mnemonic.
- Version bumped to 1.3.0 (docstring, window title, docs).

## v1.2.0 — 2026-07-08
- New **Batch / Search** tab: scan a folder (optionally recursive) for `.mp4`/`.json`/`.txt` metadata files on a background `QThread`, with a live progress status label.
- Summary table per scanned file: filename, width, height, length, frame rate, format, sampler steps/CFG/name, LoRA names, UNET names.
- Live search box filters the batch table by filename, LoRA/model name, sampler, or prompt text — answers "which videos used LoRA X?".
- Diff view: select exactly two rows (Ctrl+Click) and click "Diff Selected" to open a dialog comparing key metadata fields side by side, with differing fields highlighted.
- "Export Summary CSV" writes the currently filtered batch table to a CSV file.
- Double-click a batch row to load that file into the main single-file viewer tabs.
- Added a `summarize_file()` helper and `row_matches_search()` used by both the batch table and search filter.
- `VHS_Metadata_Parser.spec` gained an `excludes` list for shared-venv ML packages (torch, cv2, numpy, etc.) to keep the EXE small.

## v1.1.1 (pre-existing, undocumented)
- Version bump only; no changelog entry existed prior to this file.

## v1.1.0
- Migrated from PyQt5 to PyQt6.
- Dark blue-green theme applied throughout.
- Updated all Qt6 enum flags (ResizeMode, EditTrigger, etc.).

## v1.0.0
- Initial release with PyQt5.
- Tabbed metadata viewer.
- Drag & drop and file browser support.
