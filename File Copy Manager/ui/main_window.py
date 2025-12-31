"""Main window UI for File Copy Manager application"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Optional, Callable

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
        self.root.geometry("1000x870")
        self.root.configure(bg='#1a1a1a')

        # Set minimum window size
        self.root.minsize(1000, 870)

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

        # Folder organization
        self._create_folder_organization_section(main_frame)

        # Buttons
        self._create_buttons(main_frame)

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
        """Create extension input"""
        frame = ttk.Frame(parent, style='Dark.TFrame')
        frame.pack(fill='x', pady=(0, 10))

        ttk.Label(frame, text="File Extension:", style='Dark.TLabel').pack(anchor='w')

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
        entry.pack(fill='x', pady=(5, 0))

        ttk.Label(
            frame,
            text="Example: .jpg, .png, .pdf",
            style='Dark.TLabel',
            font=self.fonts['italic']
        ).pack(anchor='w', pady=(2, 0))

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

    def _create_buttons(self, parent: ttk.Frame) -> None:
        """Create action buttons"""
        button_frame = ttk.Frame(parent, style='Dark.TFrame')
        button_frame.pack(fill='x', pady=(5, 10))

        # Copy Files button
        self.copy_button = tk.Button(
            button_frame,
            text="Copy Files",
            command=self._copy_files,
            bg=self.colors['button_bg'],
            fg=self.colors['button_fg'],
            font=self.fonts['button'],
            relief='raised',
            bd=2,
            padx=20,
            pady=10
        )
        self.copy_button.pack(side='left', padx=(0, 10))

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

    def _update_folder_example(self, *args) -> None:
        """Update the folder organization example"""
        try:
            structure = FolderStructure(self.folder_structure_var.get())
            example = FolderOrganizer.get_folder_structure_example(structure)
            self.folder_example_label.config(text=f"Example: {example}")
        except Exception:
            self.folder_example_label.config(text="")

    def _copy_files(self) -> None:
        """Handle copy files operation"""
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

        self.add_status("Starting copy operation...")

        try:
            # Get options
            preserve_structure = self.preserve_structure_var.get()
            number_duplicates = self.number_duplicates_var.get()
            recursive_search = self.recursive_search_var.get()
            folder_structure = FolderStructure(self.folder_structure_var.get())

            # Create file copier
            file_copier = FileCopier(
                status_callback=self.add_status,
                folder_structure=folder_structure,
                number_duplicates=number_duplicates
            )

            # Perform operation
            results = file_copier.copy_files(
                source_folder,
                dest_folder,
                extension,
                preserve_structure,
                recursive_search
            )

            # Count results
            success_count = sum(1 for r in results if r.success)
            error_count = sum(1 for r in results if not r.success)

            # Save configuration
            self.config.set("last_extension", extension)
            self.config.set("preserve_structure", preserve_structure)
            self.config.set("folder_structure", self.folder_structure_var.get())
            self.config.set("number_duplicates", number_duplicates)
            self.config.set("recursive_search", recursive_search)
            self.config.save()

            # Show result
            if error_count == 0 and success_count > 0:
                messagebox.showinfo("Success", f"Successfully copied {success_count} files")
            elif success_count > 0:
                messagebox.showwarning(
                    "Completed with errors",
                    f"Copied {success_count} files with {error_count} errors. Check status for details."
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
