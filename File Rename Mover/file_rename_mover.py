import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import shutil
import re
import json
from pathlib import Path

class FileRenameMover:
    def __init__(self, root):
        self.root = root
        self.root.title("File Rename Mover")
        self.root.geometry("800x600")
        self.root.configure(bg='#1a1a1a')

        # Get the directory where the script is located
        self.script_dir = Path(__file__).parent
        self.config_file = self.script_dir / "config.json"

        # Load configuration
        self.config = self.load_config()

        # Configure style for dark theme
        self.style = ttk.Style()
        self.style.theme_use('clam')

        # Configure dark red/black theme
        self.style.configure('Dark.TFrame', background='#1a1a1a')
        self.style.configure('Dark.TLabel', background='#1a1a1a', foreground='#ff4444')
        self.style.configure('Dark.TButton', background='#333333', foreground='#ff4444', borderwidth=1)
        self.style.map('Dark.TButton', background=[('active', '#ff4444'), ('pressed', '#cc3333')])
        self.style.configure('Dark.TEntry', background='#2d2d2d', foreground='#ffffff', borderwidth=1, insertcolor='#ff4444')

        self.setup_ui()

    def load_config(self):
        """Load configuration from config.json or create default config"""
        default_config = {
            "default_source_folder": "",
            "default_destination_folder": "",
            "last_extension": "",
            "last_rename_to": ""
        }

        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    return {**default_config, **config}
            except (json.JSONDecodeError, OSError):
                pass

        # Create default config file if it doesn't exist
        self.save_config(default_config)
        return default_config

    def save_config(self, config=None):
        """Save configuration to config.json"""
        if config is None:
            config = self.config

        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
        except OSError:
            pass

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, style='Dark.TFrame')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # Source Folder
        source_frame = ttk.Frame(main_frame, style='Dark.TFrame')
        source_frame.pack(fill='x', pady=(0, 10))

        ttk.Label(source_frame, text="Source Folder:", style='Dark.TLabel').pack(anchor='w')
        source_input_frame = tk.Frame(source_frame, bg='#1a1a1a')
        source_input_frame.pack(fill='x', pady=(5, 0))

        self.source_var = tk.StringVar(value=self.config.get("default_source_folder", ""))
        self.source_entry = tk.Entry(source_input_frame, textvariable=self.source_var, width=120,
                                   bg='#2d2d2d', fg='#ffffff', insertbackground='#ff4444', bd=1, relief='solid')
        self.source_entry.pack(side='left', fill='x', expand=True, padx=(0, 5))

        self.source_browse_btn = tk.Button(source_input_frame, text="...", command=self.browse_source,
                                         bg='#ff4444', fg='#ffffff', relief='raised', bd=2, width=3, height=1,
                                         font=('Arial', 12, 'bold'),
                                         activebackground='#cc3333', activeforeground='#ffffff')
        self.source_browse_btn.pack(side='right')

        # Destination Folder
        dest_frame = ttk.Frame(main_frame, style='Dark.TFrame')
        dest_frame.pack(fill='x', pady=(0, 10))

        ttk.Label(dest_frame, text="Destination Folder:", style='Dark.TLabel').pack(anchor='w')
        dest_input_frame = tk.Frame(dest_frame, bg='#1a1a1a')
        dest_input_frame.pack(fill='x', pady=(5, 0))

        self.dest_var = tk.StringVar(value=self.config.get("default_destination_folder", ""))
        self.dest_entry = tk.Entry(dest_input_frame, textvariable=self.dest_var, width=120,
                                 bg='#2d2d2d', fg='#ffffff', insertbackground='#ff4444', bd=1, relief='solid')
        self.dest_entry.pack(side='left', fill='x', expand=True, padx=(0, 5))

        self.dest_browse_btn = tk.Button(dest_input_frame, text="...", command=self.browse_destination,
                                       bg='#ff4444', fg='#ffffff', relief='raised', bd=2, width=3, height=1,
                                       font=('Arial', 12, 'bold'),
                                       activebackground='#cc3333', activeforeground='#ffffff')
        self.dest_browse_btn.pack(side='right')

        # Extension
        ext_frame = ttk.Frame(main_frame, style='Dark.TFrame')
        ext_frame.pack(fill='x', pady=(0, 10))

        ttk.Label(ext_frame, text="Extension:", style='Dark.TLabel').pack(anchor='w')
        self.ext_var = tk.StringVar(value=self.config.get("last_extension", ""))
        self.ext_var.trace_add('write', self.update_example)
        self.ext_entry = tk.Entry(ext_frame, textvariable=self.ext_var, width=150,
                                bg='#2d2d2d', fg='#ffffff', insertbackground='#ff4444', bd=1, relief='solid')
        self.ext_entry.pack(fill='x', pady=(5, 0))

        # Rename to
        rename_frame = ttk.Frame(main_frame, style='Dark.TFrame')
        rename_frame.pack(fill='x', pady=(0, 10))

        ttk.Label(rename_frame, text="Rename to: (Note: _######_ will be automatically added)", style='Dark.TLabel').pack(anchor='w')
        self.rename_var = tk.StringVar(value=self.config.get("last_rename_to", ""))
        self.rename_var.trace_add('write', self.update_example)
        self.rename_entry = tk.Entry(rename_frame, textvariable=self.rename_var, width=150,
                                   bg='#2d2d2d', fg='#ffffff', insertbackground='#ff4444', bd=1, relief='solid')
        self.rename_entry.pack(fill='x', pady=(5, 0))

        # Example label
        self.example_label = ttk.Label(rename_frame, text="", style='Dark.TLabel', font=('Arial', 9, 'italic'))
        self.example_label.pack(anchor='w', pady=(2, 0))
        self.update_example()

        # Move and Rename Button
        button_frame = ttk.Frame(main_frame, style='Dark.TFrame')
        button_frame.pack(fill='x', pady=(10, 20))

        self.move_button = tk.Button(button_frame, text="Move and Rename", command=self.move_and_rename,
                                   bg='#ff4444', fg='#ffffff', font=('Arial', 12, 'bold'),
                                   relief='raised', bd=2, padx=20, pady=10)
        self.move_button.pack(side='left', padx=(0, 10))

        self.settings_button = tk.Button(button_frame, text="Settings", command=self.open_settings,
                                       bg='#ff4444', fg='#ffffff', font=('Arial', 12, 'bold'),
                                       relief='raised', bd=2, padx=20, pady=10)
        self.settings_button.pack(side='left')

        # Status Listbox
        status_frame = ttk.Frame(main_frame, style='Dark.TFrame')
        status_frame.pack(fill='both', expand=True)

        ttk.Label(status_frame, text="Status:", style='Dark.TLabel').pack(anchor='w')

        # Create listbox with scrollbar
        listbox_frame = ttk.Frame(status_frame, style='Dark.TFrame')
        listbox_frame.pack(fill='both', expand=True, pady=(5, 0))

        self.status_listbox = tk.Listbox(listbox_frame, bg='#2d2d2d', fg='#ffffff',
                                       selectbackground='#ff4444', selectforeground='#ffffff',
                                       bd=1, relief='solid')
        self.status_listbox.pack(side='left', fill='both', expand=True)

        scrollbar = tk.Scrollbar(listbox_frame, bg='#333333', troughcolor='#1a1a1a')
        scrollbar.pack(side='right', fill='y')

        self.status_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.status_listbox.yview)

        # Initial status message
        self.add_status("Ready to move and rename files...")

    def browse_source(self):
        initial_dir = self.source_var.get() or self.config.get("default_source_folder", "")
        folder = filedialog.askdirectory(title="Select Source Folder", initialdir=initial_dir if initial_dir else None)
        if folder:
            self.source_var.set(folder)
            self.config["default_source_folder"] = folder
            self.save_config()
            self.add_status(f"Source folder selected: {folder}")

    def browse_destination(self):
        initial_dir = self.dest_var.get() or self.config.get("default_destination_folder", "")
        folder = filedialog.askdirectory(title="Select Destination Folder", initialdir=initial_dir if initial_dir else None)
        if folder:
            self.dest_var.set(folder)
            self.config["default_destination_folder"] = folder
            self.save_config()
            self.add_status(f"Destination folder selected: {folder}")

    def open_settings(self):
        """Open the settings dialog"""
        SettingsDialog(self.root, self)

    def update_example(self, *args):
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

    def add_status(self, message):
        self.status_listbox.insert(tk.END, message)
        self.status_listbox.see(tk.END)
        self.root.update_idletasks()

    def get_max_counter(self, dest_folder, base_name, extension):
        """Scan destination folder for existing files and find the highest counter"""
        max_counter = 0
        pattern = rf"{re.escape(base_name)}_(\d{{6}})_{re.escape(extension)}$"

        try:
            for filename in os.listdir(dest_folder):
                match = re.match(pattern, filename)
                if match:
                    counter = int(match.group(1))
                    max_counter = max(max_counter, counter)
        except OSError:
            pass

        return max_counter

    def move_and_rename(self):
        # Validate inputs
        source_folder = self.source_var.get().strip()
        dest_folder = self.dest_var.get().strip()
        extension = self.ext_var.get().strip()
        rename_to = self.rename_var.get().strip()

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

        # Ensure extension starts with a dot
        if not extension.startswith('.'):
            extension = '.' + extension

        # Check if source folder exists
        if not os.path.exists(source_folder):
            messagebox.showerror("Error", "Source folder does not exist")
            return

        # Create destination folder if it doesn't exist
        try:
            os.makedirs(dest_folder, exist_ok=True)
        except OSError as e:
            messagebox.showerror("Error", f"Cannot create destination folder: {e}")
            return

        self.add_status("Starting move and rename operation...")

        # Get files with the specified extension
        source_files = []
        try:
            for filename in os.listdir(source_folder):
                if filename.lower().endswith(extension.lower()):
                    source_files.append(filename)
        except OSError as e:
            messagebox.showerror("Error", f"Cannot read source folder: {e}")
            return

        if not source_files:
            self.add_status(f"No files found with extension '{extension}' in source folder")
            return

        self.add_status(f"Found {len(source_files)} files with extension '{extension}'")

        # Get the maximum counter from existing files in destination
        max_counter = self.get_max_counter(dest_folder, rename_to, extension)
        self.add_status(f"Starting counter from: {max_counter + 1:06d}")

        # Process files
        counter = max_counter + 1
        success_count = 0
        error_count = 0

        for filename in source_files:
            source_path = os.path.join(source_folder, filename)
            new_filename = f"{rename_to}_{counter:06d}_{extension}"
            dest_path = os.path.join(dest_folder, new_filename)

            try:
                shutil.move(source_path, dest_path)
                self.add_status(f"Moved: {filename} → {new_filename}")
                success_count += 1
                counter += 1
            except Exception as e:
                self.add_status(f"Error moving {filename}: {e}")
                error_count += 1

        # Final status
        self.add_status(f"Operation completed: {success_count} files moved, {error_count} errors")

        # Save the extension and rename pattern for next time
        self.config["last_extension"] = extension
        self.config["last_rename_to"] = rename_to
        self.save_config()

        if error_count == 0:
            messagebox.showinfo("Success", f"Successfully moved and renamed {success_count} files")
        else:
            messagebox.showwarning("Completed with errors",
                                 f"Moved {success_count} files with {error_count} errors. Check status for details.")

