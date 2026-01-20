"""Results viewer dialog with thumbnail grid for FaceFinder"""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import List, Optional, Dict
import subprocess
from PIL import Image, ImageTk


class ResultsViewer(tk.Toplevel):
    """Dialog window showing matched images as thumbnails in a grid"""

    THUMBNAIL_SIZE = 150
    GRID_PADDING = 10

    def __init__(self, parent: tk.Tk, matches: List[str], colors: Dict):
        """
        Initialize results viewer

        Args:
            parent: Parent window
            matches: List of matched image file paths
            colors: Theme colors dictionary
        """
        super().__init__(parent)
        self.matches = matches
        self.colors = colors
        self._thumbnail_cache: Dict[str, ImageTk.PhotoImage] = {}
        self._image_refs: List[ImageTk.PhotoImage] = []  # Keep references to prevent GC

        self._setup_window()
        self._create_ui()
        self._load_thumbnails()

    def _setup_window(self) -> None:
        """Configure the dialog window"""
        self.title(f"Match Results - {len(self.matches)} images found")
        self.geometry("800x600")
        self.minsize(600, 400)
        self.configure(bg=self.colors['background'])

        # Make it modal
        self.transient(self.master)
        self.grab_set()

    def _create_ui(self) -> None:
        """Create the UI components"""
        # Main frame
        main_frame = tk.Frame(self, bg=self.colors['background'])
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Header
        header = tk.Label(
            main_frame,
            text=f"Found {len(self.matches)} matching images",
            bg=self.colors['background'],
            fg=self.colors['foreground'],
            font=('Segoe UI', 12, 'bold')
        )
        header.pack(anchor='w', pady=(0, 5))

        hint = tk.Label(
            main_frame,
            text="Double-click an image to open its location in Explorer",
            bg=self.colors['background'],
            fg='#888888',
            font=('Segoe UI', 9, 'italic')
        )
        hint.pack(anchor='w', pady=(0, 10))

        # Scrollable canvas for thumbnail grid
        canvas_frame = tk.Frame(main_frame, bg=self.colors['background'])
        canvas_frame.pack(fill='both', expand=True)

        self.canvas = tk.Canvas(
            canvas_frame,
            bg=self.colors['input_bg'],
            highlightthickness=0
        )
        self.canvas.pack(side='left', fill='both', expand=True)

        # Scrollbar
        scrollbar = tk.Scrollbar(
            canvas_frame,
            orient='vertical',
            command=self.canvas.yview,
            bg=self.colors.get('scrollbar_bg', '#333333'),
            troughcolor=self.colors.get('scrollbar_trough', '#1a1a1a')
        )
        scrollbar.pack(side='right', fill='y')
        self.canvas.configure(yscrollcommand=scrollbar.set)

        # Frame inside canvas for thumbnails
        self.grid_frame = tk.Frame(self.canvas, bg=self.colors['input_bg'])
        self.canvas_window = self.canvas.create_window(
            (0, 0),
            window=self.grid_frame,
            anchor='nw'
        )

        # Bind events
        self.grid_frame.bind('<Configure>', self._on_frame_configure)
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        self.canvas.bind_all('<MouseWheel>', self._on_mousewheel)

        # Close button
        close_btn = tk.Button(
            main_frame,
            text="Close",
            command=self.destroy,
            bg=self.colors['button_bg'],
            fg=self.colors['button_fg'],
            font=('Segoe UI', 10),
            padx=20,
            pady=5
        )
        close_btn.pack(pady=(10, 0))

    def _on_frame_configure(self, event) -> None:
        """Update scroll region when frame size changes"""
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def _on_canvas_configure(self, event) -> None:
        """Resize frame when canvas size changes"""
        # Recalculate grid layout
        self._layout_thumbnails()

    def _on_mousewheel(self, event) -> None:
        """Handle mouse wheel scrolling"""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')

    def _load_thumbnails(self) -> None:
        """Load and display all thumbnails"""
        for path in self.matches:
            self._create_thumbnail_widget(path)
        self._layout_thumbnails()

    def _create_thumbnail_widget(self, path: str) -> None:
        """Create a thumbnail widget for an image"""
        # Create frame for thumbnail + label
        item_frame = tk.Frame(
            self.grid_frame,
            bg=self.colors['input_bg'],
            padx=5,
            pady=5
        )
        item_frame.image_path = path  # Store path for later

        # Load and resize image
        try:
            img = Image.open(path)
            img.thumbnail((self.THUMBNAIL_SIZE, self.THUMBNAIL_SIZE), Image.LANCZOS)

            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(img)
            self._image_refs.append(photo)  # Keep reference

            # Image label
            img_label = tk.Label(
                item_frame,
                image=photo,
                bg=self.colors['input_bg'],
                cursor='hand2'
            )
            img_label.image = photo  # Keep reference
            img_label.pack()

        except Exception as e:
            # Show placeholder for failed images
            img_label = tk.Label(
                item_frame,
                text="[Error]",
                width=15,
                height=8,
                bg='#333333',
                fg='#ff6666'
            )
            img_label.pack()

        # Filename label
        filename = Path(path).name
        if len(filename) > 25:
            filename = filename[:22] + "..."

        name_label = tk.Label(
            item_frame,
            text=filename,
            bg=self.colors['input_bg'],
            fg=self.colors['foreground'],
            font=('Segoe UI', 8),
            wraplength=self.THUMBNAIL_SIZE
        )
        name_label.pack()

        # Bind double-click to open Explorer
        for widget in [item_frame, img_label, name_label]:
            widget.bind('<Double-Button-1>', lambda e, p=path: self._open_in_explorer(p))
            widget.bind('<Enter>', lambda e, f=item_frame: self._on_hover(f, True))
            widget.bind('<Leave>', lambda e, f=item_frame: self._on_hover(f, False))

        item_frame.pack_forget()  # Will be positioned by _layout_thumbnails

    def _layout_thumbnails(self) -> None:
        """Arrange thumbnails in a grid based on current window width"""
        # Get canvas width
        self.update_idletasks()
        canvas_width = self.canvas.winfo_width()
        if canvas_width < 100:
            canvas_width = 780  # Default

        # Calculate columns that fit
        item_width = self.THUMBNAIL_SIZE + self.GRID_PADDING * 2
        cols = max(1, canvas_width // item_width)

        # Position all items
        row = 0
        col = 0
        for child in self.grid_frame.winfo_children():
            child.grid(row=row, column=col, padx=5, pady=5)
            col += 1
            if col >= cols:
                col = 0
                row += 1

    def _on_hover(self, frame: tk.Frame, entering: bool) -> None:
        """Handle mouse hover effect"""
        if entering:
            frame.configure(bg=self.colors.get('select_bg', '#444444'))
            for child in frame.winfo_children():
                if isinstance(child, tk.Label):
                    child.configure(bg=self.colors.get('select_bg', '#444444'))
        else:
            frame.configure(bg=self.colors['input_bg'])
            for child in frame.winfo_children():
                if isinstance(child, tk.Label):
                    child.configure(bg=self.colors['input_bg'])

    def _open_in_explorer(self, path: str) -> None:
        """Open file location in Explorer"""
        if Path(path).exists():
            subprocess.Popen(['explorer', '/select,', path])
