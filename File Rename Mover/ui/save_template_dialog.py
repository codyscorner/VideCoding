"""Save Template dialog for File Rename Mover application"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.main_window_v2 import MainWindowV2


class SaveTemplateDialog:
    """Dialog for saving current settings as a template"""

    def __init__(self, parent: tk.Tk, app: 'MainWindowV2'):
        """
        Initialize save template dialog

        Args:
            parent: Parent window
            app: Main application window instance
        """
        self.app = app
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Save Template")
        self.dialog.geometry("450x180")
        self.dialog.configure(bg=app.colors['background'])
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center the dialog
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 450) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 180) // 2
        self.dialog.geometry(f"+{x}+{y}")

        # Variables
        self.name_var = tk.StringVar()

        self._setup_ui()

        # Focus the name entry
        self.name_entry.focus_set()

        # Bind Enter key to save
        self.dialog.bind('<Return>', lambda e: self._save_template())
        self.dialog.bind('<Escape>', lambda e: self.dialog.destroy())

    def _setup_ui(self) -> None:
        """Set up the dialog UI"""
        main_frame = ttk.Frame(self.dialog, style='Dark.TFrame')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # Title
        title_label = ttk.Label(
            main_frame,
            text="Save Current Settings as Template",
            style='Dark.TLabel',
            font=self.app.fonts['bold']
        )
        title_label.pack(anchor='w', pady=(0, 15))

        # Template name input
        name_frame = ttk.Frame(main_frame, style='Dark.TFrame')
        name_frame.pack(fill='x', pady=(0, 15))

        ttk.Label(
            name_frame,
            text="Template Name:",
            style='Dark.TLabel'
        ).pack(anchor='w')

        self.name_entry = tk.Entry(
            name_frame,
            textvariable=self.name_var,
            bg=self.app.colors['input_bg'],
            fg=self.app.colors['input_fg'],
            insertbackground=self.app.colors['insert_cursor'],
            bd=1,
            relief='solid',
            font=self.app.fonts['default']
        )
        self.name_entry.pack(fill='x', pady=(5, 0))

        # Buttons
        button_frame = ttk.Frame(main_frame, style='Dark.TFrame')
        button_frame.pack(fill='x', pady=(10, 0))

        # Save button
        save_btn = tk.Button(
            button_frame,
            text="Save",
            command=self._save_template,
            bg=self.app.colors['button_bg'],
            fg=self.app.colors['button_fg'],
            font=self.app.fonts['button'],
            relief='raised',
            bd=2,
            padx=20,
            pady=5
        )
        save_btn.pack(side='left', padx=(0, 10))

        # Cancel button
        cancel_btn = tk.Button(
            button_frame,
            text="Cancel",
            command=self.dialog.destroy,
            bg=self.app.colors['button_bg'],
            fg=self.app.colors['button_fg'],
            font=self.app.fonts['button'],
            relief='raised',
            bd=2,
            padx=20,
            pady=5
        )
        cancel_btn.pack(side='left')

    def _save_template(self) -> None:
        """Save the template and close dialog"""
        name = self.name_var.get().strip()

        if not name:
            messagebox.showwarning(
                "Name Required",
                "Please enter a name for the template.",
                parent=self.dialog
            )
            return

        # Check if template already exists
        if self.app.template_manager.template_exists(name):
            confirm = messagebox.askyesno(
                "Template Exists",
                f"A template named '{name}' already exists.\nDo you want to overwrite it?",
                parent=self.dialog
            )
            if not confirm:
                return

        # Get current settings and save template
        settings = self.app._get_current_settings()
        if self.app.template_manager.save_template(name, settings):
            self.app._refresh_template_list()
            self.app.template_var.set(name)
            self.app.add_status(f"Template '{name}' saved successfully.")
            self.dialog.destroy()
        else:
            messagebox.showerror(
                "Save Failed",
                "Failed to save template. Please try again.",
                parent=self.dialog
            )
