"""
MP4 Metadata Editor
Drag and drop one or more MP4 files to update their metadata.
Only fields that are filled in will be written — blank fields are ignored.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os
import re
import sys

# ── Optional dependencies ─────────────────────────────────────────────────────
try:
    import mutagen.mp4
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "mutagen"])
    import mutagen.mp4

try:
    import tkinterdnd2
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

# ── Metadata field definitions ────────────────────────────────────────────────
# (label, mutagen_key, is_integer, use_textbox)
FIELDS = [
    ("Title",            "\xa9nam", False, False),
    ("Artist",           "\xa9ART", False, False),
    ("Album Artist",     "aART",    False, False),
    ("Album",            "\xa9alb", False, False),
    ("Year",             "\xa9day", False, False),
    ("Genre",            "\xa9gen", False, False),
    ("Composer",         "\xa9wrt", False, False),
    ("Grouping",         "\xa9grp", False, False),
    ("Copyright",        "cprt",    False, False),
    ("Show",             "tvsh",    False, False),
    ("Episode ID",       "tven",    False, False),
    ("Episode Number",   "tves",    True,  False),
    ("Season Number",    "tvsn",    True,  False),
    ("Category",         "catg",    False, False),
    ("Keywords",         "keyw",    False, False),
    ("Comment",          "\xa9cmt", False, True),
    ("Description",      "desc",    False, True),
    ("Long Description", "ldes",    False, True),
    ("Lyrics",           "\xa9lyr", False, True),
]

# ── Theme ─────────────────────────────────────────────────────────────────────
DARK_BG   = "#0d1b2a"
PANEL_BG  = "#112240"
ACCENT    = "#1e3a5f"
HIGHLIGHT = "#2e6da4"
TEXT_FG   = "#cdd9e5"
ENTRY_BG  = "#1c2e40"
ENTRY_FG  = "#e6f0fa"
DROP_BG   = "#0a2540"
SUCCESS   = "#3fb950"
ERROR     = "#f85149"
WARN      = "#e3b341"

F_MAIN    = ("Segoe UI", 10)
F_LABEL   = ("Segoe UI", 9)
F_TITLE   = ("Segoe UI", 13, "bold")
F_SMALL   = ("Segoe UI", 8)


# ── Core write logic ──────────────────────────────────────────────────────────
def write_metadata(filepath: str, fields: dict) -> tuple[bool, str]:
    """Write only non-blank fields.  Returns (ok, message)."""
    try:
        audio = mutagen.mp4.MP4(filepath)
        if audio.tags is None:
            audio.add_tags()

        changed = 0
        for label, key, is_int, _ in FIELDS:
            value = fields.get(key, "").strip()
            if not value:
                continue
            if is_int:
                try:
                    audio.tags[key] = [int(value)]
                except ValueError:
                    return False, f"'{label}' must be a whole number."
            else:
                audio.tags[key] = [value]
            changed += 1

        if changed == 0:
            return False, "No fields to write (all blank)."

        audio.save()
        return True, f"Updated {changed} field(s)."
    except Exception as exc:
        return False, str(exc)


# ── Main window ───────────────────────────────────────────────────────────────
class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("MP4 Metadata Editor v1.0.0")
        self.root.geometry("800x860")
        self.root.minsize(640, 600)
        self.root.configure(bg=DARK_BG)

        self.queued_files: list[str] = []
        # Maps mutagen key → (StringVar, optional Text widget)
        self.field_widgets: dict[str, tuple[tk.StringVar, tk.Text | None]] = {}

        self._build_ui()
        self._setup_dnd()

    # ── UI ────────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = self.root

        # Title bar
        hdr = tk.Frame(root, bg=ACCENT, pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="MP4 Metadata Editor", font=F_TITLE,
                 bg=ACCENT, fg=ENTRY_FG).pack(side="left", padx=16)
        tk.Label(hdr, text="Fill in any fields — blank fields are never overwritten",
                 font=F_SMALL, bg=ACCENT, fg=TEXT_FG).pack(side="right", padx=16)

        body = tk.Frame(root, bg=DARK_BG)
        body.pack(fill="both", expand=True, padx=12, pady=8)

        # Drop zone
        self.drop_label = tk.Label(
            body,
            text="⊕  Drag & drop MP4 files here  —  or click to browse",
            font=("Segoe UI", 10, "italic"),
            bg=DROP_BG, fg=HIGHLIGHT, pady=18, cursor="hand2",
            relief="ridge", bd=2
        )
        self.drop_label.pack(fill="x", pady=(0, 6))
        self.drop_label.bind("<Button-1>", self._browse)

        # File list
        lf = tk.LabelFrame(body, text=" Queued files ", font=F_LABEL,
                           bg=PANEL_BG, fg=TEXT_FG, bd=1)
        lf.pack(fill="x", pady=(0, 8))

        sb = tk.Scrollbar(lf)
        self.listbox = tk.Listbox(lf, height=5, bg=ENTRY_BG, fg=ENTRY_FG,
                                  selectbackground=HIGHLIGHT, font=F_LABEL,
                                  yscrollcommand=sb.set, activestyle="none",
                                  relief="flat", bd=0)
        sb.config(command=self.listbox.yview)
        sb.pack(side="right", fill="y")
        self.listbox.pack(fill="x", padx=4, pady=(2, 4))

        br = tk.Frame(lf, bg=PANEL_BG)
        br.pack(fill="x", padx=8, pady=(0, 6))
        self._btn(br, "Remove Selected", self._remove_selected).pack(side="left", padx=(0, 6))
        self._btn(br, "Clear All Files", self._clear_files).pack(side="left")

        # Metadata fields in a scrollable canvas
        fields_wrap = tk.Frame(body, bg=DARK_BG)
        fields_wrap.pack(fill="both", expand=True)

        canvas = tk.Canvas(fields_wrap, bg=DARK_BG, highlightthickness=0)
        vsb = tk.Scrollbar(fields_wrap, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self.inner = tk.Frame(canvas, bg=DARK_BG)
        win_id = canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.inner.bind("<Configure>",
                        lambda *_: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(win_id, width=e.width))
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        self._build_fields()

        # Bottom button row
        bot = tk.Frame(body, bg=DARK_BG)
        bot.pack(fill="x", pady=8)
        self._btn(bot, "Clear All Fields", self._clear_fields).pack(side="left")
        self._btn(bot, "Apply to All Files", self._apply,
                  bg=HIGHLIGHT, width=22).pack(side="right")

        # Status bar
        self.status_var = tk.StringVar(
            value="Ready — add files and fill in the metadata fields you want to update.")
        self.status_label = tk.Label(root, textvariable=self.status_var, font=F_SMALL,
                                     bg=ACCENT, fg=TEXT_FG, anchor="w", padx=10, pady=5)
        self.status_label.pack(fill="x", side="bottom")

    def _build_fields(self):
        """Two-column grid of entry / text widgets for each metadata field."""
        col_count = 2
        short_fields = [(l, k, n, t) for l, k, n, t in FIELDS if not t]
        long_fields  = [(l, k, n, t) for l, k, n, t in FIELDS if t]

        # Short single-line fields in two columns
        for i, (label, key, is_int, _) in enumerate(short_fields):
            row, col = divmod(i, col_count)
            cell = tk.Frame(self.inner, bg=PANEL_BG, bd=1, relief="flat")
            cell.grid(row=row, column=col, padx=5, pady=4, sticky="nsew")
            self.inner.columnconfigure(col, weight=1)

            hint = " (integer)" if is_int else ""
            tk.Label(cell, text=f"{label}{hint}", font=F_LABEL,
                     bg=PANEL_BG, fg=TEXT_FG, anchor="w").pack(fill="x", padx=8, pady=(6, 2))

            var = tk.StringVar()
            entry = tk.Entry(cell, textvariable=var, bg=ENTRY_BG, fg=ENTRY_FG,
                             insertbackground=ENTRY_FG, font=F_LABEL,
                             relief="flat", bd=4)
            entry.pack(fill="x", padx=8, pady=(0, 6))
            self.field_widgets[key] = (var, None)

        # Long multi-line text fields, each spanning full width
        base_row = (len(short_fields) + col_count - 1) // col_count
        for i, (label, key, _, _) in enumerate(long_fields):
            cell = tk.Frame(self.inner, bg=PANEL_BG, bd=1, relief="flat")
            cell.grid(row=base_row + i, column=0, columnspan=col_count,
                      padx=5, pady=4, sticky="nsew")

            tk.Label(cell, text=label, font=F_LABEL,
                     bg=PANEL_BG, fg=TEXT_FG, anchor="w").pack(fill="x", padx=8, pady=(6, 2))

            var = tk.StringVar()
            txt = tk.Text(cell, height=4, bg=ENTRY_BG, fg=ENTRY_FG,
                          insertbackground=ENTRY_FG, font=F_LABEL,
                          relief="flat", bd=4, wrap="word")
            txt.pack(fill="x", padx=8, pady=(0, 6))

            def _sync(*_, t=txt, v=var):
                v.set(t.get("1.0", "end-1c"))

            txt.bind("<KeyRelease>", _sync)
            self.field_widgets[key] = (var, txt)

    def _btn(self, parent, text, command=None, bg=ACCENT, width=None):
        kw = dict(text=text, command=command, bg=bg, fg=ENTRY_FG,
                  font=F_LABEL, relief="flat", cursor="hand2",
                  padx=10, pady=5, activebackground=HIGHLIGHT, activeforeground="white")
        if width:
            kw["width"] = width
        b = tk.Button(parent, **kw)
        b.bind("<Enter>", lambda e, _b=b: _b.configure(bg=HIGHLIGHT))
        b.bind("<Leave>", lambda e, _b=b, _c=bg: _b.configure(bg=_c))
        return b

    # ── DnD ───────────────────────────────────────────────────────────────
    def _setup_dnd(self):
        if not DND_AVAILABLE:
            self.drop_label.configure(
                text="Click here to browse for MP4 files"
                     "  (install tkinterdnd2 to enable drag & drop)"
            )
            return
        # Register drop target on both the label and the root window so
        # files can be dropped anywhere on the app.
        for widget in (self.drop_label, self.listbox, self.root):
            try:
                widget.drop_target_register(tkinterdnd2.DND_FILES)
                widget.dnd_bind("<<Drop>>", self._on_drop)
            except Exception as exc:
                print(f"DnD register failed on {widget}: {exc}")

    def _on_drop(self, event):
        # tkinterdnd2 wraps paths containing spaces in {braces}
        paths = re.findall(r'\{([^}]+)\}|(\S+)', event.data)
        paths = [a or b for a, b in paths]
        self._add_files([p for p in paths if p.lower().endswith(".mp4")])

    # ── File list management ──────────────────────────────────────────────
    def _browse(self, *_):
        paths = filedialog.askopenfilenames(
            title="Select MP4 files",
            filetypes=[("MP4 files", "*.mp4"), ("All files", "*.*")]
        )
        self._add_files(list(paths))

    def _add_files(self, paths: list[str]):
        added = 0
        for p in paths:
            if p not in self.queued_files:
                self.queued_files.append(p)
                self.listbox.insert("end", os.path.basename(p))
                added += 1
        if added:
            self._status(f"Added {added} file(s).  Total queued: {len(self.queued_files)}.", WARN)

    def _remove_selected(self):
        for idx in reversed(self.listbox.curselection()):
            self.listbox.delete(idx)
            del self.queued_files[idx]
        self._status(f"{len(self.queued_files)} file(s) in queue.", TEXT_FG)

    def _clear_files(self):
        self.queued_files.clear()
        self.listbox.delete(0, "end")
        self._status("File list cleared.", TEXT_FG)

    def _clear_fields(self):
        for var, txt in self.field_widgets.values():
            var.set("")
            if txt:
                txt.delete("1.0", "end")

    # ── Apply ─────────────────────────────────────────────────────────────
    def _apply(self):
        if not self.queued_files:
            messagebox.showwarning("No files", "Add at least one MP4 file first.")
            return

        fields = {key: var.get() for key, (var, _) in self.field_widgets.items()}
        if not any(v.strip() for v in fields.values()):
            messagebox.showwarning("Nothing to write",
                                   "Fill in at least one metadata field before applying.")
            return

        self._status("Writing metadata…", WARN)
        threading.Thread(
            target=self._apply_thread,
            args=(list(self.queued_files), fields),
            daemon=True
        ).start()

    def _apply_thread(self, files: list[str], fields: dict):
        results = []
        ok = fail = 0
        for path in files:
            success, msg = write_metadata(path, fields)
            name = os.path.basename(path)
            results.append((success, name, msg))
            if success:
                ok += 1
            else:
                fail += 1

        summary = f"{ok} file(s) updated"
        if fail:
            summary += f", {fail} failed"
        color = SUCCESS if fail == 0 else (WARN if ok > 0 else ERROR)
        self.root.after(0, lambda: self._show_results(summary, results, color))

    def _show_results(self, summary: str, results: list, color: str):
        self._status(summary, color)
        ResultWindow(self.root, summary, results)

    def _status(self, text: str, color: str = TEXT_FG):
        self.status_var.set(text)
        self.status_label.configure(fg=color)


# ── Results popup ─────────────────────────────────────────────────────────────
class ResultWindow(tk.Toplevel):
    def __init__(self, parent, summary: str, results: list):
        super().__init__(parent)
        self.title("Results")
        self.configure(bg=DARK_BG)
        self.geometry("580x360")
        self.grab_set()
        self.resizable(True, True)

        tk.Label(self, text=summary, font=F_TITLE, bg=DARK_BG,
                 fg=ENTRY_FG, pady=10).pack(fill="x", padx=14)

        frame = tk.Frame(self, bg=DARK_BG)
        frame.pack(fill="both", expand=True, padx=14, pady=(0, 8))

        vsb = tk.Scrollbar(frame)
        vsb.pack(side="right", fill="y")

        txt = tk.Text(frame, bg=PANEL_BG, fg=ENTRY_FG, font=F_LABEL,
                      relief="flat", bd=4, yscrollcommand=vsb.set, wrap="word")
        vsb.config(command=txt.yview)
        txt.pack(fill="both", expand=True)
        txt.tag_configure("ok",  foreground=SUCCESS)
        txt.tag_configure("err", foreground=ERROR)

        for success, name, msg in results:
            tag = "ok" if success else "err"
            icon = "✓" if success else "✗"
            txt.insert("end", f"{icon}  {name}\n    {msg}\n\n", tag)
        txt.configure(state="disabled")

        tk.Button(self, text="Close", command=self.destroy,
                  bg=HIGHLIGHT, fg=ENTRY_FG, font=F_LABEL,
                  relief="flat", padx=24, pady=6,
                  cursor="hand2").pack(pady=8)


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    if DND_AVAILABLE:
        root = tkinterdnd2.TkinterDnD.Tk()
    else:
        root = tk.Tk()

    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
