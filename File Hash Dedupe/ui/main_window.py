"""Main window UI for File Hash Dedupe"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Optional
import threading
import queue
import atexit
import os

from config import ConfigManager
from hasher import FileDeduplicator
from ui.styles import ThemeManager


def _cleanup_all_children():
    """Emergency cleanup - kill all child processes on exit"""
    try:
        import psutil
        current = psutil.Process(os.getpid())
        for child in current.children(recursive=True):
            try:
                child.kill()
            except Exception:
                pass
    except Exception:
        pass

# Register cleanup to run on any exit
atexit.register(_cleanup_all_children)


class MainWindow:
    """Main application window"""

    def __init__(self, root: tk.Tk, config_manager: ConfigManager, version: str):
        """
        Initialize the main window

        Args:
            root: Tkinter root window
            config_manager: Configuration manager instance
            version: Application version string
        """
        self.root = root
        self.config = config_manager
        self.version = version

        # State
        self._is_processing = False
        self._cancel_requested = False
        self._message_queue = queue.Queue()

        # Setup window
        self._setup_window()

        # Apply theme
        ThemeManager.apply_theme(root)

        # Create UI
        self._create_widgets()

        # Load saved values
        self._load_config()

        # Start message processing
        self._process_messages()

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_window(self) -> None:
        """Configure the main window"""
        self.root.title(f"File Hash Dedupe v{self.version}")
        self.root.minsize(700, 550)

        # Restore geometry or set default
        geometry = self.config.window_geometry
        if geometry:
            try:
                self.root.geometry(geometry)
            except Exception:
                self.root.geometry("750x600")
        else:
            self.root.geometry("750x600")

        # Center window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - self.root.winfo_width()) // 2
        y = (self.root.winfo_screenheight() - self.root.winfo_height()) // 2
        self.root.geometry(f"+{x}+{y}")

    def _create_widgets(self) -> None:
        """Create all UI widgets"""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(
            main_frame,
            text="File Hash Dedupe",
            style='Header.TLabel',
            font=('Segoe UI', 18, 'bold')
        )
        title_label.pack(pady=(0, 5))

        subtitle_label = ttk.Label(
            main_frame,
            text="Find and move duplicate files based on content hash",
            foreground=ThemeManager.COLORS['fg_secondary']
        )
        subtitle_label.pack(pady=(0, 20))

        # Source folder section
        self._create_folder_section(main_frame)

        # Options section
        self._create_options_section(main_frame)

        # Action buttons
        self._create_action_buttons(main_frame)

        # Progress section
        self._create_progress_section(main_frame)

        # Status section
        self._create_status_section(main_frame)

    def _create_folder_section(self, parent: ttk.Frame) -> None:
        """Create the folder selection section"""
        folder_frame = ttk.LabelFrame(parent, text="Source Folder", padding="10")
        folder_frame.pack(fill=tk.X, pady=(0, 15))

        # Source folder
        source_frame = ttk.Frame(folder_frame)
        source_frame.pack(fill=tk.X)

        self.source_entry = tk.Entry(source_frame, font=('Segoe UI', 10))
        self.source_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        ThemeManager.style_entry(self.source_entry)

        source_btn = tk.Button(
            source_frame,
            text="Browse...",
            command=self._browse_source,
            bg=ThemeManager.COLORS['bg_light'],
            fg=ThemeManager.COLORS['fg_primary'],
            activebackground=ThemeManager.COLORS['accent'],
            activeforeground='white',
            font=('Segoe UI', 10),
            relief='flat',
            padx=15,
            pady=5,
            cursor='hand2'
        )
        source_btn.pack(side=tk.RIGHT)

        # Info label
        info_label = ttk.Label(
            folder_frame,
            text="Duplicates will be moved to a 'Dupes' subfolder in the source folder",
            foreground=ThemeManager.COLORS['fg_dim'],
            font=('Segoe UI', 9)
        )
        info_label.pack(anchor='w', pady=(10, 0))

    def _create_options_section(self, parent: ttk.Frame) -> None:
        """Create the options section"""
        options_frame = ttk.LabelFrame(parent, text="Options", padding="10")
        options_frame.pack(fill=tk.X, pady=(0, 15))

        # Recursive checkbox
        self.recursive_var = tk.BooleanVar(value=True)
        recursive_cb = ttk.Checkbutton(
            options_frame,
            text="Search subfolders recursively",
            variable=self.recursive_var
        )
        recursive_cb.pack(anchor='w')

    def _create_action_buttons(self, parent: ttk.Frame) -> None:
        """Create the action buttons"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=(0, 15))

        self.dedupe_button = tk.Button(
            button_frame,
            text="Find Duplicates",
            command=self._start_dedupe,
            bg=ThemeManager.COLORS['accent'],
            fg='white',
            activebackground=ThemeManager.COLORS['accent_hover'],
            activeforeground='white',
            disabledforeground=ThemeManager.COLORS['fg_dim'],
            font=('Segoe UI', 11, 'bold'),
            relief='flat',
            padx=30,
            pady=10,
            cursor='hand2'
        )
        self.dedupe_button.pack(side=tk.LEFT, padx=(0, 10))

        self.cancel_button = tk.Button(
            button_frame,
            text="Cancel",
            command=self._cancel_dedupe,
            state='disabled',
            bg=ThemeManager.COLORS['accent_dark'],
            fg=ThemeManager.COLORS['fg_primary'],
            activebackground=ThemeManager.COLORS['error'],
            activeforeground='white',
            disabledforeground=ThemeManager.COLORS['fg_dim'],
            font=('Segoe UI', 11, 'bold'),
            relief='flat',
            padx=30,
            pady=10,
            cursor='hand2'
        )
        self.cancel_button.pack(side=tk.LEFT)

    def _create_progress_section(self, parent: ttk.Frame) -> None:
        """Create the progress section"""
        progress_frame = ttk.Frame(parent)
        progress_frame.pack(fill=tk.X, pady=(0, 15))

        self.progress_label = ttk.Label(
            progress_frame,
            text="Ready",
            foreground=ThemeManager.COLORS['fg_secondary']
        )
        self.progress_label.pack(anchor='w', pady=(0, 5))

        self.progress_bar = ttk.Progressbar(
            progress_frame,
            style='green.Horizontal.TProgressbar',
            orient='horizontal',
            mode='determinate',
            maximum=100
        )
        self.progress_bar.pack(fill=tk.X)

    def _create_status_section(self, parent: ttk.Frame) -> None:
        """Create the status log section"""
        status_frame = ttk.LabelFrame(parent, text="Status", padding="10")
        status_frame.pack(fill=tk.BOTH, expand=True)

        # Listbox with scrollbar
        list_frame = ttk.Frame(status_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.status_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            height=12
        )
        self.status_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar.config(command=self.status_listbox.yview)

        # Apply theme
        ThemeManager.style_listbox(self.status_listbox)
        ThemeManager.style_scrollbar(scrollbar)

    def _browse_source(self) -> None:
        """Open folder browser for source folder"""
        initial_dir = self.source_entry.get() or str(Path.home())
        folder = filedialog.askdirectory(
            title="Select Source Folder",
            initialdir=initial_dir
        )
        if folder:
            self.source_entry.delete(0, tk.END)
            self.source_entry.insert(0, folder)

    def _load_config(self) -> None:
        """Load configuration into UI"""
        if self.config.source_folder:
            self.source_entry.insert(0, self.config.source_folder)

        self.recursive_var.set(self.config.recursive)

    def _save_config(self) -> None:
        """Save UI values to configuration"""
        self.config.source_folder = self.source_entry.get()
        self.config.recursive = self.recursive_var.get()
        self.config.window_geometry = self.root.geometry()
        self.config.save()

    def _start_dedupe(self) -> None:
        """Start the deduplication process"""
        # Validate
        source = self.source_entry.get().strip()
        if not source:
            messagebox.showerror("Validation Error", "Please select a source folder")
            return

        if not os.path.exists(source):
            messagebox.showerror("Validation Error", "Source folder does not exist")
            return

        # Save config
        self._save_config()

        # Update UI state
        self._is_processing = True
        self._cancel_requested = False
        self.dedupe_button.config(state='disabled')
        self.cancel_button.config(state='normal')
        self.progress_bar['value'] = 0
        self.status_listbox.delete(0, tk.END)

        # Start worker thread
        thread = threading.Thread(
            target=self._dedupe_worker,
            args=(source, self.recursive_var.get()),
            daemon=True
        )
        thread.start()

    def _dedupe_worker(self, source: str, recursive: bool) -> None:
        """Worker thread for deduplication"""
        try:
            deduplicator = FileDeduplicator(
                status_callback=lambda msg: self._message_queue.put(('status', msg)),
                progress_callback=lambda cur, total, fname: self._message_queue.put(
                    ('progress', {'current': cur, 'total': total, 'filename': fname})
                ),
                cancel_check=lambda: self._cancel_requested
            )

            results, total, unique, moved = deduplicator.find_and_move_duplicates(
                source,
                recursive=recursive
            )

            if self._cancel_requested:
                self._message_queue.put(('cancelled', None))
            else:
                self._message_queue.put(('complete', {
                    'total': total,
                    'unique': unique,
                    'moved': moved
                }))

        except Exception as e:
            self._message_queue.put(('error', {
                'type': 'unexpected',
                'message': str(e)
            }))

    def _process_messages(self) -> None:
        """Process messages from worker thread"""
        try:
            while True:
                msg_type, data = self._message_queue.get_nowait()

                if msg_type == 'status':
                    self.status_listbox.insert(tk.END, data)
                    self.status_listbox.see(tk.END)

                elif msg_type == 'progress':
                    current = data['current']
                    self.progress_bar['value'] = current
                    self.progress_bar.update_idletasks()
                    self.progress_label.config(
                        text=f"{current}%: {data['filename']}"
                    )

                elif msg_type == 'complete':
                    self._on_dedupe_complete(data)
                    return

                elif msg_type == 'cancelled':
                    self._on_dedupe_cancelled()
                    return

                elif msg_type == 'error':
                    self._on_dedupe_error(data)
                    return

        except queue.Empty:
            pass

        # Schedule next check
        self.root.after(50, self._process_messages)

    def _on_dedupe_complete(self, data: dict) -> None:
        """Handle deduplication completion"""
        self._is_processing = False
        self.dedupe_button.config(state='normal')
        self.cancel_button.config(state='disabled')
        self.progress_bar['value'] = 100
        self.progress_label.config(text="Complete!")

        total = data['total']
        unique = data['unique']
        moved = data['moved']

        messagebox.showinfo(
            "Success",
            f"Deduplication complete!\n\n"
            f"Total files scanned: {total}\n"
            f"Unique files: {unique}\n"
            f"Duplicates moved: {moved}"
        )

    def _on_dedupe_cancelled(self) -> None:
        """Handle deduplication cancellation"""
        self._is_processing = False
        self.dedupe_button.config(state='normal')
        self.cancel_button.config(state='disabled')
        self.progress_label.config(text="Cancelled")

        self.status_listbox.insert(tk.END, "Operation cancelled by user")
        self.status_listbox.see(tk.END)

    def _on_dedupe_error(self, data: dict) -> None:
        """Handle deduplication error"""
        self._is_processing = False
        self.dedupe_button.config(state='normal')
        self.cancel_button.config(state='disabled')
        self.progress_label.config(text="Error")

        error_type = data['type']
        message = data['message']

        if error_type == 'validation':
            messagebox.showerror("Validation Error", message)
        else:
            messagebox.showerror("Error", f"An unexpected error occurred: {message}")

    def _cancel_dedupe(self) -> None:
        """Request cancellation"""
        if self._is_processing:
            self._cancel_requested = True
            self.cancel_button.config(state='disabled')
            self.progress_label.config(text="Cancelling...")
            self.status_listbox.insert(tk.END, "Cancellation requested...")
            self.status_listbox.see(tk.END)

    def _on_close(self) -> None:
        """Handle window close"""
        if self._is_processing:
            self._cancel_requested = True

        self._save_config()
        self.root.destroy()
