"""Manage Templates dialog for File Rename Mover application"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.main_window_v2 import MainWindowV2


class ManageTemplatesDialog:
    """Dialog for managing saved templates"""

    def __init__(self, parent: tk.Tk, app: 'MainWindowV2'):
        """
        Initialize manage templates dialog

        Args:
            parent: Parent window
            app: Main application window instance
        """
        self.app = app
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Manage Templates")
        self.dialog.geometry("600x450")
        self.dialog.configure(bg=app.colors['background'])
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center the dialog
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 600) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 450) // 2
        self.dialog.geometry(f"+{x}+{y}")

        self._setup_ui()
        self._refresh_list()

        # Bind keyboard shortcuts
        self.dialog.bind('<Delete>', lambda e: self._delete_template())
        self.dialog.bind('<Escape>', lambda e: self.dialog.destroy())

    def _setup_ui(self) -> None:
        """Set up the dialog UI"""
        main_frame = ttk.Frame(self.dialog, style='Dark.TFrame')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # Title
        title_label = ttk.Label(
            main_frame,
            text="Manage Templates",
            style='Dark.TLabel',
            font=self.app.fonts['title']
        )
        title_label.pack(anchor='w', pady=(0, 15))

        # Content frame (list + buttons side by side)
        content_frame = ttk.Frame(main_frame, style='Dark.TFrame')
        content_frame.pack(fill='both', expand=True)

        # Template list with scrollbar
        list_frame = ttk.Frame(content_frame, style='Dark.TFrame')
        list_frame.pack(side='left', fill='both', expand=True, padx=(0, 15))

        self.template_listbox = tk.Listbox(
            list_frame,
            bg=self.app.colors['input_bg'],
            fg=self.app.colors['input_fg'],
            selectbackground=self.app.colors['select_bg'],
            selectforeground=self.app.colors['select_fg'],
            bd=1,
            relief='solid',
            font=self.app.fonts['default'],
            selectmode=tk.SINGLE
        )
        self.template_listbox.pack(side='left', fill='both', expand=True)

        scrollbar = tk.Scrollbar(
            list_frame,
            bg=self.app.colors['scrollbar_bg'],
            troughcolor=self.app.colors['scrollbar_trough']
        )
        scrollbar.pack(side='right', fill='y')

        self.template_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.template_listbox.yview)

        # Bind double-click to load
        self.template_listbox.bind('<Double-Button-1>', lambda e: self._load_and_close())

        # Button frame
        button_frame = ttk.Frame(content_frame, style='Dark.TFrame')
        button_frame.pack(side='right', fill='y')

        # Action buttons
        buttons = [
            ("Load", self._load_and_close),
            ("Rename", self._rename_template),
            ("Duplicate", self._duplicate_template),
            ("Delete", self._delete_template),
        ]

        for text, command in buttons:
            btn = tk.Button(
                button_frame,
                text=text,
                command=command,
                bg=self.app.colors['button_bg'],
                fg=self.app.colors['button_fg'],
                font=self.app.fonts['button'],
                relief='raised',
                bd=2,
                width=12,
                pady=5
            )
            btn.pack(pady=(0, 10))

        # Close button at the bottom
        close_frame = ttk.Frame(main_frame, style='Dark.TFrame')
        close_frame.pack(fill='x', pady=(15, 0))

        close_btn = tk.Button(
            close_frame,
            text="Close",
            command=self.dialog.destroy,
            bg=self.app.colors['button_bg'],
            fg=self.app.colors['button_fg'],
            font=self.app.fonts['button'],
            relief='raised',
            bd=2,
            padx=20,
            pady=5
        )
        close_btn.pack(side='right')

        # Template details frame
        details_frame = ttk.Frame(main_frame, style='Dark.TFrame')
        details_frame.pack(fill='x', pady=(15, 0))

        ttk.Label(
            details_frame,
            text="Template Details:",
            style='Dark.TLabel',
            font=self.app.fonts['bold']
        ).pack(anchor='w')

        self.details_text = tk.Text(
            details_frame,
            bg=self.app.colors['input_bg'],
            fg=self.app.colors['input_fg'],
            bd=1,
            relief='solid',
            font=self.app.fonts['default'],
            height=6,
            state='disabled',
            wrap='word'
        )
        self.details_text.pack(fill='x', pady=(5, 0))

        # Bind selection change
        self.template_listbox.bind('<<ListboxSelect>>', self._on_selection_change)

    def _refresh_list(self) -> None:
        """Refresh the template list"""
        self.template_listbox.delete(0, tk.END)
        for name in self.app.template_manager.get_template_names():
            self.template_listbox.insert(tk.END, name)

    def _get_selected_name(self) -> str | None:
        """Get the currently selected template name"""
        selection = self.template_listbox.curselection()
        if selection:
            return self.template_listbox.get(selection[0])
        return None

    def _on_selection_change(self, event=None) -> None:
        """Handle selection change in the listbox"""
        name = self._get_selected_name()
        if name:
            template = self.app.template_manager.get_template(name)
            if template:
                self._show_template_details(template)
        else:
            self._clear_details()

    def _show_template_details(self, template: dict) -> None:
        """Show template details in the details text widget"""
        self.details_text.config(state='normal')
        self.details_text.delete('1.0', tk.END)

        # Format template details
        details = []
        if template.get('default_source_folder'):
            details.append(f"Source: {template['default_source_folder']}")
        if template.get('default_destination_folder'):
            details.append(f"Destination: {template['default_destination_folder']}")
        if template.get('last_extension'):
            details.append(f"Extension: {template['last_extension']}")
        if template.get('last_rename_to'):
            details.append(f"Base Name: {template['last_rename_to']}")
        if template.get('pattern_type'):
            details.append(f"Pattern: {template['pattern_type']}")
        if template.get('folder_structure'):
            details.append(f"Folder Structure: {template['folder_structure']}")

        self.details_text.insert('1.0', '\n'.join(details))
        self.details_text.config(state='disabled')

    def _clear_details(self) -> None:
        """Clear the details text widget"""
        self.details_text.config(state='normal')
        self.details_text.delete('1.0', tk.END)
        self.details_text.config(state='disabled')

    def _load_and_close(self) -> None:
        """Load selected template and close dialog"""
        name = self._get_selected_name()
        if not name:
            messagebox.showwarning(
                "No Selection",
                "Please select a template to load.",
                parent=self.dialog
            )
            return

        template = self.app.template_manager.get_template(name)
        if template:
            self.app._apply_settings(template)
            self.app.template_var.set(name)
            self.app._refresh_template_list()
            self.app.add_status(f"Template '{name}' loaded successfully.")
            self.dialog.destroy()

    def _rename_template(self) -> None:
        """Rename the selected template"""
        old_name = self._get_selected_name()
        if not old_name:
            messagebox.showwarning(
                "No Selection",
                "Please select a template to rename.",
                parent=self.dialog
            )
            return

        new_name = simpledialog.askstring(
            "Rename Template",
            "Enter new name:",
            initialvalue=old_name,
            parent=self.dialog
        )

        if new_name and new_name.strip() and new_name.strip() != old_name:
            new_name = new_name.strip()
            if self.app.template_manager.template_exists(new_name):
                messagebox.showerror(
                    "Name Exists",
                    f"A template named '{new_name}' already exists.",
                    parent=self.dialog
                )
                return

            if self.app.template_manager.rename_template(old_name, new_name):
                self._refresh_list()
                self.app._refresh_template_list()
                # Select the renamed item
                names = self.app.template_manager.get_template_names()
                if new_name in names:
                    idx = names.index(new_name)
                    self.template_listbox.selection_set(idx)
                    self.template_listbox.see(idx)
                self.app.add_status(f"Template renamed from '{old_name}' to '{new_name}'.")
            else:
                messagebox.showerror(
                    "Rename Failed",
                    "Failed to rename template.",
                    parent=self.dialog
                )

    def _duplicate_template(self) -> None:
        """Duplicate the selected template"""
        source_name = self._get_selected_name()
        if not source_name:
            messagebox.showwarning(
                "No Selection",
                "Please select a template to duplicate.",
                parent=self.dialog
            )
            return

        new_name = simpledialog.askstring(
            "Duplicate Template",
            "Enter name for the copy:",
            initialvalue=f"{source_name} (Copy)",
            parent=self.dialog
        )

        if new_name and new_name.strip():
            new_name = new_name.strip()
            if self.app.template_manager.template_exists(new_name):
                messagebox.showerror(
                    "Name Exists",
                    f"A template named '{new_name}' already exists.",
                    parent=self.dialog
                )
                return

            if self.app.template_manager.duplicate_template(source_name, new_name):
                self._refresh_list()
                self.app._refresh_template_list()
                # Select the new item
                names = self.app.template_manager.get_template_names()
                if new_name in names:
                    idx = names.index(new_name)
                    self.template_listbox.selection_set(idx)
                    self.template_listbox.see(idx)
                self.app.add_status(f"Template '{source_name}' duplicated as '{new_name}'.")
            else:
                messagebox.showerror(
                    "Duplicate Failed",
                    "Failed to duplicate template.",
                    parent=self.dialog
                )

    def _delete_template(self) -> None:
        """Delete the selected template"""
        name = self._get_selected_name()
        if not name:
            messagebox.showwarning(
                "No Selection",
                "Please select a template to delete.",
                parent=self.dialog
            )
            return

        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete the template '{name}'?",
            parent=self.dialog
        )

        if confirm:
            if self.app.template_manager.delete_template(name):
                self._refresh_list()
                self.app._refresh_template_list()
                self._clear_details()
                # Clear selection in main window if this was the selected template
                if self.app.template_var.get() == name:
                    self.app.template_var.set("")
                self.app.add_status(f"Template '{name}' deleted.")
            else:
                messagebox.showerror(
                    "Delete Failed",
                    "Failed to delete template.",
                    parent=self.dialog
                )
