# Multi-Line Clipboard Queue Loader

## Project Overview
Build a simple, standalone desktop application using **Python + Tkinter** (no external dependencies beyond built-in modules) that allows the user to:
- Paste multiple lines of text into a text area.
- Load them into an internal list and display them in a **Listbox**.
- Easily navigate through the list (Previous / Next).
- Copy the current item to the system clipboard with one click or double-click.
- Use the app as a queue to quickly copy each item one-by-one, which populates your clipboard manager's history or lets you immediately paste (Ctrl+V) into forms, spreadsheets, terminals, etc.

Ideal workflow:
1. Paste a big list of values (one per line) into the text box.
2. Click **Load List**.
3. Focus your target application/field.
4. Click **Copy** (or double-click an item) → item goes to clipboard.
5. Press Ctrl+V in your target app.
6. Click **Next** and repeat → fast sequential pasting.

## Core Features
- Multiline Text widget for input.
- "Load List" button: splits by newlines, strips whitespace, removes empty lines.
- Listbox displaying all loaded items (with vertical scrollbar).
- Current position indicator (e.g., "Item 3 of 15").
- Buttons: **Previous**, **Copy Current**, **Next**, **Clear List**.
- Double-click any item in Listbox → copy it to clipboard and set as current.
- Keyboard-friendly: arrow keys work naturally on Listbox; Enter on focused button copies.
- Status bar at bottom with feedback ("Copied: username@example.com", errors, etc.).
- Graceful handling of empty list, no selection, etc.
- Window title: "Clipboard Queue Loader", reasonable default size (700x500), resizable.

## Project Structure
clipboard-queue-loader/
├── main.py          # ← Main (and only) source file
├── README.md        # ← This file (for reference)
└── requirements.txt # (optional, can be empty or list nothing)

## Detailed UI Layout (using grid)
- Row 0: Label "Paste your list here (one item per line):"
- Row 1: Text widget (height=8, width=80) + vertical scrollbar
- Row 2: Button "Load List" (span columns, large/padded)
- Row 3: Label "Loaded Items:"
- Row 4-6: Listbox (height=12) + vertical scrollbar on the right
- Row 7: Control bar (grid):
  - Previous button
  - Label "Current: 0 / 0" (updated live)
  - Copy Current button (default or highlighted)
  - Next button
  - Clear List button
- Row 8: Status label (sticky bottom, relief, background color for visibility)

## Behavior & Functions to Implement
- Global variables: `item_list = []`, `current_index = 0`
- `load_list()`:
  - Read from Text widget
  - Split on `\n`, strip each line, filter out empty/whitespace-only
  - Set `item_list`, reset `current_index = 0` if list non-empty
  - Populate Listbox
  - Select first item
  - Update current label and status
- `update_listbox()`: delete all, insert all items, re-select current_index, scroll to view
- `update_current_label()`: show f"Current: {current_index + 1} / {len(item_list)}" (or "None" if empty)
- `go_previous()` / `go_next()`: bounds checking, update index → update_listbox() → update_current_label()
- `copy_current()`:
  - If list empty → status warning
  - Else: `root.clipboard_clear()` then `root.clipboard_append(item_list[current_index])`
  - Status: "Copied: [first 60 chars]..." (green or normal color)
- Double-click binding on Listbox:
  - Get selected index via `curselection()`
  - If valid, set `current_index = that index`, update display, then call `copy_current()`
- Clear List: empty item_list, current_index=0, clear Listbox and Text widget, update labels
- Status label updates after every action
- Optional nice touches (recommended):
  - Bind `<Return>` to Copy button when focused
  - Make Copy button slightly larger / different color
  - Add small delay option? (skip unless you want; manual navigation is sufficient)
  - Prevent duplicate items? (optional)

## Edge Cases to Handle
- Empty input / all whitespace → warning in status
- Only one item
- Very long list (hundreds of lines) → Listbox should scroll fine
- Items with newlines or special chars (preserve exactly as pasted)
- No clipboard manager needed – works with standard OS clipboard + any clipboard history tool (Ditto, CopyQ, Maccy, etc.)

## Extra Credit (Optional, mention if you implement)
- "Auto-copy all with delay" button (uses `root.after` chain, 300–500ms delay)
- Search/filter box for the Listbox
- Save/Load list from file
- Dark mode toggle
- Global hotkey support (requires `keyboard` or `pynput` – not required)

Generate clean, well-commented, PEP-8 style code in a single `main.py` file that runs immediately with `python main.py`. Include `if __name__ == "__main__": root.mainloop()`. Make the UI intuitive and polished.