class SettingsDialog:
    def __init__(self, parent, app):
        self.app = app
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Settings")
        self.dialog.geometry("700x300")
        self.dialog.configure(bg='#1a1a1a')
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.setup_ui()

    def setup_ui(self):
        main_frame = ttk.Frame(self.dialog, style='Dark.TFrame')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # Title
        title_label = ttk.Label(main_frame, text="Default Folder Settings",
                               style='Dark.TLabel', font=('Arial', 14, 'bold'))
        title_label.pack(anchor='w', pady=(0, 20))

        # Default Source Folder
        source_frame = ttk.Frame(main_frame, style='Dark.TFrame')
        source_frame.pack(fill='x', pady=(0, 15))

        ttk.Label(source_frame, text="Default Source Folder:", style='Dark.TLabel').pack(anchor='w')
        source_input_frame = tk.Frame(source_frame, bg='#1a1a1a')
        source_input_frame.pack(fill='x', pady=(5, 0))

        self.source_var = tk.StringVar(value=self.app.config.get("default_source_folder", ""))
        self.source_entry = tk.Entry(source_input_frame, textvariable=self.source_var,
                                   bg='#2d2d2d', fg='#ffffff', insertbackground='#ff4444', bd=1, relief='solid')
        self.source_entry.pack(side='left', fill='x', expand=True, padx=(0, 5))

        self.source_browse_btn = tk.Button(source_input_frame, text="...", command=self.browse_source,
                                         bg='#ff4444', fg='#ffffff', relief='raised', bd=2, width=3, height=1,
                                         font=('Arial', 12, 'bold'),
                                         activebackground='#cc3333', activeforeground='#ffffff')
        self.source_browse_btn.pack(side='right')

        # Default Destination Folder
        dest_frame = ttk.Frame(main_frame, style='Dark.TFrame')
        dest_frame.pack(fill='x', pady=(0, 15))

        ttk.Label(dest_frame, text="Default Destination Folder:", style='Dark.TLabel').pack(anchor='w')
        dest_input_frame = tk.Frame(dest_frame, bg='#1a1a1a')
        dest_input_frame.pack(fill='x', pady=(5, 0))

        self.dest_var = tk.StringVar(value=self.app.config.get("default_destination_folder", ""))
        self.dest_entry = tk.Entry(dest_input_frame, textvariable=self.dest_var,
                                 bg='#2d2d2d', fg='#ffffff', insertbackground='#ff4444', bd=1, relief='solid')
        self.dest_entry.pack(side='left', fill='x', expand=True, padx=(0, 5))

        self.dest_browse_btn = tk.Button(dest_input_frame, text="...", command=self.browse_destination,
                                       bg='#ff4444', fg='#ffffff', relief='raised', bd=2, width=3, height=1,
                                       font=('Arial', 12, 'bold'),
                                       activebackground='#cc3333', activeforeground='#ffffff')
        self.dest_browse_btn.pack(side='right')

        # Buttons
        button_frame = ttk.Frame(main_frame, style='Dark.TFrame')
        button_frame.pack(fill='x', pady=(20, 0))

        self.save_button = tk.Button(button_frame, text="Save", command=self.save_settings,
                                   bg='#ff4444', fg='#ffffff', font=('Arial', 12, 'bold'),
                                   relief='raised', bd=2, padx=20, pady=10)
        self.save_button.pack(side='left', padx=(0, 10))

        self.cancel_button = tk.Button(button_frame, text="Cancel", command=self.dialog.destroy,
                                     bg='#ff4444', fg='#ffffff', font=('Arial', 12, 'bold'),
                                     relief='raised', bd=2, padx=20, pady=10)
        self.cancel_button.pack(side='left')

    def browse_source(self):
        initial_dir = self.source_var.get() or None
        folder = filedialog.askdirectory(title="Select Default Source Folder", initialdir=initial_dir)
        if folder:
            self.source_var.set(folder)

    def browse_destination(self):
        initial_dir = self.dest_var.get() or None
        folder = filedialog.askdirectory(title="Select Default Destination Folder", initialdir=initial_dir)
        if folder:
            self.dest_var.set(folder)

    def save_settings(self):
        # Update config
        self.app.config["default_source_folder"] = self.source_var.get()
        self.app.config["default_destination_folder"] = self.dest_var.get()
        self.app.save_config()

        # Update main form fields
        self.app.source_var.set(self.source_var.get())
        self.app.dest_var.set(self.dest_var.get())

        messagebox.showinfo("Settings Saved", "Default folders have been updated successfully!")
        self.dialog.destroy()

def main():
    root = tk.Tk()
    app = FileRenameMover(root)
    root.mainloop()

if __name__ == "__main__":
    main()