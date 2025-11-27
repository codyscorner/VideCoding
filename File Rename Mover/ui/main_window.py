"""Main window UI for File Rename Mover application"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Optional, Callable

from config import ConfigManager
from file_operations import FileRenamer
from ui.styles import ThemeManager


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
        self.root.title(f"File Rename Mover (V-{self.version})")
        self.root.geometry("800x600")
        self.root.configure(bg='#1a1a1a')

        # Initialize theme
        self.style = ttk.Style()
        self.theme = ThemeManager(self.style, 'dark_red')
        self.colors = self.theme.get_all_colors()
        self.fonts = self.theme.get_all_fonts()

        # Initialize file renamer
        self.file_renamer = FileRenamer(status_callback=self.add_status)

        # UI Variables
        self.source_var = tk.StringVar(value=self.config.get("default_source_folder", ""))
        self.dest_var = tk.StringVar(value=self.config.get("default_destination_folder", ""))
        self.ext_var = tk.StringVar(value=self.config.get("last_extension", ""))
        self.rename_var = tk.StringVar(value=self.config.get("last_rename_to", ""))

        # Build UI
        self._setup_ui()

        # Set up variable traces
        self.ext_var.trace_add('write', self._update_example)
        self.rename_var.trace_add('write', self._update_example)

    def _setup_ui(self) -> None:
        """Set up the main UI components"""
        main_frame = ttk.Frame(self.root, style='Dark.TFrame')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # Source Folder
        self._create_folder_input(
            main_frame,
            "Source Folder:",
            self.source_var,
            self._browse_source
        )

        # Destination Folder
        self._create_folder_input(
            main_frame,
            "Destination Folder:",
            self.dest_var,
            self._browse_destination
        )

        # Extension
        self._create_text_input(
            main_frame,
            "Extension:",
            self.ext_var
        )

        # Rename pattern
        rename_frame = ttk.Frame(main_frame, style='Dark.TFrame')
        rename_frame.pack(fill='x', pady=(0, 10))

        ttk.Label(
            rename_frame,
            text="Rename to: (Note: _######_ will be automatically added)",
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
        self._update_example()

        # Buttons
        self._create_buttons(main_frame)

        # Status listbox
        self._create_status_listbox(main_frame)

    def _create_folder_input(
        self,
        parent: ttk.Frame,
        label: str,
        variable: tk.StringVar,
        browse_command: Callable
    ) -> None:
        """
        Create a folder input field with browse button

        Args:
            parent: Parent frame
            label: Label text
            variable: StringVar for the entry
            browse_command: Command for browse button
        """
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
        """
        Create a simple text input field

        Args:
            parent: Parent frame
            label: Label text
            variable: StringVar for the entry
        """
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
        button_frame.pack(fill='x', pady=(10, 20))

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
            relief='solid'
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

    def _update_example(self, *args) -> None:
        """Update the example filename as user types"""
        rename_to = self.rename_var.get().strip()
        extension = self.ext_var.get().strip()

        if not extension.startswith('.') and extension:
            extension = '.' + extension

        if rename_to:
            example = f"Example: {rename_to}_000001_{extension}"
        else:
            example = ""

        self.example_label.config(text=example)

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
        rename_to = self.rename_var.get().strip()

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

        if not rename_to:
            messagebox.showerror("Error", "Please enter a rename pattern")
            return

        self.add_status("Starting move and rename operation...")

        try:
            # Perform operation
            results = self.file_renamer.move_and_rename(
                source_folder,
                dest_folder,
                extension,
                rename_to
            )

            # Count results
            success_count = sum(1 for r in results if r.success)
            error_count = sum(1 for r in results if not r.success)

            # Save configuration
            self.config.set("last_extension", extension)
            self.config.set("last_rename_to", rename_to)
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
        """
        Add a status message to the listbox

        Args:
            message: Message to add
        """
        self.status_listbox.insert(tk.END, message)
        self.status_listbox.see(tk.END)
        self.root.update_idletasks()

    def update_from_config(self) -> None:
        """Update UI fields from configuration"""
        self.source_var.set(self.config.get("default_source_folder", ""))
        self.dest_var.set(self.config.get("default_destination_folder", ""))
