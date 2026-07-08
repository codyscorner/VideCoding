# Changelog

## v1.1.0 — 2026-07-08
- Added calculation history panel ("Hist" toggle) — click any past entry to reuse its result.
- Added full keyboard input: digits, operators, `.`, `(` `)`, `%`, Enter/Return to evaluate, Backspace to delete, Esc to clear.
- Added "Copy" button to copy the displayed result to the clipboard.
- Added scientific mode ("Sci" toggle): parentheses for grouping, √ (square root), xʸ (power).
- Rewrote the input/expression engine from a two-term chain model to a single running expression string to support parentheses and nested operations; auto-balances unclosed parentheses on evaluate.

## v1.0.0 — 2026-03-18
- Initial release: dark blue "Midnight" theme, standard arithmetic, percentage, sign toggle, memory functions (MC/MR/M+/M-), comma-formatted output.
