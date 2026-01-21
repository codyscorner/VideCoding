"""Main window UI for File Copy Manager application"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Optional, Callable
import threading
import queue

from config import ConfigManager
from file_operations import FileCopier
from ui.styles import ThemeManager
from folder_organization import FolderStructure, FolderOrganizer


class MainWindow:
    """Main application window"""

    def __init__(self, root: tk.Tk, config_manager: ConfigManager, version: str):
        """
        Initialize main window

        Args:
            root: Tkinter root window
            config_manager: Configuration manager instance
            version: Application version string
        """
        self.root = root
        self.config = config_manager
        self.version = version

        # Set up window
        self.root.title(f"File Copy Manager (V-{self.version})")
        self.root.geometry("1200x900")
        self.root.configure(bg='#1a1a1a')

        # Set minimum window size (75% of starting dimensions)
        self.root.minsize(900, 675)

        # Initialize theme
        self.style = ttk.Style()
        self.theme = ThemeManager(self.style, 'yellow_black')
        self.colors = self.theme.get_all_colors()
        self.fonts = self.theme.get_all_fonts()

        # UI Variables
        self.source_var = tk.StringVar(value=self.config.get("default_source_folder", ""))
        self.dest_var = tk.StringVar(value=self.config.get("default_destination_folder", ""))
        self.ext_var = tk.StringVar(value=self.config.get("last_extension", ""))

        # Copy options
        self.preserve_structure_var = tk.BooleanVar(value=self.config.get("preserve_structure", True))
        self.folder_structure_var = tk.StringVar(value=self.config.get("folder_structure", "flat"))
        self.number_duplicates_var = tk.BooleanVar(value=self.config.get("number_duplicates", True))
        self.recursive_search_var = tk.BooleanVar(value=self.config.get("recursive_search", True))

        # Filter options
        self.enable_size_filter_var = tk.BooleanVar(value=self.config.get("enable_size_filter", False))
        self.min_size_var = tk.StringVar(value=self.config.get("min_size", "0"))
        self.max_size_var = tk.StringVar(value=self.config.get("max_size", ""))
        self.size_unit_var = tk.StringVar(value=self.config.get("size_unit", "MB"))

        self.enable_date_filter_var = tk.BooleanVar(value=self.config.get("enable_date_filter", False))
        self.days_old_var = tk.StringVar(value=self.config.get("days_old", "30"))

        # Threading state
        self._copy_thread: Optional[threading.Thread] = None
        self._progress_queue: queue.Queue = queue.Queue()
        self._cancel_requested: bool = False
        self._is_copying: bool = False

        # Build UI
        self._setup_ui()

        # Set up variable traces
        self.preserve_structure_var.trace_add('write', self._on_preserve_structure_changed)
        self.folder_structure_var.trace_add('write', self._update_folder_example)

    def _setup_ui(self) -> None:
        """Set up the main UI components"""
        # Create main container with scrollbar
        main_container = ttk.Frame(self.root, style='Dark.TFrame')
        main_container.pack(fill='both', expand=True)

        # Canvas for scrolling
        canvas = tk.Canvas(main_container, bg=self.colors['background'], highlightthickness=0)
        scrollbar = tk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style='Dark.TFrame')

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        main_frame = ttk.Frame(scrollable_frame, style='Dark.TFrame')
        main_frame.pack(fill='both', expand=True, padx=15, pady=10)

        # Title
        self._create_title(main_frame)

        # Source and Destination folders
        self._create_folder_inputs(main_frame)

        # Extension
        self._create_extension_input(main_frame)

        # Copy options
        self._create_copy_options(main_frame)

        # Filter options
        self._create_filter_options(main_frame)

        # Folder organization
        self._create_folder_organization_section(main_frame)

        # Buttons
        self._create_buttons(main_frame)

        # Progress bars
        self._create_progress_section(main_frame)

        # Status listbox
        self._create_status_listbox(main_frame)

    def _create_title(self, parent: ttk.Frame) -> None:
        """Create title label"""
        title_frame = ttk.Frame(parent, style='Dark.TFrame')
        title_frame.pack(fill='x', pady=(0, 15))

        ttk.Label(
            title_frame,
            text="File Copy Manager",
            style='Dark.TLabel',
            font=self.fonts['title']
        ).pack(anchor='center')

        ttk.Label(
            title_frame,
            text="Copy files with automatic numbering and folder organization",
            style='Dark.TLabel',
            font=self.fonts['italic']
        ).pack(anchor='center')

    def _create_folder_inputs(self, parent: ttk.Frame) -> None:
        """Create source and destination folder inputs"""
        # Source Folder
        self._create_folder_input(
            parent,
            "Source Folder:",
            self.source_var,
            self._browse_source
        )

        # Destination Folder
        self._create_folder_input(
            parent,
            "Destination Folder:",
            self.dest_var,
            self._browse_destination
        )

    def _create_extension_input(self, parent: ttk.Frame) -> None:
        """Create extension input with preset dropdown"""
        # Define file type presets
        self.file_type_presets = {
            "-- Select Preset --": "",
            "Images": "*.jpg, *.jpeg, *.png, *.gif, *.bmp, *.tiff, *.tif, *.webp, *.svg, *.ico, *.raw, *.heic, *.heif",
            "Videos": "*.mp4, *.avi, *.mkv, *.mov, *.wmv, *.flv, *.webm, *.m4v, *.mpeg, *.mpg, *.3gp, *.ts",
            "Audio": "*.mp3, *.wav, *.flac, *.aac, *.ogg, *.wma, *.m4a, *.opus, *.aiff, *.alac",
            "Documents": "*.pdf, *.doc, *.docx, *.xls, *.xlsx, *.ppt, *.pptx, *.txt, *.rtf, *.odt, *.ods, *.odp",
            "Archives": "*.zip, *.rar, *.7z, *.tar, *.gz, *.bz2, *.xz, *.iso, *.cab",
            "Code": "*.py, *.js, *.ts, *.html, *.css, *.java, *.cpp, *.c, *.h, *.cs, *.php, *.rb, *.go, *.rs, *.swift",
            "Data": "*.json, *.xml, *.csv, *.yaml, *.yml, *.sql, *.db, *.sqlite, *.mdb",
        }

        frame = ttk.Frame(parent, style='Dark.TFrame')
        frame.pack(fill='x', pady=(0, 5))

        # Label row with preset dropdown
        label_frame = ttk.Frame(frame, style='Dark.TFrame')
        label_frame.pack(fill='x')

        ttk.Label(label_frame, text="File Mask:", style='Dark.TLabel').pack(side='left')

        # Preset dropdown
        ttk.Label(label_frame, text="Presets:", style='Dark.TLabel').pack(side='left', padx=(20, 5))
        self.preset_var = tk.StringVar(value="-- Select Preset --")
        preset_combo = ttk.Combobox(
            label_frame,
            textvariable=self.preset_var,
            values=list(self.file_type_presets.keys()),
            state="readonly",
            width=20
        )
        preset_combo.pack(side='left')
        preset_combo.bind('<<ComboboxSelected>>', self._on_preset_selected)

        entry = tk.Entry(
            frame,
            textvariable=self.ext_var,
            width=150,
            bg=self.colors['input_bg'],
            fg=self.colors['input_fg'],
            insertbackground=self.colors['insert_cursor'],
            bd=1,
            relief='solid'
        )
        entry.pack(fill='x', pady=(2, 0))

        ttk.Label(
            frame,
            text="Example: *.jpg, *.png  or  oct*.*  or  .pdf",
            style='Dark.TLabel',
            font=self.fonts['italic']
        ).pack(anchor='w', pady=(2, 0))

    def _on_preset_selected(self, event=None) -> None:
        """Handle preset selection from dropdown"""
        preset_name = self.preset_var.get()
        if preset_name in self.file_type_presets:
            preset_value = self.file_type_presets[preset_name]
            if preset_value:  # Don't clear if selecting the placeholder
                self.ext_var.set(preset_value)

    def _create_copy_options(self, parent: ttk.Frame) -> None:
        """Create copy options section"""
        section_frame = ttk.Frame(parent, style='Dark.TFrame')
        section_frame.pack(fill='x', pady=(5, 5))

        ttk.Label(
            section_frame,
            text="Copy Options",
            style='Dark.TLabel',
            font=self.fonts['bold']
        ).pack(anchor='w', pady=(0, 5))

        # Recursive search checkbox
        recursive_check = tk.Checkbutton(
            section_frame,
            text="Search subfolders recursively (include all files from nested folders)",
            variable=self.recursive_search_var,
            bg=self.colors['background'],
            fg=self.colors['foreground'],
            selectcolor=self.colors['input_bg'],
            activebackground=self.colors['background'],
            activeforeground=self.colors['foreground'],
            font=self.fonts['default']
        )
        recursive_check.pack(anchor='w', pady=(0, 5))

        # Preserve structure checkbox
        preserve_check = tk.Checkbutton(
            section_frame,
            text="Preserve original folder structure",
            variable=self.preserve_structure_var,
            bg=self.colors['background'],
            fg=self.colors['foreground'],
            selectcolor=self.colors['input_bg'],
            activebackground=self.colors['background'],
            activeforeground=self.colors['foreground'],
            font=self.fonts['default']
        )
        preserve_check.pack(anchor='w', pady=(0, 5))

        # Number duplicates checkbox
        number_check = tk.Checkbutton(
            section_frame,
            text="Number duplicate files (e.g., file_001.jpg, file_002.jpg)",
            variable=self.number_duplicates_var,
            bg=self.colors['background'],
            fg=self.colors['foreground'],
            selectcolor=self.colors['input_bg'],
            activebackground=self.colors['background'],
            activeforeground=self.colors['foreground'],
            font=self.fonts['default']
        )
        number_check.pack(anchor='w')

    def _create_filter_options(self, parent: ttk.Frame) -> None:
        """Create filter options section"""
        section_frame = ttk.Frame(parent, style='Dark.TFrame')
        section_frame.pack(fill='x', pady=(5, 5))

        ttk.Label(
            section_frame,
            text="File Filters",
            style='Dark.TLabel',
            font=self.fonts['bold']
        ).pack(anchor='w', pady=(0, 5))

        # Size filter
        size_frame = ttk.Frame(section_frame, style='Dark.TFrame')
        size_frame.pack(fill='x', pady=(0, 5))

        size_check = tk.Checkbutton(
            size_frame,
            text="Filter by file size:",
            variable=self.enable_size_filter_var,
            bg=self.colors['background'],
            fg=self.colors['foreground'],
            selectcolor=self.colors['input_bg'],
            activebackground=self.colors['background'],
            activeforeground=self.colors['foreground'],
            font=self.fonts['default'],
            command=self._on_size_filter_changed
        )
        size_check.pack(anchor='w')

        # Size inputs frame
        self.size_inputs_frame = ttk.Frame(size_frame, style='Dark.TFrame')
        self.size_inputs_frame.pack(fill='x', padx=(20, 0), pady=(5, 0))

        # Min size
        min_frame = ttk.Frame(self.size_inputs_frame, style='Dark.TFrame')
        min_frame.pack(side='left', padx=(0, 10))

        ttk.Label(min_frame, text="Min:", style='Dark.TLabel').pack(side='left', padx=(0, 5))
        tk.Entry(
            min_frame,
            textvariable=self.min_size_var,
            width=10,
            bg=self.colors['input_bg'],
            fg=self.colors['input_fg'],
            insertbackground=self.colors['insert_cursor'],
            bd=1,
            relief='solid'
        ).pack(side='left')

        # Max size
        max_frame = ttk.Frame(self.size_inputs_frame, style='Dark.TFrame')
        max_frame.pack(side='left', padx=(0, 10))

        ttk.Label(max_frame, text="Max:", style='Dark.TLabel').pack(side='left', padx=(0, 5))
        tk.Entry(
            max_frame,
            textvariable=self.max_size_var,
            width=10,
            bg=self.colors['input_bg'],
            fg=self.colors['input_fg'],
            insertbackground=self.colors['insert_cursor'],
            bd=1,
            relief='solid'
        ).pack(side='left')

        # Unit
        unit_frame = ttk.Frame(self.size_inputs_frame, style='Dark.TFrame')
        unit_frame.pack(side='left')

        ttk.Label(unit_frame, text="Unit:", style='Dark.TLabel').pack(side='left', padx=(0, 5))
        ttk.Combobox(
            unit_frame,
            textvariable=self.size_unit_var,
            values=["B", "KB", "MB", "GB"],
            state="readonly",
            width=5
        ).pack(side='left')

        # Date filter
        date_frame = ttk.Frame(section_frame, style='Dark.TFrame')
        date_frame.pack(fill='x')

        date_check = tk.Checkbutton(
            date_frame,
            text="Filter by file age:",
            variable=self.enable_date_filter_var,
            bg=self.colors['background'],
            fg=self.colors['foreground'],
            selectcolor=self.colors['input_bg'],
            activebackground=self.colors['background'],
            activeforeground=self.colors['foreground'],
            font=self.fonts['default'],
            command=self._on_date_filter_changed
        )
        date_check.pack(anchor='w')

        # Date inputs frame
        self.date_inputs_frame = ttk.Frame(date_frame, style='Dark.TFrame')
        self.date_inputs_frame.pack(fill='x', padx=(20, 0), pady=(5, 0))

        days_frame = ttk.Frame(self.date_inputs_frame, style='Dark.TFrame')
        days_frame.pack(side='left')

        ttk.Label(days_frame, text="Modified within last:", style='Dark.TLabel').pack(side='left', padx=(0, 5))
        tk.Entry(
            days_frame,
            textvariable=self.days_old_var,
            width=10,
            bg=self.colors['input_bg'],
            fg=self.colors['input_fg'],
            insertbackground=self.colors['insert_cursor'],
            bd=1,
            relief='solid'
        ).pack(side='left', padx=(0, 5))
        ttk.Label(days_frame, text="days", style='Dark.TLabel').pack(side='left')

        # Initialize visibility
        self._on_size_filter_changed()
        self._on_date_filter_changed()

    def _create_folder_organization_section(self, parent: ttk.Frame) -> None:
        """Create folder organization section"""
        self.folder_org_frame = ttk.Frame(parent, style='Dark.TFrame')
        self.folder_org_frame.pack(fill='x', pady=(5, 5))

        # Title
        ttk.Label(
            self.folder_org_frame,
            text="Folder Organization (when not preserving structure)",
            style='Dark.TLabel',
            font=self.fonts['bold']
        ).pack(anchor='w', pady=(0, 5))

        # Folder structure
        folder_frame = ttk.Frame(self.folder_org_frame, style='Dark.TFrame')
        folder_frame.pack(fill='x')

        ttk.Label(folder_frame, text="Organize into:", style='Dark.TLabel').pack(anchor='w')
        folder_combo = ttk.Combobox(
            folder_frame,
            textvariable=self.folder_structure_var,
            values=["flat", "year", "year_month", "year_month_day", "date", "month"],
            state="readonly",
            width=30
        )
        folder_combo.pack(fill='x', pady=(5, 0))

        # Example label
        self.folder_example_label = ttk.Label(
            folder_frame,
            text="",
            style='Dark.TLabel',
            font=self.fonts['italic']
        )
        self.folder_example_label.pack(anchor='w', pady=(2, 0))
        self._update_folder_example()

        # Update visibility based on preserve structure
        self._on_preserve_structure_changed()

    def _create_folder_input(
        self,
        parent: ttk.Frame,
        label: str,
        variable: tk.StringVar,
        browse_command: Callable
    ) -> None:
        """Create a folder input field with browse button"""
        frame = ttk.Frame(parent, style='Dark.TFrame')
        frame.pack(fill='x', pady=(0, 5))

        ttk.Label(frame, text=label, style='Dark.TLabel').pack(anchor='w')

        input_frame = tk.Frame(frame, bg=self.colors['background'])
        input_frame.pack(fill='x', pady=(2, 0))

        entry = tk.Entry(
            input_frame,
            textvariable=variable,
            width=120,
            bg=self.colors['input_bg'],
            fg=self.colors['input_fg'],
            insertbackground=self.colors['insert_cursor'],
            bd=1,
            relief='solid'
        )
        entry.pack(side='left', fill='x', expand=True, padx=(0, 5))

        browse_btn = tk.Button(
            input_frame,
            text="...",
            command=browse_command,
            bg=self.colors['button_bg'],
            fg=self.colors['button_fg'],
            relief='raised',
            bd=2,
            width=3,
            height=1,
            font=self.fonts['button'],
            activebackground=self.colors['button_active'],
            activeforeground=self.colors['button_fg']
        )
        browse_btn.pack(side='right')

    def _create_buttons(self, parent: ttk.Frame) -> None:
        """Create action buttons"""
        button_frame = ttk.Frame(parent, style='Dark.TFrame')
        button_frame.pack(fill='x', pady=(5, 10))

        # Copy Files button
        self.copy_button = tk.Button(
            button_frame,
            text="Copy Files",
            command=self._start_copy,
            bg=self.colors['button_bg'],
            fg=self.colors['button_fg'],
            font=self.fonts['button'],
            relief='raised',
            bd=2,
            padx=20,
            pady=10
        )
        self.copy_button.pack(side='left', padx=(0, 10))

        # Cancel button (initially disabled)
        self.cancel_button = tk.Button(
            button_frame,
            text="Cancel",
            command=self._cancel_copy,
            bg='#8B0000',  # Dark red
            fg=self.colors['button_fg'],
            font=self.fonts['button'],
            relief='raised',
            bd=2,
            padx=20,
            pady=10,
            state='disabled'
        )
        self.cancel_button.pack(side='left', padx=(0, 10))

    def _create_progress_section(self, parent: ttk.Frame) -> None:
        """Create progress bars section"""
        progress_frame = ttk.Frame(parent, style='Dark.TFrame')
        progress_frame.pack(fill='x', pady=(5, 10))

        # Overall progress
        ttk.Label(
            progress_frame,
            text="Overall Progress:",
            style='Dark.TLabel'
        ).pack(anchor='w')

        self.overall_progress = ttk.Progressbar(
            progress_frame,
            orient='horizontal',
            mode='determinate',
            length=100,
            style='Yellow.Horizontal.TProgressbar'
        )
        self.overall_progress.pack(fill='x', pady=(5, 10))

        # Current file progress
        ttk.Label(
            progress_frame,
            text="Current File:",
            style='Dark.TLabel'
        ).pack(anchor='w')

        self.file_progress = ttk.Progressbar(
            progress_frame,
            orient='horizontal',
            mode='determinate',
            length=100,
            style='Yellow.Horizontal.TProgressbar'
        )
        self.file_progress.pack(fill='x', pady=(5, 0))

        # Progress label
        self.progress_label = ttk.Label(
            progress_frame,
            text="Ready",
            style='Dark.TLabel',
            font=self.fonts['italic']
        )
        self.progress_label.pack(anchor='w', pady=(2, 0))

    def _create_status_listbox(self, parent: ttk.Frame) -> None:
        """Create status listbox with scrollbar"""
        status_frame = ttk.Frame(parent, style='Dark.TFrame')
        status_frame.pack(fill='both', expand=True)

        ttk.Label(status_frame, text="Status:", style='Dark.TLabel').pack(anchor='w')

        listbox_frame = ttk.Frame(status_frame, style='Dark.TFrame')
        listbox_frame.pack(fill='both', expand=True, pady=(5, 0))

        self.status_listbox = tk.Listbox(
            listbox_frame,
            bg=self.colors['input_bg'],
            fg=self.colors['input_fg'],
            selectbackground=self.colors['select_bg'],
            selectforeground=self.colors['select_fg'],
            bd=1,
            relief='solid',
            height=10
        )
        self.status_listbox.pack(side='left', fill='both', expand=True)

        scrollbar = tk.Scrollbar(
            listbox_frame,
            bg=self.colors['scrollbar_bg'],
            troughcolor=self.colors['scrollbar_trough']
        )
        scrollbar.pack(side='right', fill='y')

        self.status_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.status_listbox.yview)

        # Initial status message
        self.add_status("Ready to copy files...")

    def _browse_source(self) -> None:
        """Handle source folder browse button"""
        initial_dir = self.source_var.get() or self.config.get("default_source_folder", "")
        folder = filedialog.askdirectory(
            title="Select Source Folder",
            initialdir=initial_dir if initial_dir else None
        )
        if folder:
            self.source_var.set(folder)
            self.config.set("default_source_folder", folder)
            self.config.save()
            self.add_status(f"Source folder selected: {folder}")

    def _browse_destination(self) -> None:
        """Handle destination folder browse button"""
        initial_dir = self.dest_var.get() or self.config.get("default_destination_folder", "")
        folder = filedialog.askdirectory(
            title="Select Destination Folder",
            initialdir=initial_dir if initial_dir else None
        )
        if folder:
            self.dest_var.set(folder)
            self.config.set("default_destination_folder", folder)
            self.config.save()
            self.add_status(f"Destination folder selected: {folder}")

    def _on_preserve_structure_changed(self, *args) -> None:
        """Handle preserve structure checkbox change"""
        if self.preserve_structure_var.get():
            # Hide folder organization options
            self.folder_org_frame.pack_forget()
        else:
            # Show folder organization options
            self.folder_org_frame.pack(fill='x', pady=(5, 5))

    def _on_size_filter_changed(self) -> None:
        """Handle size filter checkbox change"""
        if self.enable_size_filter_var.get():
            self.size_inputs_frame.pack(fill='x', padx=(20, 0), pady=(5, 0))
        else:
            self.size_inputs_frame.pack_forget()

    def _on_date_filter_changed(self) -> None:
        """Handle date filter checkbox change"""
        if self.enable_date_filter_var.get():
            self.date_inputs_frame.pack(fill='x', padx=(20, 0), pady=(5, 0))
        else:
            self.date_inputs_frame.pack_forget()

    def _update_folder_example(self, *args) -> None:
        """Update the folder organization example"""
        try:
            structure = FolderStructure(self.folder_structure_var.get())
            example = FolderOrganizer.get_folder_structure_example(structure)
            self.folder_example_label.config(text=f"Example: {example}")
        except Exception:
            self.folder_example_label.config(text="")

    def _start_copy(self) -> None:
        """Start the copy operation in a background thread"""
        # Get values
        source_folder = self.source_var.get().strip()
        dest_folder = self.dest_var.get().strip()
        extension = self.ext_var.get().strip()

        # Validate inputs
        if not source_folder:
            messagebox.showerror("Error", "Please select a source folder")
            return

        if not dest_folder:
            messagebox.showerror("Error", "Please select a destination folder")
            return

        if not extension:
            messagebox.showerror("Error", "Please enter a file extension")
            return

        # Check if source and dest are the same
        if source_folder == dest_folder:
            messagebox.showerror("Error", "Source and destination folders cannot be the same")
            return

        # Get filter options (validate before starting thread)
        min_size_bytes = None
        max_size_bytes = None
        max_days_old = None

        if self.enable_size_filter_var.get():
            try:
                unit_multiplier = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}
                multiplier = unit_multiplier.get(self.size_unit_var.get(), 1024**2)

                min_val = self.min_size_var.get().strip()
                if min_val:
                    min_size_bytes = float(min_val) * multiplier

                max_val = self.max_size_var.get().strip()
                if max_val:
                    max_size_bytes = float(max_val) * multiplier
            except ValueError:
                messagebox.showerror("Error", "Invalid size filter values")
                return

        if self.enable_date_filter_var.get():
            try:
                days_val = self.days_old_var.get().strip()
                if days_val:
                    max_days_old = int(days_val)
            except ValueError:
                messagebox.showerror("Error", "Invalid date filter value")
                return

        # Prepare UI for copying
        self._is_copying = True
        self._cancel_requested = False
        self.copy_button.config(state='disabled')
        self.cancel_button.config(state='normal')
        self.overall_progress['value'] = 0
        self.file_progress['value'] = 0
        self.progress_label.config(text="Preparing...")

        # Gather all options for the thread
        copy_options = {
            'source_folder': source_folder,
            'dest_folder': dest_folder,
            'extension': extension,
            'preserve_structure': self.preserve_structure_var.get(),
            'number_duplicates': self.number_duplicates_var.get(),
            'recursive_search': self.recursive_search_var.get(),
            'folder_structure': self.folder_structure_var.get(),
            'min_size_bytes': min_size_bytes,
            'max_size_bytes': max_size_bytes,
            'max_days_old': max_days_old
        }

        # Start the worker thread
        self._copy_thread = threading.Thread(
            target=self._copy_files_worker,
            args=(copy_options,),
            daemon=True
        )
        self._copy_thread.start()

        # Start polling the queue for updates
        self._poll_progress_queue()

    def _copy_files_worker(self, options: dict) -> None:
        """Worker thread that performs the actual file copying"""
        try:
            self._queue_message('status', "Starting copy operation...")

            folder_structure = FolderStructure(options['folder_structure'])

            # Create file copier with thread-safe callbacks
            file_copier = FileCopier(
                status_callback=lambda msg: self._queue_message('status', msg),
                folder_structure=folder_structure,
                number_duplicates=options['number_duplicates'],
                progress_callback=lambda cur, tot, fname, fprog: self._queue_message(
                    'progress', {'current': cur, 'total': tot, 'filename': fname, 'file_progress': fprog}
                ),
                cancel_check=lambda: self._cancel_requested
            )

            # Perform operation
            results = file_copier.copy_files(
                options['source_folder'],
                options['dest_folder'],
                options['extension'],
                options['preserve_structure'],
                options['recursive_search'],
                min_size_bytes=options['min_size_bytes'],
                max_size_bytes=options['max_size_bytes'],
                max_days_old=options['max_days_old']
            )

            # Check if cancelled
            if self._cancel_requested:
                self._queue_message('cancelled', None)
                return

            # Count results
            success_count = sum(1 for r in results if r.success)
            error_count = sum(1 for r in results if not r.success)

            # Queue completion with results
            self._queue_message('complete', {
                'success_count': success_count,
                'error_count': error_count,
                'options': options
            })

        except ValueError as e:
            self._queue_message('error', {'type': 'validation', 'message': str(e)})
        except OSError as e:
            self._queue_message('error', {'type': 'filesystem', 'message': str(e)})
        except Exception as e:
            self._queue_message('error', {'type': 'unexpected', 'message': str(e)})

    def _queue_message(self, msg_type: str, data) -> None:
        """Add a message to the progress queue (thread-safe)"""
        self._progress_queue.put((msg_type, data))

    def _poll_progress_queue(self) -> None:
        """Poll the progress queue and update UI (runs on main thread)"""
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
                        if total > 0:
                            overall_percent = (current / total) * 100
                            self.overall_progress['value'] = overall_percent
                        self.file_progress['value'] = data['file_progress']
                        self.progress_label.config(
                            text=f"Processing {current}/{total}: {data['filename']}"
                        )

                    elif msg_type == 'complete':
                        self._on_copy_complete(data)
                        return  # Stop polling

                    elif msg_type == 'cancelled':
                        self._on_copy_cancelled()
                        return  # Stop polling

                    elif msg_type == 'error':
                        self._on_copy_error(data)
                        return  # Stop polling

                except queue.Empty:
                    break

        except Exception as e:
            # Safety catch for any UI update errors
            print(f"Error in progress queue polling: {e}")

        # Continue polling if still copying
        if self._is_copying:
            self.root.after(50, self._poll_progress_queue)

    def _on_copy_complete(self, data: dict) -> None:
        """Handle copy operation completion (runs on main thread)"""
        self._is_copying = False
        self.copy_button.config(state='normal')
        self.cancel_button.config(state='disabled')

        success_count = data['success_count']
        error_count = data['error_count']
        options = data['options']

        # Save configuration
        self.config.set("last_extension", options['extension'])
        self.config.set("default_source_folder", options['source_folder'])
        self.config.set("default_destination_folder", options['dest_folder'])
        self.config.set("preserve_structure", options['preserve_structure'])
        self.config.set("folder_structure", options['folder_structure'])
        self.config.set("number_duplicates", options['number_duplicates'])
        self.config.set("recursive_search", options['recursive_search'])
        self.config.set("enable_size_filter", self.enable_size_filter_var.get())
        self.config.set("min_size", self.min_size_var.get())
        self.config.set("max_size", self.max_size_var.get())
        self.config.set("size_unit", self.size_unit_var.get())
        self.config.set("enable_date_filter", self.enable_date_filter_var.get())
        self.config.set("days_old", self.days_old_var.get())
        self.config.save()

        # Show result
        self.progress_label.config(text="Complete!")
        if error_count == 0 and success_count > 0:
            messagebox.showinfo("Success", f"Successfully copied {success_count} files")
        elif success_count > 0:
            messagebox.showwarning(
                "Completed with errors",
                f"Copied {success_count} files with {error_count} errors. Check status for details."
            )
        elif error_count == 0:
            messagebox.showinfo("No Files", "No files were found to process")

    def _on_copy_cancelled(self) -> None:
        """Handle copy operation cancellation (runs on main thread)"""
        self._is_copying = False
        self.copy_button.config(state='normal')
        self.cancel_button.config(state='disabled')
        self.progress_label.config(text="Cancelled")
        self.status_listbox.insert(tk.END, "Operation cancelled by user")
        self.status_listbox.see(tk.END)
        messagebox.showinfo("Cancelled", "Copy operation was cancelled")

    def _on_copy_error(self, data: dict) -> None:
        """Handle copy operation error (runs on main thread)"""
        self._is_copying = False
        self.copy_button.config(state='normal')
        self.cancel_button.config(state='disabled')
        self.progress_label.config(text="Error")

        error_type = data['type']
        message = data['message']

        if error_type == 'validation':
            messagebox.showerror("Validation Error", message)
        elif error_type == 'filesystem':
            messagebox.showerror("File System Error", message)
        else:
            messagebox.showerror("Error", f"An unexpected error occurred: {message}")

    def _cancel_copy(self) -> None:
        """Request cancellation of the copy operation"""
        if self._is_copying:
            self._cancel_requested = True
            self.cancel_button.config(state='disabled')
            self.progress_label.config(text="Cancelling...")
            self.status_listbox.insert(tk.END, "Cancellation requested, please wait...")
            self.status_listbox.see(tk.END)

    def add_status(self, message: str) -> None:
        """Add a status message to the listbox"""
        self.status_listbox.insert(tk.END, message)
        self.status_listbox.see(tk.END)
        self.root.update_idletasks()

    def _update_progress(self, current: int, total: int, current_file: str, file_progress: int = 0) -> None:
        """Update progress bars and label"""
        # Update overall progress
        if total > 0:
            overall_percent = (current / total) * 100
            self.overall_progress['value'] = overall_percent

        # Update file progress
        self.file_progress['value'] = file_progress

        # Update label
        self.progress_label.config(text=f"Processing {current}/{total}: {current_file}")

        # Force UI update
        self.root.update_idletasks()
