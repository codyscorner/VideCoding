"""Main window UI for Image People Sorter"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Optional
import threading
import queue
import atexit
import os

from config import ConfigManager
from face_detector import ImagePeopleSorter
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

        # Set up window
        self.root.title(f"Image People Sorter (V-{self.version})")
        self.root.geometry("900x700")
        self.root.configure(bg='#2D0A0A')  # Deep Maroon background

        # Set minimum window size
        self.root.minsize(675, 525)

        # Initialize theme
        self.style = ttk.Style()
        self.theme = ThemeManager(self.style, 'crimson_slate')
        self.colors = self.theme.get_all_colors()
        self.fonts = self.theme.get_all_fonts()

        # UI Variables
        self.source_var = tk.StringVar(value=self.config.get("default_source_folder", ""))
        self.dest_var = tk.StringVar(value=self.config.get("default_destination_folder", ""))
        self.recursive_var = tk.BooleanVar(value=self.config.get("recursive_search", True))
        self.copy_mode_var = tk.BooleanVar(value=self.config.get("copy_mode", True))

        # Threading state
        self._sort_thread: Optional[threading.Thread] = None
        self._progress_queue: queue.Queue = queue.Queue()
        self._cancel_requested: bool = False
        self._is_sorting: bool = False

        # Build UI
        self._setup_ui()

        # Handle window close to clean up properly
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_ui(self) -> None:
        """Set up the user interface"""
        # Main container
        main_frame = ttk.Frame(self.root, style='Dark.TFrame')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # Title
        title_label = ttk.Label(
            main_frame,
            text="Image People Sorter",
            style='Heading.TLabel',
            font=('Segoe UI', 18, 'bold')
        )
        title_label.pack(pady=(0, 5))

        subtitle_label = ttk.Label(
            main_frame,
            text="Sort images by detecting faces - separates people from non-people images",
            style='Dark.TLabel',
            font=self.fonts['italic']
        )
        subtitle_label.pack(pady=(0, 20))

        # Folder inputs section
        self._create_folder_section(main_frame)

        # Options section
        self._create_options_section(main_frame)

        # Action buttons
        self._create_buttons(main_frame)

        # Progress section
        self._create_progress_section(main_frame)

        # Status section
        self._create_status_section(main_frame)

    def _create_folder_section(self, parent: ttk.Frame) -> None:
        """Create folder input section"""
        # Source folder
        self._create_folder_input(
            parent,
            "Source Folder:",
            self.source_var,
            self._browse_source
        )

        # Destination folder
        self._create_folder_input(
            parent,
            "Destination Folder:",
            self.dest_var,
            self._browse_destination
        )

        # Info label
        info_frame = ttk.Frame(parent, style='Dark.TFrame')
        info_frame.pack(fill='x', pady=(0, 10))

        ttk.Label(
            info_frame,
            text="Images will be sorted into 'People' and 'No_People' subfolders",
            style='Dark.TLabel',
            font=self.fonts['italic']
        ).pack(anchor='w')

    def _create_folder_input(
        self,
        parent: ttk.Frame,
        label_text: str,
        variable: tk.StringVar,
        browse_command
    ) -> None:
        """Create a folder input row"""
        frame = ttk.Frame(parent, style='Dark.TFrame')
        frame.pack(fill='x', pady=(0, 10))

        ttk.Label(
            frame,
            text=label_text,
            style='Dark.TLabel'
        ).pack(anchor='w')

        input_frame = ttk.Frame(frame, style='Dark.TFrame')
        input_frame.pack(fill='x', pady=(5, 0))

        entry = tk.Entry(
            input_frame,
            textvariable=variable,
            width=80,
            bg=self.colors['input_bg'],
            fg=self.colors['input_fg'],
            insertbackground=self.colors['insert_cursor'],
            bd=1,
            relief='solid',
            highlightbackground=self.colors['border'],
            highlightcolor=self.colors['accent'],
            highlightthickness=1
        )
        entry.pack(side='left', fill='x', expand=True, padx=(0, 10))

        browse_btn = tk.Button(
            input_frame,
            text="Browse...",
            command=browse_command,
            bg=self.colors['bg_surface'],
            fg=self.colors['text_primary'],
            font=self.fonts['default'],
            relief='raised',
            bd=1,
            padx=15,
            pady=5,
            activebackground=self.colors['border'],
            activeforeground=self.colors['text_primary']
        )
        browse_btn.pack(side='right')

    def _create_options_section(self, parent: ttk.Frame) -> None:
        """Create options section"""
        options_frame = ttk.Frame(parent, style='Dark.TFrame')
        options_frame.pack(fill='x', pady=(0, 15))

        ttk.Label(
            options_frame,
            text="Options",
            style='Heading.TLabel',
            font=self.fonts['heading']
        ).pack(anchor='w', pady=(0, 10))

        # Options row
        options_row = ttk.Frame(options_frame, style='Dark.TFrame')
        options_row.pack(fill='x')

        # Recursive search
        ttk.Checkbutton(
            options_row,
            text="Search subfolders recursively",
            variable=self.recursive_var,
            style='Dark.TCheckbutton'
        ).pack(side='left', padx=(0, 40))

        # File operation mode label
        ttk.Label(
            options_row,
            text="File Operation:",
            style='Dark.TLabel'
        ).pack(side='left', padx=(0, 10))

        # Copy radio button
        ttk.Radiobutton(
            options_row,
            text="Copy",
            variable=self.copy_mode_var,
            value=True,
            style='Dark.TRadiobutton'
        ).pack(side='left', padx=(0, 10))

        # Move radio button
        ttk.Radiobutton(
            options_row,
            text="Move",
            variable=self.copy_mode_var,
            value=False,
            style='Dark.TRadiobutton'
        ).pack(side='left')

    def _create_buttons(self, parent: ttk.Frame) -> None:
        """Create action buttons"""
        button_frame = ttk.Frame(parent, style='Dark.TFrame')
        button_frame.pack(fill='x', pady=(0, 15))

        # Sort button
        self.sort_button = tk.Button(
            button_frame,
            text="Sort Images",
            command=self._start_sort,
            bg=self.colors['button_bg'],
            fg=self.colors['button_fg'],
            font=self.fonts['button'],
            relief='raised',
            bd=2,
            padx=25,
            pady=10,
            activebackground=self.colors['button_hover'],
            activeforeground=self.colors['button_fg']
        )
        self.sort_button.pack(side='left', padx=(0, 10))

        # Cancel button
        self.cancel_button = tk.Button(
            button_frame,
            text="Cancel",
            command=self._cancel_sort,
            bg=self.colors['accent_dim'],
            fg=self.colors['button_fg'],
            font=self.fonts['button'],
            relief='raised',
            bd=2,
            padx=25,
            pady=10,
            state='disabled',
            activebackground=self.colors['button_bg'],
            activeforeground=self.colors['button_fg']
        )
        self.cancel_button.pack(side='left')

    def _create_progress_section(self, parent: ttk.Frame) -> None:
        """Create progress section"""
        progress_frame = ttk.Frame(parent, style='Dark.TFrame')
        progress_frame.pack(fill='x', pady=(0, 15))

        # Progress label
        self.progress_label = ttk.Label(
            progress_frame,
            text="Ready",
            style='Dark.TLabel'
        )
        self.progress_label.pack(anchor='w', pady=(0, 5))

        # Progress bar
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            style='Crimson.Horizontal.TProgressbar',
            orient='horizontal',
            length=400,
            mode='determinate'
        )
        self.progress_bar.pack(fill='x')

    def _create_status_section(self, parent: ttk.Frame) -> None:
        """Create status output section"""
        status_frame = ttk.Frame(parent, style='Dark.TFrame')
        status_frame.pack(fill='both', expand=True)

        ttk.Label(
            status_frame,
            text="Status",
            style='Heading.TLabel',
            font=self.fonts['heading']
        ).pack(anchor='w', pady=(0, 5))

        # Listbox with scrollbar
        list_frame = ttk.Frame(status_frame, style='Dark.TFrame')
        list_frame.pack(fill='both', expand=True)

        scrollbar = ttk.Scrollbar(list_frame, style='Dark.Vertical.TScrollbar')
        scrollbar.pack(side='right', fill='y')

        self.status_listbox = tk.Listbox(
            list_frame,
            bg=self.colors['bg_surface'],
            fg=self.colors['text_primary'],
            font=self.fonts['mono'],
            selectbackground=self.colors['button_bg'],
            selectforeground=self.colors['button_fg'],
            bd=1,
            relief='solid',
            highlightbackground=self.colors['border'],
            highlightcolor=self.colors['accent'],
            highlightthickness=1,
            yscrollcommand=scrollbar.set
        )
        self.status_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.status_listbox.yview)

    def _browse_source(self) -> None:
        """Browse for source folder"""
        folder = filedialog.askdirectory(
            title="Select Source Folder",
            initialdir=self.source_var.get() or str(Path.home())
        )
        if folder:
            self.source_var.set(folder)

    def _browse_destination(self) -> None:
        """Browse for destination folder"""
        folder = filedialog.askdirectory(
            title="Select Destination Folder",
            initialdir=self.dest_var.get() or str(Path.home())
        )
        if folder:
            self.dest_var.set(folder)

    def _start_sort(self) -> None:
        """Start the sort operation"""
        # Validate inputs
        source_folder = self.source_var.get().strip()
        dest_folder = self.dest_var.get().strip()

        if not source_folder:
            messagebox.showerror("Error", "Please select a source folder")
            return

        if not dest_folder:
            messagebox.showerror("Error", "Please select a destination folder")
            return

        if source_folder == dest_folder:
            messagebox.showerror("Error", "Source and destination folders cannot be the same")
            return

        # Prepare UI
        self._is_sorting = True
        self._cancel_requested = False
        self.sort_button.config(state='disabled')
        self.cancel_button.config(state='normal')
        self.progress_bar['value'] = 0
        self.progress_label.config(text="Preparing...")

        # Gather options
        sort_options = {
            'source_folder': source_folder,
            'dest_folder': dest_folder,
            'recursive': self.recursive_var.get(),
            'copy_mode': self.copy_mode_var.get()
        }

        # Save config when starting sort
        self.config.set("default_source_folder", source_folder)
        self.config.set("default_destination_folder", dest_folder)
        self.config.set("recursive_search", sort_options['recursive'])
        self.config.set("copy_mode", sort_options['copy_mode'])
        self.config.save()

        # Start worker thread
        self._sort_thread = threading.Thread(
            target=self._sort_worker,
            args=(sort_options,),
            daemon=True
        )
        self._sort_thread.start()

        # Start polling for updates
        self._poll_progress_queue()

    def _sort_worker(self, options: dict) -> None:
        """Worker thread for sorting"""
        try:
            self._queue_message('status', "Starting sort operation...")

            sorter = ImagePeopleSorter(
                status_callback=lambda msg: self._queue_message('status', msg),
                progress_callback=lambda cur, tot, fname, fprog: self._queue_message(
                    'progress', {'current': cur, 'total': tot, 'filename': fname, 'file_progress': fprog}
                ),
                cancel_check=lambda: self._cancel_requested,
                copy_mode=options['copy_mode']
            )

            results, people_count, no_people_count = sorter.sort_images(
                options['source_folder'],
                options['dest_folder'],
                options['recursive']
            )

            if self._cancel_requested:
                self._queue_message('cancelled', None)
                return

            error_count = sum(1 for r in results if not r.success)

            self._queue_message('complete', {
                'people_count': people_count,
                'no_people_count': no_people_count,
                'error_count': error_count,
                'options': options
            })

        except ValueError as e:
            self._queue_message('error', {'type': 'validation', 'message': str(e)})
        except Exception as e:
            self._queue_message('error', {'type': 'unexpected', 'message': str(e)})

    def _queue_message(self, msg_type: str, data) -> None:
        """Add message to queue (thread-safe)"""
        self._progress_queue.put((msg_type, data))

    def _poll_progress_queue(self) -> None:
        """Poll progress queue and update UI"""
        try:
            while True:
                try:
                    msg_type, data = self._progress_queue.get_nowait()

                    if msg_type == 'status':
                        self.status_listbox.insert(tk.END, data)
                        self.status_listbox.see(tk.END)

                    elif msg_type == 'progress':
                        total = data['total']
                        current = data['current']
                        # Progress is now 0-100 directly from the detector
                        self.progress_bar['value'] = current
                        self.progress_bar.update_idletasks()
                        self.progress_label.config(
                            text=f"{current}%: {data['filename']}"
                        )

                    elif msg_type == 'complete':
                        self._on_sort_complete(data)
                        return

                    elif msg_type == 'cancelled':
                        self._on_sort_cancelled()
                        return

                    elif msg_type == 'error':
                        self._on_sort_error(data)
                        return

                except queue.Empty:
                    break

        except Exception as e:
            print(f"Error in progress polling: {e}")

        if self._is_sorting:
            self.root.after(50, self._poll_progress_queue)

    def _on_sort_complete(self, data: dict) -> None:
        """Handle sort completion"""
        self._is_sorting = False
        self.sort_button.config(state='normal')
        self.cancel_button.config(state='disabled')

        people_count = data['people_count']
        no_people_count = data['no_people_count']
        error_count = data['error_count']
        options = data['options']

        # Save config
        self.config.set("default_source_folder", options['source_folder'])
        self.config.set("default_destination_folder", options['dest_folder'])
        self.config.set("recursive_search", options['recursive'])
        self.config.set("copy_mode", options['copy_mode'])
        self.config.save()

        # Show result
        self.progress_label.config(text="Complete!")
        self.progress_bar['value'] = 100

        action = "copied" if options['copy_mode'] else "moved"
        if error_count == 0:
            messagebox.showinfo(
                "Success",
                f"Successfully sorted images!\n\n"
                f"People: {people_count} images {action}\n"
                f"No People: {no_people_count} images {action}"
            )
        else:
            messagebox.showwarning(
                "Completed with errors",
                f"Sorted images with {error_count} errors.\n\n"
                f"People: {people_count} images {action}\n"
                f"No People: {no_people_count} images {action}\n\n"
                f"Check status for details."
            )

    def _on_sort_cancelled(self) -> None:
        """Handle sort cancellation"""
        self._is_sorting = False
        self.sort_button.config(state='normal')
        self.cancel_button.config(state='disabled')
        self.progress_label.config(text="Cancelled")
        self.status_listbox.insert(tk.END, "Operation cancelled by user")
        self.status_listbox.see(tk.END)
        messagebox.showinfo("Cancelled", "Sort operation was cancelled")

    def _on_sort_error(self, data: dict) -> None:
        """Handle sort error"""
        self._is_sorting = False
        self.sort_button.config(state='normal')
        self.cancel_button.config(state='disabled')
        self.progress_label.config(text="Error")

        error_type = data['type']
        message = data['message']

        if error_type == 'validation':
            messagebox.showerror("Validation Error", message)
        else:
            messagebox.showerror("Error", f"An unexpected error occurred: {message}")

    def _cancel_sort(self) -> None:
        """Request cancellation and kill worker processes"""
        if self._is_sorting:
            self._cancel_requested = True
            self.cancel_button.config(state='disabled')
            self.progress_label.config(text="Cancelling...")
            self.status_listbox.insert(tk.END, "Cancellation requested, killing workers...")
            self.status_listbox.see(tk.END)
            # Force kill child processes immediately
            self._kill_child_processes()

    def _kill_child_processes(self) -> None:
        """Force kill all child processes"""
        try:
            import psutil
            current_process = psutil.Process(os.getpid())
            children = current_process.children(recursive=True)

            # First try graceful termination
            for child in children:
                try:
                    child.terminate()
                except Exception:
                    pass

            # Wait briefly
            psutil.wait_procs(children, timeout=1)

            # Force kill any remaining
            for child in current_process.children(recursive=True):
                try:
                    child.kill()
                except Exception:
                    pass
        except ImportError:
            # psutil not available, try os-level kill on Windows
            try:
                import subprocess
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(os.getpid())],
                             capture_output=True, timeout=2)
            except Exception:
                pass

    def _on_close(self) -> None:
        """Handle window close - clean up resources"""
        if self._is_sorting:
            self._cancel_requested = True

        self._kill_child_processes()
        self.root.destroy()
