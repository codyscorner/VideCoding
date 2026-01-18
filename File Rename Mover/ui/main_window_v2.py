"""Enhanced main window UI with advanced features for File Rename Mover application"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Optional, Callable

from config import ConfigManager
from file_operations import FileRenamer
from ui.styles import ThemeManager
from sorting import SortBy, SortOrder
from rename_patterns import PatternType, DateTimeFormat, PatternFactory
from folder_organization import FolderStructure, FolderOrganizer
from templates import TemplateManager


class MainWindowV2:
    """Enhanced main application window with advanced features"""

    def __init__(self, root: tk.Tk, config_manager: ConfigManager, version: str, template_manager: TemplateManager):
        """
        Initialize enhanced main window

        Args:
            root: Tkinter root window
            config_manager: Configuration manager instance
            version: Application version string
            template_manager: Template manager instance
        """
        self.root = root
        self.config = config_manager
        self.version = version
        self.template_manager = template_manager

        # Set up window
        self.root.title(f"File Rename Mover (V-{self.version})")
        self.root.geometry("1000x870")
        self.root.configure(bg='#1a1a1a')

        # Set minimum window size to prevent UI from breaking
        self.root.minsize(1000, 870)

        # Initialize theme
        self.style = ttk.Style()
        self.theme = ThemeManager(self.style, 'dark_red')
        self.colors = self.theme.get_all_colors()
        self.fonts = self.theme.get_all_fonts()

        # UI Variables - Basic
        self.source_var = tk.StringVar(value=self.config.get("default_source_folder", ""))
        self.dest_var = tk.StringVar(value=self.config.get("default_destination_folder", ""))
        self.ext_var = tk.StringVar(value=self.config.get("last_extension", ""))
        self.rename_var = tk.StringVar(value=self.config.get("last_rename_to", ""))

        # UI Variables - Sorting
        self.sort_by_var = tk.StringVar(value=self.config.get("sort_by", "name"))
        self.sort_order_var = tk.StringVar(value=self.config.get("sort_order", "asc"))

        # UI Variables - Pattern
        self.pattern_type_var = tk.StringVar(value=self.config.get("pattern_type", "numbering"))
        self.datetime_format_var = tk.StringVar(value=self.config.get("datetime_format", "YYYYMMDD"))
        self.include_counter_var = tk.BooleanVar(value=self.config.get("include_counter", True))
        self.custom_pattern_var = tk.StringVar(value=self.config.get("custom_pattern", "{counter}"))

        # UI Variables - Folder Organization
        self.folder_structure_var = tk.StringVar(value=self.config.get("folder_structure", "flat"))

        # UI Variables - Templates
        self.template_var = tk.StringVar(value="")

        # Build UI
        self._setup_ui()

        # Set up variable traces
        self.ext_var.trace_add('write', self._update_example)
        self.rename_var.trace_add('write', self._update_example)
        self.pattern_type_var.trace_add('write', self._update_example)
        self.datetime_format_var.trace_add('write', self._update_example)
        self.include_counter_var.trace_add('write', self._update_example)
        self.custom_pattern_var.trace_add('write', self._update_example)
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

        # Templates section (at the top for easy access)
        self._create_templates_section(main_frame)

        # Source and Destination folders
        self._create_folder_inputs(main_frame)

        # Extension and Base Name
        self._create_basic_inputs(main_frame)

        # Sorting options
        self._create_sorting_section(main_frame)

        # Pattern options
        self._create_pattern_section(main_frame)

        # Folder organization
        self._create_folder_organization_section(main_frame)

        # Buttons
        self._create_buttons(main_frame)

        # Status listbox
        self._create_status_listbox(main_frame)

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

    def _create_basic_inputs(self, parent: ttk.Frame) -> None:
        """Create extension and base name inputs"""
        # Extension
        self._create_text_input(parent, "Extension:", self.ext_var)

        # Base name
        rename_frame = ttk.Frame(parent, style='Dark.TFrame')
        rename_frame.pack(fill='x', pady=(0, 10))

        ttk.Label(
            rename_frame,
            text="Base Name:",
            style='Dark.TLabel'
        ).pack(anchor='w')

        self.rename_entry = tk.Entry(
            rename_frame,
            textvariable=self.rename_var,
            width=150,
            bg=self.colors['input_bg'],
            fg=self.colors['input_fg'],
            insertbackground=self.colors['insert_cursor'],
            bd=1,
            relief='solid'
        )
        self.rename_entry.pack(fill='x', pady=(5, 0))

        # Example label
        self.example_label = ttk.Label(
            rename_frame,
            text="",
            style='Dark.TLabel',
            font=self.fonts['italic']
        )
        self.example_label.pack(anchor='w', pady=(2, 0))

    def _create_sorting_section(self, parent: ttk.Frame) -> None:
        """Create sorting options section"""
        section_frame = ttk.Frame(parent, style='Dark.TFrame')
        section_frame.pack(fill='x', pady=(5, 5))

        # Title
        ttk.Label(
            section_frame,
            text="Sorting Options",
            style='Dark.TLabel',
            font=self.fonts['bold']
        ).pack(anchor='w', pady=(0, 5))

        # Sort by and order in one row
        sort_row = ttk.Frame(section_frame, style='Dark.TFrame')
        sort_row.pack(fill='x')

        # Sort by
        sort_by_frame = ttk.Frame(sort_row, style='Dark.TFrame')
        sort_by_frame.pack(side='left', fill='x', expand=True, padx=(0, 10))

        ttk.Label(sort_by_frame, text="Sort by:", style='Dark.TLabel').pack(anchor='w')
        sort_by_combo = ttk.Combobox(
            sort_by_frame,
            textvariable=self.sort_by_var,
            values=["name", "date_modified", "date_created", "size"],
            state="readonly",
            width=20
        )
        sort_by_combo.pack(fill='x', pady=(5, 0))

        # Sort order
        sort_order_frame = ttk.Frame(sort_row, style='Dark.TFrame')
        sort_order_frame.pack(side='left', fill='x', expand=True)

        ttk.Label(sort_order_frame, text="Order:", style='Dark.TLabel').pack(anchor='w')
        sort_order_combo = ttk.Combobox(
            sort_order_frame,
            textvariable=self.sort_order_var,
            values=["asc", "desc"],
            state="readonly",
            width=20
        )
        sort_order_combo.pack(fill='x', pady=(5, 0))

    def _create_pattern_section(self, parent: ttk.Frame) -> None:
        """Create rename pattern options section"""
        section_frame = ttk.Frame(parent, style='Dark.TFrame')
        section_frame.pack(fill='x', pady=(5, 5))

        # Title
        ttk.Label(
            section_frame,
            text="Rename Pattern",
            style='Dark.TLabel',
            font=self.fonts['bold']
        ).pack(anchor='w', pady=(0, 5))

        # Pattern type
        pattern_type_frame = ttk.Frame(section_frame, style='Dark.TFrame')
        pattern_type_frame.pack(fill='x', pady=(0, 5))

        ttk.Label(pattern_type_frame, text="Pattern Type:", style='Dark.TLabel').pack(anchor='w')
        pattern_combo = ttk.Combobox(
            pattern_type_frame,
            textvariable=self.pattern_type_var,
            values=["numbering", "datetime", "prefix", "custom"],
            state="readonly",
            width=30
        )
        pattern_combo.pack(fill='x', pady=(5, 0))
        pattern_combo.bind('<<ComboboxSelected>>', self._on_pattern_type_changed)

        # Datetime options frame (shown when datetime pattern selected)
        self.datetime_options_frame = ttk.Frame(section_frame, style='Dark.TFrame')

        datetime_row1 = ttk.Frame(self.datetime_options_frame, style='Dark.TFrame')
        datetime_row1.pack(fill='x', pady=(5, 0))

        ttk.Label(datetime_row1, text="DateTime Format:", style='Dark.TLabel').pack(anchor='w')
        datetime_combo = ttk.Combobox(
            datetime_row1,
            textvariable=self.datetime_format_var,
            values=["YYYYMMDD", "YYYY_MM_DD", "YYYYMMDD_HHMMSS", "YYYY_MM_DD_HH_MM_SS", "MMDDYYYY", "DDMMYYYY"],
            state="readonly",
            width=30
        )
        datetime_combo.pack(fill='x', pady=(5, 0))

        datetime_row2 = ttk.Frame(self.datetime_options_frame, style='Dark.TFrame')
        datetime_row2.pack(fill='x', pady=(5, 0))

        counter_check = tk.Checkbutton(
            datetime_row2,
            text="Include counter",
            variable=self.include_counter_var,
            bg=self.colors['background'],
            fg=self.colors['foreground'],
            selectcolor=self.colors['input_bg'],
            activebackground=self.colors['background'],
            activeforeground=self.colors['foreground']
        )
        counter_check.pack(anchor='w')

        # Custom pattern frame (shown when custom pattern selected)
        self.custom_pattern_frame = ttk.Frame(section_frame, style='Dark.TFrame')

        custom_row = ttk.Frame(self.custom_pattern_frame, style='Dark.TFrame')
        custom_row.pack(fill='x', pady=(5, 0))

        ttk.Label(custom_row, text="Custom Pattern:", style='Dark.TLabel').pack(anchor='w')
        ttk.Label(
            custom_row,
            text="Available: {counter}, {date}, {time}, {datetime}, {year}, {month}, {day}, {original}",
            style='Dark.TLabel',
            font=self.fonts['italic']
        ).pack(anchor='w')

        custom_entry = tk.Entry(
            custom_row,
            textvariable=self.custom_pattern_var,
            width=150,
            bg=self.colors['input_bg'],
            fg=self.colors['input_fg'],
            insertbackground=self.colors['insert_cursor'],
            bd=1,
            relief='solid'
        )
        custom_entry.pack(fill='x', pady=(5, 0))

        # Show/hide pattern options based on selection
        self._on_pattern_type_changed()

    def _create_folder_organization_section(self, parent: ttk.Frame) -> None:
        """Create folder organization section"""
        section_frame = ttk.Frame(parent, style='Dark.TFrame')
        section_frame.pack(fill='x', pady=(5, 5))

        # Title
        ttk.Label(
            section_frame,
            text="Folder Organization",
            style='Dark.TLabel',
            font=self.fonts['bold']
        ).pack(anchor='w', pady=(0, 5))

        # Folder structure
        folder_frame = ttk.Frame(section_frame, style='Dark.TFrame')
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

    def _create_templates_section(self, parent: ttk.Frame) -> None:
        """Create templates section for saving/loading presets"""
        section_frame = ttk.Frame(parent, style='Dark.TFrame')
        section_frame.pack(fill='x', pady=(0, 15))

        # Title
        ttk.Label(
            section_frame,
            text="Templates",
            style='Dark.TLabel',
            font=self.fonts['bold']
        ).pack(anchor='w', pady=(0, 5))

        # Template controls row
        controls_frame = ttk.Frame(section_frame, style='Dark.TFrame')
        controls_frame.pack(fill='x')

        # Template dropdown
        dropdown_frame = ttk.Frame(controls_frame, style='Dark.TFrame')
        dropdown_frame.pack(side='left', fill='x', expand=True, padx=(0, 10))

        self.template_combo = ttk.Combobox(
            dropdown_frame,
            textvariable=self.template_var,
            values=self.template_manager.get_template_names(),
            state="readonly",
            width=40
        )
        self.template_combo.pack(fill='x')

        # Buttons frame
        buttons_frame = ttk.Frame(controls_frame, style='Dark.TFrame')
        buttons_frame.pack(side='right')

        # Load button
        self.load_template_btn = tk.Button(
            buttons_frame,
            text="Load",
            command=self._load_template,
            bg=self.colors['button_bg'],
            fg=self.colors['button_fg'],
            font=self.fonts['button'],
            relief='raised',
            bd=2,
            padx=10,
            pady=2
        )
        self.load_template_btn.pack(side='left', padx=(0, 5))

        # Save button
        self.save_template_btn = tk.Button(
            buttons_frame,
            text="Save",
            command=self._save_template,
            bg=self.colors['button_bg'],
            fg=self.colors['button_fg'],
            font=self.fonts['button'],
            relief='raised',
            bd=2,
            padx=10,
            pady=2
        )
        self.save_template_btn.pack(side='left', padx=(0, 5))

        # Manage button
        self.manage_templates_btn = tk.Button(
            buttons_frame,
            text="Manage",
            command=self._manage_templates,
            bg=self.colors['button_bg'],
            fg=self.colors['button_fg'],
            font=self.fonts['button'],
            relief='raised',
            bd=2,
            padx=10,
            pady=2
        )
        self.manage_templates_btn.pack(side='left')

    def _create_folder_input(
        self,
        parent: ttk.Frame,
        label: str,
        variable: tk.StringVar,
        browse_command: Callable
    ) -> None:
        """Create a folder input field with browse button"""
        frame = ttk.Frame(parent, style='Dark.TFrame')
        frame.pack(fill='x', pady=(0, 10))

        ttk.Label(frame, text=label, style='Dark.TLabel').pack(anchor='w')

        input_frame = tk.Frame(frame, bg=self.colors['background'])
        input_frame.pack(fill='x', pady=(5, 0))

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

    def _create_text_input(
        self,
        parent: ttk.Frame,
        label: str,
        variable: tk.StringVar
    ) -> None:
        """Create a simple text input field"""
        frame = ttk.Frame(parent, style='Dark.TFrame')
        frame.pack(fill='x', pady=(0, 10))

        ttk.Label(frame, text=label, style='Dark.TLabel').pack(anchor='w')

        entry = tk.Entry(
            frame,
            textvariable=variable,
            width=150,
            bg=self.colors['input_bg'],
            fg=self.colors['input_fg'],
            insertbackground=self.colors['insert_cursor'],
            bd=1,
            relief='solid'
        )
        entry.pack(fill='x', pady=(5, 0))

    def _create_buttons(self, parent: ttk.Frame) -> None:
        """Create action buttons"""
        button_frame = ttk.Frame(parent, style='Dark.TFrame')
        button_frame.pack(fill='x', pady=(5, 10))

        # Move and Rename button
        self.move_button = tk.Button(
            button_frame,
            text="Move and Rename",
            command=self._move_and_rename,
            bg=self.colors['button_bg'],
            fg=self.colors['button_fg'],
            font=self.fonts['button'],
            relief='raised',
            bd=2,
            padx=20,
            pady=10
        )
        self.move_button.pack(side='left', padx=(0, 10))

        # Settings button
        self.settings_button = tk.Button(
            button_frame,
            text="Settings",
            command=self._open_settings,
            bg=self.colors['button_bg'],
            fg=self.colors['button_fg'],
            font=self.fonts['button'],
            relief='raised',
            bd=2,
            padx=20,
            pady=10
        )
        self.settings_button.pack(side='left')

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
            height=8
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
        self.add_status("Ready to move and rename files...")

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

    def _on_pattern_type_changed(self, *args) -> None:
        """Handle pattern type change"""
        pattern_type = self.pattern_type_var.get()

        # Hide all pattern-specific frames
        self.datetime_options_frame.pack_forget()
        self.custom_pattern_frame.pack_forget()

        # Show relevant frame
        if pattern_type == "datetime":
            self.datetime_options_frame.pack(fill='x', pady=(5, 0))
        elif pattern_type == "custom":
            self.custom_pattern_frame.pack(fill='x', pady=(5, 0))

        self._update_example()

    def _update_example(self, *args) -> None:
        """Update the example filename as user types"""
        try:
            base_name = self.rename_var.get().strip()
            extension = self.ext_var.get().strip()

            if not extension.startswith('.') and extension:
                extension = '.' + extension

            if not base_name:
                self.example_label.config(text="")
                return

            # Create pattern
            pattern_type = PatternType(self.pattern_type_var.get())
            pattern = self._create_pattern(pattern_type)

            # Generate example filename
            example_filename = pattern.generate_filename(
                base_name,
                extension,
                1,
                None
            )

            self.example_label.config(text=f"Example: {example_filename}")
        except Exception:
            self.example_label.config(text="")

    def _update_folder_example(self, *args) -> None:
        """Update the folder organization example"""
        try:
            structure = FolderStructure(self.folder_structure_var.get())
            example = FolderOrganizer.get_folder_structure_example(structure)
            self.folder_example_label.config(text=f"Example: {example}")
        except Exception:
            self.folder_example_label.config(text="")

    def _create_pattern(self, pattern_type: PatternType) -> 'RenamePattern':
        """Create rename pattern from UI settings"""
        if pattern_type == PatternType.NUMBERING:
            return PatternFactory.create_pattern(PatternType.NUMBERING)

        elif pattern_type == PatternType.DATETIME:
            dt_format = DateTimeFormat[self.datetime_format_var.get()]
            return PatternFactory.create_pattern(
                PatternType.DATETIME,
                datetime_format=dt_format,
                include_counter=self.include_counter_var.get(),
                use_file_date=True
            )

        elif pattern_type == PatternType.PREFIX:
            return PatternFactory.create_pattern(
                PatternType.PREFIX,
                prefix=self.rename_var.get().strip(),
                keep_original_name=True
            )

        elif pattern_type == PatternType.CUSTOM:
            return PatternFactory.create_pattern(
                PatternType.CUSTOM,
                pattern_string=self.custom_pattern_var.get()
            )

        else:
            return PatternFactory.create_pattern(PatternType.NUMBERING)

    def _open_settings(self) -> None:
        """Open the settings dialog"""
        from ui.settings_dialog import SettingsDialog
        SettingsDialog(self.root, self)

    def _move_and_rename(self) -> None:
        """Handle move and rename operation"""
        # Get values
        source_folder = self.source_var.get().strip()
        dest_folder = self.dest_var.get().strip()
        extension = self.ext_var.get().strip()
        base_name = self.rename_var.get().strip()

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

        if not base_name:
            messagebox.showerror("Error", "Please enter a base name")
            return

        self.add_status("Starting move and rename operation...")

        try:
            # Create pattern
            pattern_type = PatternType(self.pattern_type_var.get())
            pattern = self._create_pattern(pattern_type)

            # Get sorting options
            sort_by_value = self.sort_by_var.get()
            if sort_by_value == "name":
                sort_by = SortBy.NAME
            elif sort_by_value == "date_modified":
                sort_by = SortBy.DATE_MODIFIED
            elif sort_by_value == "date_created":
                sort_by = SortBy.DATE_CREATED
            elif sort_by_value == "size":
                sort_by = SortBy.SIZE
            else:
                sort_by = SortBy.NAME

            sort_order = SortOrder.ASCENDING if self.sort_order_var.get() == "asc" else SortOrder.DESCENDING

            # Get folder structure
            folder_structure = FolderStructure(self.folder_structure_var.get())

            # Create file renamer
            file_renamer = FileRenamer(
                status_callback=self.add_status,
                rename_pattern=pattern,
                sort_by=sort_by,
                sort_order=sort_order,
                folder_structure=folder_structure
            )

            # Perform operation
            results = file_renamer.move_and_rename(
                source_folder,
                dest_folder,
                extension,
                base_name
            )

            # Count results
            success_count = sum(1 for r in results if r.success)
            error_count = sum(1 for r in results if not r.success)

            # Save configuration
            self.config.set("last_extension", extension)
            self.config.set("last_rename_to", base_name)
            self.config.set("sort_by", self.sort_by_var.get())
            self.config.set("sort_order", self.sort_order_var.get())
            self.config.set("pattern_type", self.pattern_type_var.get())
            self.config.set("datetime_format", self.datetime_format_var.get())
            self.config.set("include_counter", self.include_counter_var.get())
            self.config.set("folder_structure", self.folder_structure_var.get())
            self.config.set("custom_pattern", self.custom_pattern_var.get())
            self.config.save()

            # Show result
            if error_count == 0 and success_count > 0:
                messagebox.showinfo("Success", f"Successfully moved and renamed {success_count} files")
            elif success_count > 0:
                messagebox.showwarning(
                    "Completed with errors",
                    f"Moved {success_count} files with {error_count} errors. Check status for details."
                )
            elif error_count == 0:
                # No files found
                messagebox.showinfo("No Files", "No files were found to process")

        except ValueError as e:
            messagebox.showerror("Validation Error", str(e))
        except OSError as e:
            messagebox.showerror("File System Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")

    def add_status(self, message: str) -> None:
        """Add a status message to the listbox"""
        self.status_listbox.insert(tk.END, message)
        self.status_listbox.see(tk.END)
        self.root.update_idletasks()

    def update_from_config(self) -> None:
        """Update UI fields from configuration"""
        self.source_var.set(self.config.get("default_source_folder", ""))
        self.dest_var.set(self.config.get("default_destination_folder", ""))

    def _get_current_settings(self) -> dict:
        """Get all current UI settings as a dictionary"""
        return {
            "default_source_folder": self.source_var.get(),
            "default_destination_folder": self.dest_var.get(),
            "last_extension": self.ext_var.get(),
            "last_rename_to": self.rename_var.get(),
            "sort_by": self.sort_by_var.get(),
            "sort_order": self.sort_order_var.get(),
            "pattern_type": self.pattern_type_var.get(),
            "datetime_format": self.datetime_format_var.get(),
            "include_counter": self.include_counter_var.get(),
            "folder_structure": self.folder_structure_var.get(),
            "custom_pattern": self.custom_pattern_var.get()
        }

    def _apply_settings(self, settings: dict) -> None:
        """Apply settings dictionary to UI"""
        if "default_source_folder" in settings:
            self.source_var.set(settings["default_source_folder"] or "")
        if "default_destination_folder" in settings:
            self.dest_var.set(settings["default_destination_folder"] or "")
        if "last_extension" in settings:
            self.ext_var.set(settings["last_extension"] or "")
        if "last_rename_to" in settings:
            self.rename_var.set(settings["last_rename_to"] or "")
        if "sort_by" in settings:
            self.sort_by_var.set(settings["sort_by"] or "name")
        if "sort_order" in settings:
            self.sort_order_var.set(settings["sort_order"] or "asc")
        if "pattern_type" in settings:
            self.pattern_type_var.set(settings["pattern_type"] or "numbering")
        if "datetime_format" in settings:
            self.datetime_format_var.set(settings["datetime_format"] or "YYYYMMDD")
        if "include_counter" in settings:
            self.include_counter_var.set(settings.get("include_counter", True))
        if "folder_structure" in settings:
            self.folder_structure_var.set(settings["folder_structure"] or "flat")
        if "custom_pattern" in settings:
            self.custom_pattern_var.set(settings["custom_pattern"] or "{counter}")

        # Update pattern UI visibility
        self._on_pattern_type_changed()

    def _refresh_template_list(self) -> None:
        """Refresh the template dropdown with current templates"""
        self.template_combo['values'] = self.template_manager.get_template_names()

    def _load_template(self) -> None:
        """Load selected template and apply settings"""
        template_name = self.template_var.get()
        if not template_name:
            messagebox.showwarning("No Template Selected", "Please select a template to load.")
            return

        template = self.template_manager.get_template(template_name)
        if template:
            self._apply_settings(template)
            self.add_status(f"Template '{template_name}' loaded successfully.")
        else:
            messagebox.showerror("Error", f"Template '{template_name}' not found.")

    def _save_template(self) -> None:
        """Save current settings as a template"""
        from ui.save_template_dialog import SaveTemplateDialog
        dialog = SaveTemplateDialog(self.root, self)

    def _manage_templates(self) -> None:
        """Open template management dialog"""
        from ui.manage_templates_dialog import ManageTemplatesDialog
        dialog = ManageTemplatesDialog(self.root, self)
