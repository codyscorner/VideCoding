import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import zipfile
import os
import shutil

# ── Colour palette ──────────────────────────────────────────────────────────
BG_DARK      = "#1a1f2e"
BG_MID       = "#222840"
BG_PANEL     = "#2a3150"
ACCENT       = "#4a90d9"
ACCENT_HOVER = "#5ba3f0"
ACCENT_DIM   = "#2e5f99"
TEXT_BRIGHT  = "#e8eaf6"
TEXT_DIM     = "#8899bb"
BORDER       = "#3a4a70"
SUCCESS      = "#4dd0a0"
ERROR_COL    = "#e05c5c"

FONT_TITLE  = ("Segoe UI", 11, "bold")
FONT_LABEL  = ("Segoe UI", 9)
FONT_ENTRY  = ("Segoe UI", 9)
FONT_BTN    = ("Segoe UI", 9, "bold")
FONT_STATUS = ("Consolas", 8)


class HoverButton(tk.Button):
    def __init__(self, master, **kw):
        self._bg      = kw.pop("bg",            ACCENT)
        self._hover   = kw.pop("hover_bg",      ACCENT_HOVER)
        self._fg      = kw.pop("fg",            TEXT_BRIGHT)
        super().__init__(master, bg=self._bg, fg=self._fg,
                         activebackground=self._hover, activeforeground=TEXT_BRIGHT,
                         relief="flat", cursor="hand2", bd=0, **kw)
        self.bind("<Enter>", lambda _: self.config(bg=self._hover))
        self.bind("<Leave>", lambda _: self.config(bg=self._bg))


class UnzipperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Unzipper  V-1.0.0")
        self.root.geometry("660x480")
        self.root.resizable(False, False)
        self.root.configure(bg=BG_DARK)

        self._build_ui()

    # ── UI construction ───────────────────────────────────────────────────
    def _build_ui(self):
        # ── Title bar strip ──────────────────────────────────────────────
        title_bar = tk.Frame(self.root, bg=ACCENT_DIM, height=42)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)
        tk.Label(title_bar, text="⚡  Unzipper", font=("Segoe UI", 13, "bold"),
                 bg=ACCENT_DIM, fg=TEXT_BRIGHT).pack(side="left", padx=16, pady=8)
        tk.Label(title_bar, text="V-1.0.0", font=("Segoe UI", 8),
                 bg=ACCENT_DIM, fg=TEXT_DIM).pack(side="left", pady=12)

        # ── Main content frame ───────────────────────────────────────────
        body = tk.Frame(self.root, bg=BG_DARK, padx=20, pady=14)
        body.pack(fill="both", expand=True)

        # ── Path rows ────────────────────────────────────────────────────
        self.source_entry = self._path_row(body, "Source Folder", 0, self.browse_source)
        self.dest_entry   = self._path_row(body, "Destination Folder", 1, self.browse_dest)

        # ── Filename row ─────────────────────────────────────────────────
        tk.Label(body, text="Filename  (Flat Unzip)", font=FONT_LABEL,
                 bg=BG_DARK, fg=TEXT_DIM).grid(row=2, column=0, sticky="w", pady=(10, 2))
        self.filename_entry = tk.Entry(body, font=FONT_ENTRY, width=46,
                                       bg=BG_PANEL, fg=TEXT_BRIGHT,
                                       insertbackground=TEXT_BRIGHT,
                                       relief="flat", bd=0,
                                       highlightthickness=1,
                                       highlightbackground=BORDER,
                                       highlightcolor=ACCENT)
        self.filename_entry.grid(row=3, column=0, columnspan=3, sticky="ew", ipady=5)
        self.filename_entry.insert(0, "UnzippedFile")

        # ── Action buttons ────────────────────────────────────────────────
        btn_frame = tk.Frame(body, bg=BG_DARK)
        btn_frame.grid(row=4, column=0, columnspan=3, pady=16, sticky="ew")
        btn_frame.columnconfigure((0, 1), weight=1)

        HoverButton(btn_frame, text="Unzip  —  Flat",
                    font=FONT_BTN, padx=14, pady=8,
                    command=self.unzip_flat).grid(row=0, column=0, padx=(0, 6), sticky="ew")

        HoverButton(btn_frame, text="Unzip  —  Keep Structure",
                    font=FONT_BTN, padx=14, pady=8,
                    bg=BG_PANEL, hover_bg=BORDER,
                    command=self.unzip_with_structure).grid(row=0, column=1, padx=(6, 0), sticky="ew")

        # ── Divider ───────────────────────────────────────────────────────
        tk.Frame(body, bg=BORDER, height=1).grid(row=5, column=0, columnspan=3,
                                                  sticky="ew", pady=(0, 8))

        # ── Status box ────────────────────────────────────────────────────
        tk.Label(body, text="Status", font=FONT_LABEL,
                 bg=BG_DARK, fg=TEXT_DIM).grid(row=6, column=0, sticky="w")
        self.status_box = scrolledtext.ScrolledText(
            body, font=FONT_STATUS, width=72, height=9,
            bg=BG_MID, fg=TEXT_BRIGHT, insertbackground=TEXT_BRIGHT,
            relief="flat", bd=0,
            highlightthickness=1, highlightbackground=BORDER,
            highlightcolor=ACCENT, state="disabled",
            wrap="word"
        )
        self.status_box.grid(row=7, column=0, columnspan=3, sticky="nsew")
        self.status_box.tag_config("ok",  foreground=SUCCESS)
        self.status_box.tag_config("err", foreground=ERROR_COL)
        self.status_box.tag_config("inf", foreground=ACCENT)

        body.columnconfigure(0, weight=1)

    def _path_row(self, parent, label_text, row_base, browse_cmd):
        tk.Label(parent, text=label_text, font=FONT_LABEL,
                 bg=BG_DARK, fg=TEXT_DIM).grid(row=row_base * 2, column=0,
                                                sticky="w", pady=(8, 2))
        row = row_base * 2 + 1
        entry = tk.Entry(parent, font=FONT_ENTRY, width=46,
                         bg=BG_PANEL, fg=TEXT_BRIGHT,
                         insertbackground=TEXT_BRIGHT,
                         relief="flat", bd=0,
                         highlightthickness=1,
                         highlightbackground=BORDER,
                         highlightcolor=ACCENT)
        entry.grid(row=row, column=0, columnspan=2, sticky="ew", ipady=5)
        HoverButton(parent, text="Browse", font=FONT_BTN,
                    padx=10, pady=4, command=browse_cmd,
                    bg=BG_PANEL, hover_bg=BORDER
                    ).grid(row=row, column=2, padx=(8, 0), sticky="ew")
        return entry

    # ── Helpers ───────────────────────────────────────────────────────────
    def browse_source(self):
        folder = filedialog.askdirectory()
        if folder:
            self.source_entry.delete(0, tk.END)
            self.source_entry.insert(0, folder)

    def browse_dest(self):
        folder = filedialog.askdirectory()
        if folder:
            self.dest_entry.delete(0, tk.END)
            self.dest_entry.insert(0, folder)

    def log_status(self, message, tag=""):
        self.status_box.config(state="normal")
        self.status_box.insert(tk.END, message + "\n", tag)
        self.status_box.see(tk.END)
        self.status_box.config(state="disabled")

    def _validate_folders(self, source, dest):
        if not source or not dest:
            messagebox.showerror("Error", "Please select source and destination folders.")
            return False
        if not os.path.exists(source):
            messagebox.showerror("Error", f"Source folder does not exist:\n{source}")
            return False
        if not os.path.exists(dest):
            os.makedirs(dest)
        return True

    # ── Unzip modes ───────────────────────────────────────────────────────
    def unzip_flat(self):
        source   = self.source_entry.get()
        dest     = self.dest_entry.get()
        filename = self.filename_entry.get().strip()
        if not filename:
            messagebox.showerror("Error", "Please provide a filename for flat unzip.")
            return
        if not self._validate_folders(source, dest):
            return

        zip_files = [f for f in os.listdir(source) if f.lower().endswith(".zip")]
        if not zip_files:
            self.log_status("No ZIP files found in source folder.", "err")
            return

        self.log_status(f"Starting flat unzip — {len(zip_files)} ZIP(s) found…", "inf")
        counter = 1
        for zip_file in zip_files:
            zip_path = os.path.join(source, zip_file)
            try:
                with zipfile.ZipFile(zip_path, "r") as zf:
                    for file_info in zf.filelist:
                        if not file_info.is_dir():
                            ext      = os.path.splitext(file_info.filename)[1]
                            new_name = f"{filename}_{counter:06d}{ext}"
                            new_path = os.path.join(dest, new_name)
                            with zf.open(file_info) as src, open(new_path, "wb") as dst:
                                shutil.copyfileobj(src, dst)
                            self.log_status(f"  Extracted: {new_name}", "ok")
                            counter += 1
            except Exception as e:
                self.log_status(f"  Error extracting {zip_file}: {e}", "err")

        self.log_status("Flat unzip completed.", "inf")

    def unzip_with_structure(self):
        source = self.source_entry.get()
        dest   = self.dest_entry.get()
        if not self._validate_folders(source, dest):
            return

        zip_files = [f for f in os.listdir(source) if f.lower().endswith(".zip")]
        if not zip_files:
            self.log_status("No ZIP files found in source folder.", "err")
            return

        self.log_status(f"Starting structured unzip — {len(zip_files)} ZIP(s) found…", "inf")
        for zip_file in zip_files:
            zip_name    = os.path.splitext(zip_file)[0]
            folder_name = zip_name
            counter     = 0
            while os.path.exists(os.path.join(dest, folder_name)):
                counter    += 1
                folder_name = f"{zip_name}_{counter:06d}"
            folder_path = os.path.join(dest, folder_name)

            zip_path = os.path.join(source, zip_file)
            try:
                with zipfile.ZipFile(zip_path, "r") as zf:
                    zf.extractall(folder_path)
                self.log_status(f"  Extracted  {zip_file}  →  {folder_name}", "ok")
            except Exception as e:
                self.log_status(f"  Error extracting {zip_file}: {e}", "err")

        self.log_status("Structured unzip completed.", "inf")


if __name__ == "__main__":
    import os
    from pathlib import Path
    root = tk.Tk()
    _icon = Path(__file__).parent / "app_icon.ico"
    if _icon.exists():
        try:
            root.iconbitmap(str(_icon))
        except Exception:
            pass
    app  = UnzipperApp(root)
    root.mainloop()
