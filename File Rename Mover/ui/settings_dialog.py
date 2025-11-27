"""Settings dialog for File Rename Mover application"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.main_window import MainWindow


class SettingsDialog:
    """Settings dialog window"""

    def __init__(self, parent: tk.Tk, app: 'MainWindow'):
        """
        Initialize settings dialog

        Args:
            parent: Parent window
            app: Main application window instance
        """
        self.app = app
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Settings")
        self.dialog.geometry("700x300")
        self.dialog.configure(bg=app.colors['background'])
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Variables
        self.source_var = tk.StringVar(value=app.config.get("default_source_folder", ""))
        self.dest_var = tk.StringVar(value=app.config.get("default_destination_folder", ""))

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the settings dialog UI"""
        main_frame = ttk.Frame(self.dialog, style='Dark.TFrame')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # Title
        title_label = ttk.Label(
            main_frame,
            text="Default Folder Settings",
            style='Dark.TLabel',
            font=self.app.fonts['title']
        )
        title_label.pack(anchor='w', pady=(0, 20))

        # Default Source Folder
        self._create_folder_input(
            main_frame,
            "Default Source Folder:",
            self.source_var,
            self._browse_source
        )

        # Default Destination Folder
        self._create_folder_input(
            main_frame,
            "Default Destination Folder:",
            self.dest_var,
            self._browse_destination
        )

        # Buttons
        self._create_buttons(main_frame)

    def _create_folder_input(
        self,
        parent: ttk.Frame,
        label: str,
        variable: tk.StringVar,
        browse_command
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
        frame.pack(fill='x', pady=(0, 15))

        ttk.Label(frame, text=label, style='Dark.TLabel').pack(anchor='w')

        input_frame = tk.Frame(frame, bg=self.app.colors['background'])
        input_frame.pack(fill='x', pady=(5, 0))

        entry = tk.Entry(
            input_frame,
            textvariable=variable,
            bg=self.app.colors['input_bg'],
            fg=self.app.colors['input_fg'],
            insertbackground=self.app.colors['insert_cursor'],
            bd=1,
            relief='solid'
        )
        entry.pack(side='left', fill='x', expand=True, padx=(0, 5))

        browse_btn = tk.Button(
            input_frame,
            text="...",
            command=browse_command,
            bg=self.app.colors['button_bg'],
            fg=self.app.colors['button_fg'],
            relief='raised',
            bd=2,
            width=3,
            height=1,
            font=self.app.fonts['button'],
            activebackground=self.app.colors['button_active'],
            activeforeground=self.app.colors['button_fg']
        )
        browse_btn.pack(side='right')

    def _create_buttons(self, parent: ttk.Frame) -> None:
        """Create action buttons"""
        button_frame = ttk.Frame(parent, style='Dark.TFrame')
        button_frame.pack(fill='x', pady=(20, 0))

        # Save button
        self.save_button = tk.Button(
            button_frame,
            text="Save",
            command=self._save_settings,
            bg=self.app.colors['button_bg'],
            fg=self.app.colors['button_fg'],
            font=self.app.fonts['button'],
            relief='raised',
            bd=2,
            padx=20,
            pady=10
        )
        self.save_button.pack(side='left', padx=(0, 10))

        # Cancel button
        self.cancel_button = tk.Button(
            button_frame,
            text="Cancel",
            command=self.dialog.destroy,
            bg=self.app.colors['button_bg'],
            fg=self.app.colors['button_fg'],
            font=self.app.fonts['button'],
            relief='raised',
            bd=2,
            padx=20,
            pady=10
        )
        self.cancel_button.pack(side='left')

    def _browse_source(self) -> None:
        """Handle source folder browse button"""
        initial_dir = self.source_var.get() or None
        folder = filedialog.askdirectory(
            title="Select Default Source Folder",
            initialdir=initial_dir
        )
        if folder:
            self.source_var.set(folder)

    def _browse_destination(self) -> None:
        """Handle destination folder browse button"""
        initial_dir = self.dest_var.get() or None
        folder = filedialog.askdirectory(
            title="Select Default Destination Folder",
            initialdir=initial_dir
        )
        if folder:
            self.dest_var.set(folder)

    def _save_settings(self) -> None:
        """Save settings and close dialog"""
        # Update config
        self.app.config.set("default_source_folder", self.source_var.get())
        self.app.config.set("default_destination_folder", self.dest_var.get())
        self.app.config.save()

        # Update main window fields
        self.app.update_from_config()

        messagebox.showinfo("Settings Saved", "Default folders have been updated successfully!")
        self.dialog.destroy()
