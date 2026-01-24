"""
Clipboard Queue Loader - Prompt Batch Tool for AI Image Generation
A utility for sequentially copying prompts to clipboard for use with
web-based AI art tools like OpenArt.ai

Author: Claude
Version: 1.1.0
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import ctypes
import time

# =============================================================================
# Configuration
# =============================================================================

APP_TITLE = "Clipboard Queue Loader"
DEFAULT_WIDTH = 800
DEFAULT_HEIGHT = 700
PREVIEW_FONT_SIZE = 12
STATE_FILE = "clipboard_queue_state.json"


# =============================================================================
# Main Application Class
# =============================================================================

class ClipboardQueueApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry(f"{DEFAULT_WIDTH}x{DEFAULT_HEIGHT}")
        self.root.minsize(600, 500)

        # State variables
        self.item_list = []
        self.current_index = 0
        self.used_indices = set()
        self.stay_on_top = tk.BooleanVar(value=False)
        self.auto_advance = tk.BooleanVar(value=True)
        self.skip_used = tk.BooleanVar(value=False)
        self.auto_paste = tk.BooleanVar(value=False)
        self.select_all_before_paste = tk.BooleanVar(value=False)

        # Build UI
        self.create_widgets()
        self.bind_shortcuts()

        # Load saved state if exists
        self.load_state()

        # Configure grid weights for resizing
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(4, weight=1)  # Listbox row
        self.root.rowconfigure(6, weight=0)  # Preview row

    def create_widgets(self):
        """Create all UI widgets."""

        # === Row 0: Input Section Header ===
        header_frame = ttk.Frame(self.root)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        header_frame.columnconfigure(1, weight=1)

        ttk.Label(
            header_frame,
            text="Paste your prompts here (one per line):",
            font=("Segoe UI", 10, "bold")
        ).grid(row=0, column=0, sticky="w")

        # Stay on top checkbox
        ttk.Checkbutton(
            header_frame,
            text="Stay on Top",
            variable=self.stay_on_top,
            command=self.toggle_stay_on_top
        ).grid(row=0, column=2, sticky="e", padx=(10, 0))

        # === Row 1: Text Input Area ===
        input_frame = ttk.Frame(self.root)
        input_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        input_frame.columnconfigure(0, weight=1)
        input_frame.rowconfigure(0, weight=1)

        self.text_input = tk.Text(
            input_frame,
            height=6,
            width=80,
            font=("Consolas", 10),
            wrap=tk.WORD
        )
        self.text_input.grid(row=0, column=0, sticky="nsew")

        text_scroll = ttk.Scrollbar(input_frame, orient="vertical", command=self.text_input.yview)
        text_scroll.grid(row=0, column=1, sticky="ns")
        self.text_input.configure(yscrollcommand=text_scroll.set)

        # === Row 2: Load Button and Options ===
        button_frame = ttk.Frame(self.root)
        button_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        button_frame.columnconfigure(1, weight=1)

        self.load_btn = ttk.Button(
            button_frame,
            text="Load List",
            command=self.load_list,
            style="Accent.TButton"
        )
        self.load_btn.grid(row=0, column=0, padx=(0, 10))

        ttk.Button(
            button_frame,
            text="Save to File",
            command=self.save_to_file
        ).grid(row=0, column=2, padx=5)

        ttk.Button(
            button_frame,
            text="Load from File",
            command=self.load_from_file
        ).grid(row=0, column=3, padx=5)

        ttk.Button(
            button_frame,
            text="Clear All",
            command=self.clear_all
        ).grid(row=0, column=4, padx=5)

        # === Row 3: Listbox Header with Options ===
        list_header = ttk.Frame(self.root)
        list_header.grid(row=3, column=0, sticky="ew", padx=10, pady=(10, 5))
        list_header.columnconfigure(1, weight=1)

        ttk.Label(
            list_header,
            text="Loaded Prompts:",
            font=("Segoe UI", 10, "bold")
        ).grid(row=0, column=0, sticky="w")

        # Options
        ttk.Checkbutton(
            list_header,
            text="Auto-paste",
            variable=self.auto_paste
        ).grid(row=0, column=2, padx=5)

        ttk.Checkbutton(
            list_header,
            text="Select all first",
            variable=self.select_all_before_paste
        ).grid(row=0, column=3, padx=5)

        ttk.Checkbutton(
            list_header,
            text="Auto-advance",
            variable=self.auto_advance
        ).grid(row=0, column=4, padx=5)

        ttk.Checkbutton(
            list_header,
            text="Skip used",
            variable=self.skip_used
        ).grid(row=0, column=5)

        # === Row 4: Listbox ===
        list_frame = ttk.Frame(self.root)
        list_frame.grid(row=4, column=0, sticky="nsew", padx=10, pady=5)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.listbox = tk.Listbox(
            list_frame,
            height=10,
            font=("Consolas", 10),
            selectmode=tk.SINGLE,
            activestyle="dotbox"
        )
        self.listbox.grid(row=0, column=0, sticky="nsew")

        list_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        list_scroll.grid(row=0, column=1, sticky="ns")
        self.listbox.configure(yscrollcommand=list_scroll.set)

        # Listbox bindings
        self.listbox.bind("<Double-1>", self.on_listbox_double_click)
        self.listbox.bind("<<ListboxSelect>>", self.on_listbox_select)

        # === Row 5: Current Prompt Preview ===
        preview_frame = ttk.LabelFrame(self.root, text="Current Prompt Preview", padding=10)
        preview_frame.grid(row=5, column=0, sticky="nsew", padx=10, pady=10)
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)

        self.preview_text = tk.Text(
            preview_frame,
            height=4,
            font=("Segoe UI", PREVIEW_FONT_SIZE),
            wrap=tk.WORD,
            state=tk.DISABLED,
            background="#f0f0f0",
            relief=tk.FLAT,
            padx=10,
            pady=10
        )
        self.preview_text.grid(row=0, column=0, sticky="nsew")

        # === Row 6: Progress and Navigation ===
        nav_frame = ttk.Frame(self.root)
        nav_frame.grid(row=6, column=0, sticky="ew", padx=10, pady=10)
        nav_frame.columnconfigure(2, weight=1)

        # Previous button
        self.prev_btn = ttk.Button(
            nav_frame,
            text="<< Previous",
            command=self.go_previous,
            width=12
        )
        self.prev_btn.grid(row=0, column=0, padx=5)

        # Progress label
        self.progress_label = ttk.Label(
            nav_frame,
            text="No prompts loaded",
            font=("Segoe UI", 11, "bold")
        )
        self.progress_label.grid(row=0, column=1, padx=20)

        # Spacer
        ttk.Frame(nav_frame).grid(row=0, column=2, sticky="ew")

        # Copy Current (without advancing)
        self.copy_btn = ttk.Button(
            nav_frame,
            text="Copy Only",
            command=self.copy_current,
            width=12
        )
        self.copy_btn.grid(row=0, column=3, padx=5)

        # MAIN ACTION: Copy & Next (with hint)
        copy_next_frame = ttk.Frame(nav_frame)
        copy_next_frame.grid(row=0, column=4, padx=5)

        self.copy_next_btn = ttk.Button(
            copy_next_frame,
            text="COPY & NEXT",
            command=self.copy_and_next,
            width=15,
            style="Accent.TButton"
        )
        self.copy_next_btn.grid(row=0, column=0)

        ttk.Label(
            copy_next_frame,
            text="(or press Enter)",
            font=("Segoe UI", 8),
            foreground="#666666"
        ).grid(row=1, column=0)

        # Next button
        self.next_btn = ttk.Button(
            nav_frame,
            text="Next >>",
            command=self.go_next,
            width=12
        )
        self.next_btn.grid(row=0, column=5, padx=5)

        # === Row 7: Used/Remaining Stats ===
        stats_frame = ttk.Frame(self.root)
        stats_frame.grid(row=7, column=0, sticky="ew", padx=10, pady=5)
        stats_frame.columnconfigure(1, weight=1)

        self.stats_label = ttk.Label(
            stats_frame,
            text="",
            font=("Segoe UI", 9)
        )
        self.stats_label.grid(row=0, column=0, sticky="w")

        ttk.Button(
            stats_frame,
            text="Reset Used Status",
            command=self.reset_used_status
        ).grid(row=0, column=2, padx=5)

        ttk.Button(
            stats_frame,
            text="Go to First Unused",
            command=self.go_to_first_unused
        ).grid(row=0, column=3, padx=5)

        # === Row 8: Status Bar ===
        self.status_var = tk.StringVar(value="Ready - Paste prompts and click 'Load List'")
        self.status_bar = ttk.Label(
            self.root,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=(10, 5)
        )
        self.status_bar.grid(row=8, column=0, sticky="ew", padx=0, pady=0)

        # Configure styles
        self.configure_styles()

    def configure_styles(self):
        """Configure ttk styles."""
        style = ttk.Style()

        # Try to use a modern theme
        available_themes = style.theme_names()
        if "vista" in available_themes:
            style.theme_use("vista")
        elif "clam" in available_themes:
            style.theme_use("clam")

        # Accent button style (for main actions)
        style.configure(
            "Accent.TButton",
            font=("Segoe UI", 10, "bold")
        )

    def send_paste_to_previous_window(self):
        """Send Ctrl+V keystroke to the previously active window."""
        # Virtual key codes
        VK_CONTROL = 0x11
        VK_V = 0x56
        VK_A = 0x41
        VK_MENU = 0x12  # Alt key
        VK_TAB = 0x09
        KEYEVENTF_KEYUP = 0x0002

        # Use Alt+Tab to switch to previous window
        ctypes.windll.user32.keybd_event(VK_MENU, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_TAB, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_TAB, 0, KEYEVENTF_KEYUP, 0)
        ctypes.windll.user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)

        # Wait for window switch to complete
        time.sleep(0.15)

        # Send Ctrl+A first if enabled (select all to replace old prompt)
        if self.select_all_before_paste.get():
            ctypes.windll.user32.keybd_event(VK_CONTROL, 0, 0, 0)
            ctypes.windll.user32.keybd_event(VK_A, 0, 0, 0)
            ctypes.windll.user32.keybd_event(VK_A, 0, KEYEVENTF_KEYUP, 0)
            ctypes.windll.user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
            time.sleep(0.05)

        # Send Ctrl+V to paste
        ctypes.windll.user32.keybd_event(VK_CONTROL, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_V, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
        ctypes.windll.user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)

    def bind_shortcuts(self):
        """Bind keyboard shortcuts."""
        self.root.bind("<Return>", lambda e: self.copy_and_next() if e.widget != self.text_input else None)
        self.root.bind("<space>", lambda e: self.copy_and_next() if e.widget not in (self.text_input, self.listbox) else None)
        self.root.bind("<Left>", lambda e: self.go_previous())
        self.root.bind("<Right>", lambda e: self.go_next())
        self.root.bind("<Control-s>", lambda e: self.save_to_file())
        self.root.bind("<Control-o>", lambda e: self.load_from_file())
        self.root.bind("<Control-l>", lambda e: self.load_list())
        self.root.bind("<Escape>", lambda e: self.root.destroy())

    def toggle_stay_on_top(self):
        """Toggle window always-on-top."""
        self.root.attributes("-topmost", self.stay_on_top.get())
        status = "enabled" if self.stay_on_top.get() else "disabled"
        self.set_status(f"Stay on top {status}")

    def load_list(self):
        """Load prompts from the text input area."""
        text = self.text_input.get("1.0", tk.END)
        lines = text.split("\n")

        # Clean up: strip whitespace, remove empty lines
        self.item_list = [line.strip() for line in lines if line.strip()]

        if not self.item_list:
            self.set_status("Warning: No prompts to load (empty or whitespace only)")
            return

        # Reset state
        self.current_index = 0
        self.used_indices = set()

        # Update UI
        self.update_listbox()
        self.update_preview()
        self.update_progress()
        self.update_stats()

        self.set_status(f"Loaded {len(self.item_list)} prompts")
        self.save_state()

    def update_listbox(self):
        """Refresh the listbox display."""
        self.listbox.delete(0, tk.END)

        for i, item in enumerate(self.item_list):
            # Truncate long prompts for display
            display_text = item[:80] + "..." if len(item) > 80 else item

            # Add marker for used prompts
            if i in self.used_indices:
                display_text = f"\u2713 {display_text}"
            else:
                display_text = f"   {display_text}"

            self.listbox.insert(tk.END, display_text)

            # Color used items differently
            if i in self.used_indices:
                self.listbox.itemconfig(i, fg="#888888")

        # Select current item
        if self.item_list:
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(self.current_index)
            self.listbox.see(self.current_index)

            # Highlight current item
            self.listbox.itemconfig(self.current_index, bg="#e0e8ff")

    def update_preview(self):
        """Update the preview text area with current prompt."""
        self.preview_text.configure(state=tk.NORMAL)
        self.preview_text.delete("1.0", tk.END)

        if self.item_list:
            self.preview_text.insert("1.0", self.item_list[self.current_index])
        else:
            self.preview_text.insert("1.0", "(No prompts loaded)")

        self.preview_text.configure(state=tk.DISABLED)

    def update_progress(self):
        """Update the progress indicator."""
        if self.item_list:
            self.progress_label.configure(
                text=f"Prompt {self.current_index + 1} of {len(self.item_list)}"
            )
        else:
            self.progress_label.configure(text="No prompts loaded")

    def update_stats(self):
        """Update the used/remaining statistics."""
        if self.item_list:
            used = len(self.used_indices)
            total = len(self.item_list)
            remaining = total - used
            self.stats_label.configure(
                text=f"Used: {used} | Remaining: {remaining} | Total: {total}"
            )
        else:
            self.stats_label.configure(text="")

    def set_status(self, message):
        """Update the status bar."""
        self.status_var.set(message)

    def go_previous(self):
        """Navigate to previous prompt."""
        if not self.item_list:
            self.set_status("No prompts loaded")
            return

        if self.skip_used.get():
            # Find previous unused
            new_index = self.current_index - 1
            while new_index >= 0 and new_index in self.used_indices:
                new_index -= 1

            if new_index < 0:
                self.set_status("No previous unused prompts")
                return
            self.current_index = new_index
        else:
            if self.current_index > 0:
                self.current_index -= 1
            else:
                self.set_status("Already at first prompt")
                return

        self.update_listbox()
        self.update_preview()
        self.update_progress()
        self.set_status(f"Moved to prompt {self.current_index + 1}")

    def go_next(self):
        """Navigate to next prompt."""
        if not self.item_list:
            self.set_status("No prompts loaded")
            return

        if self.skip_used.get():
            # Find next unused
            new_index = self.current_index + 1
            while new_index < len(self.item_list) and new_index in self.used_indices:
                new_index += 1

            if new_index >= len(self.item_list):
                self.set_status("No more unused prompts!")
                return
            self.current_index = new_index
        else:
            if self.current_index < len(self.item_list) - 1:
                self.current_index += 1
            else:
                self.set_status("Already at last prompt")
                return

        self.update_listbox()
        self.update_preview()
        self.update_progress()
        self.set_status(f"Moved to prompt {self.current_index + 1}")

    def copy_current(self):
        """Copy current prompt to clipboard without advancing."""
        if not self.item_list:
            self.set_status("No prompts to copy")
            return

        prompt = self.item_list[self.current_index]

        # Copy to clipboard
        self.root.clipboard_clear()
        self.root.clipboard_append(prompt)
        self.root.update()  # Required for clipboard to persist

        # Mark as used
        self.used_indices.add(self.current_index)

        # Update UI
        self.update_listbox()
        self.update_stats()

        # Show truncated prompt in status
        display = prompt[:50] + "..." if len(prompt) > 50 else prompt
        self.set_status(f"Copied: {display}")

        self.save_state()

    def copy_and_next(self):
        """Copy current prompt and advance to next (main workflow action)."""
        if not self.item_list:
            self.set_status("No prompts to copy")
            return

        # Copy current
        prompt = self.item_list[self.current_index]
        self.root.clipboard_clear()
        self.root.clipboard_append(prompt)
        self.root.update()

        # Auto-paste if enabled
        if self.auto_paste.get():
            self.send_paste_to_previous_window()

        # Mark as used
        self.used_indices.add(self.current_index)

        # Show status
        display = prompt[:50] + "..." if len(prompt) > 50 else prompt

        # Advance if auto-advance is on
        if self.auto_advance.get():
            if self.skip_used.get():
                # Find next unused
                new_index = self.current_index + 1
                while new_index < len(self.item_list) and new_index in self.used_indices:
                    new_index += 1

                if new_index >= len(self.item_list):
                    self.set_status(f"Copied: {display} | ALL PROMPTS USED!")
                else:
                    self.current_index = new_index
                    self.set_status(f"Copied: {display} | Advanced to {self.current_index + 1}")
            else:
                if self.current_index < len(self.item_list) - 1:
                    self.current_index += 1
                    self.set_status(f"Copied: {display} | Advanced to {self.current_index + 1}")
                else:
                    self.set_status(f"Copied: {display} | Reached end of list")
        else:
            self.set_status(f"Copied: {display}")

        # Update UI
        self.update_listbox()
        self.update_preview()
        self.update_progress()
        self.update_stats()

        self.save_state()

    def on_listbox_double_click(self, event):
        """Handle double-click on listbox item."""
        selection = self.listbox.curselection()
        if selection:
            self.current_index = selection[0]
            self.copy_current()
            self.update_preview()
            self.update_progress()

    def on_listbox_select(self, event):
        """Handle single-click selection in listbox."""
        selection = self.listbox.curselection()
        if selection:
            self.current_index = selection[0]
            self.update_preview()
            self.update_progress()
            # Re-apply highlighting
            for i in range(len(self.item_list)):
                bg = "#e0e8ff" if i == self.current_index else ""
                self.listbox.itemconfig(i, bg=bg)

    def reset_used_status(self):
        """Clear all used markers."""
        self.used_indices = set()
        self.update_listbox()
        self.update_stats()
        self.set_status("Reset all prompts to unused")
        self.save_state()

    def go_to_first_unused(self):
        """Jump to the first unused prompt."""
        if not self.item_list:
            self.set_status("No prompts loaded")
            return

        for i in range(len(self.item_list)):
            if i not in self.used_indices:
                self.current_index = i
                self.update_listbox()
                self.update_preview()
                self.update_progress()
                self.set_status(f"Jumped to first unused prompt ({i + 1})")
                return

        self.set_status("All prompts have been used!")

    def clear_all(self):
        """Clear everything and reset."""
        if self.item_list:
            if not messagebox.askyesno("Confirm", "Clear all prompts and reset?"):
                return

        self.item_list = []
        self.current_index = 0
        self.used_indices = set()

        self.text_input.delete("1.0", tk.END)
        self.listbox.delete(0, tk.END)

        self.update_preview()
        self.update_progress()
        self.update_stats()
        self.set_status("Cleared all prompts")

        # Delete state file
        state_path = os.path.join(os.path.dirname(__file__), STATE_FILE)
        if os.path.exists(state_path):
            os.remove(state_path)

    def save_to_file(self):
        """Save prompts to a text file."""
        if not self.item_list:
            self.set_status("No prompts to save")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Save Prompts"
        )

        if filepath:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("\n".join(self.item_list))
            self.set_status(f"Saved {len(self.item_list)} prompts to {os.path.basename(filepath)}")

    def load_from_file(self):
        """Load prompts from a text file."""
        filepath = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Load Prompts"
        )

        if filepath:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # Put content in text area and load
            self.text_input.delete("1.0", tk.END)
            self.text_input.insert("1.0", content)
            self.load_list()
            self.set_status(f"Loaded prompts from {os.path.basename(filepath)}")

    def save_state(self):
        """Auto-save current state for session recovery."""
        state = {
            "item_list": self.item_list,
            "current_index": self.current_index,
            "used_indices": list(self.used_indices)
        }

        state_path = os.path.join(os.path.dirname(__file__) or ".", STATE_FILE)
        try:
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state, f)
        except Exception:
            pass  # Silent fail for state saving

    def load_state(self):
        """Load saved state from previous session."""
        state_path = os.path.join(os.path.dirname(__file__) or ".", STATE_FILE)

        if not os.path.exists(state_path):
            return

        try:
            with open(state_path, "r", encoding="utf-8") as f:
                state = json.load(f)

            self.item_list = state.get("item_list", [])
            self.current_index = state.get("current_index", 0)
            self.used_indices = set(state.get("used_indices", []))

            if self.item_list:
                # Restore text area
                self.text_input.delete("1.0", tk.END)
                self.text_input.insert("1.0", "\n".join(self.item_list))

                # Update UI
                self.update_listbox()
                self.update_preview()
                self.update_progress()
                self.update_stats()

                self.set_status(f"Restored {len(self.item_list)} prompts from previous session")
        except Exception:
            pass  # Silent fail for state loading


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    root = tk.Tk()
    app = ClipboardQueueApp(root)
    root.mainloop()
