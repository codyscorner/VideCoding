"""Dark green theme styling for File Hash Dedupe"""

import tkinter as tk
from tkinter import ttk


class ThemeManager:
    """Manages the dark green theme for the application"""

    # Dark green color scheme
    COLORS = {
        'bg_dark': '#0d1f0d',           # Very dark green background
        'bg_medium': '#1a3a1a',         # Medium dark green
        'bg_light': '#2d4a2d',          # Lighter green for inputs
        'bg_highlight': '#3d5a3d',      # Highlight/hover green
        'fg_primary': '#e0f0e0',        # Light green-white text
        'fg_secondary': '#a0c0a0',      # Muted green text
        'fg_dim': '#708070',            # Dimmed text
        'accent': '#50a050',            # Bright green accent
        'accent_hover': '#60b060',      # Hover state
        'accent_dark': '#306030',       # Darker accent
        'border': '#3a5a3a',            # Border color
        'error': '#ff6b6b',             # Error red
        'success': '#7ddc7d',           # Success bright green
        'progress_bg': '#1a3a1a',       # Progress bar background
        'progress_fg': '#50a050',       # Progress bar foreground
    }

    @classmethod
    def apply_theme(cls, root: tk.Tk) -> None:
        """Apply the dark green theme to the application"""
        style = ttk.Style()

        # Configure the theme
        root.configure(bg=cls.COLORS['bg_dark'])

        # Configure ttk styles
        style.configure(
            'TFrame',
            background=cls.COLORS['bg_dark']
        )

        style.configure(
            'TLabel',
            background=cls.COLORS['bg_dark'],
            foreground=cls.COLORS['fg_primary'],
            font=('Segoe UI', 10)
        )

        style.configure(
            'Header.TLabel',
            background=cls.COLORS['bg_dark'],
            foreground=cls.COLORS['accent'],
            font=('Segoe UI', 12, 'bold')
        )

        style.configure(
            'TButton',
            background=cls.COLORS['accent'],
            foreground=cls.COLORS['fg_primary'],
            font=('Segoe UI', 10, 'bold'),
            padding=(20, 10)
        )

        style.map(
            'TButton',
            background=[
                ('active', cls.COLORS['accent_hover']),
                ('disabled', cls.COLORS['bg_light'])
            ],
            foreground=[
                ('disabled', cls.COLORS['fg_dim'])
            ]
        )

        # Action button (primary action)
        style.configure(
            'Action.TButton',
            background=cls.COLORS['accent'],
            foreground='white',
            font=('Segoe UI', 11, 'bold'),
            padding=(30, 12)
        )

        style.map(
            'Action.TButton',
            background=[
                ('active', cls.COLORS['accent_hover']),
                ('disabled', cls.COLORS['bg_light'])
            ],
            foreground=[
                ('disabled', cls.COLORS['fg_dim'])
            ]
        )

        # Cancel button
        style.configure(
            'Cancel.TButton',
            background=cls.COLORS['accent_dark'],
            foreground=cls.COLORS['fg_primary'],
            font=('Segoe UI', 11, 'bold'),
            padding=(30, 12)
        )

        style.map(
            'Cancel.TButton',
            background=[
                ('active', cls.COLORS['error']),
                ('disabled', cls.COLORS['bg_light'])
            ],
            foreground=[
                ('disabled', cls.COLORS['fg_dim'])
            ]
        )

        style.configure(
            'TEntry',
            fieldbackground=cls.COLORS['bg_light'],
            foreground=cls.COLORS['fg_primary'],
            insertcolor=cls.COLORS['fg_primary'],
            padding=8
        )

        style.configure(
            'TCheckbutton',
            background=cls.COLORS['bg_dark'],
            foreground=cls.COLORS['fg_primary'],
            font=('Segoe UI', 10)
        )

        style.map(
            'TCheckbutton',
            background=[('active', cls.COLORS['bg_dark'])]
        )

        # Progress bar
        style.configure(
            'green.Horizontal.TProgressbar',
            troughcolor=cls.COLORS['progress_bg'],
            background=cls.COLORS['progress_fg'],
            darkcolor=cls.COLORS['accent'],
            lightcolor=cls.COLORS['accent_hover'],
            bordercolor=cls.COLORS['border'],
            thickness=25
        )

        # Labelframe
        style.configure(
            'TLabelframe',
            background=cls.COLORS['bg_dark'],
            foreground=cls.COLORS['fg_primary'],
            bordercolor=cls.COLORS['border']
        )

        style.configure(
            'TLabelframe.Label',
            background=cls.COLORS['bg_dark'],
            foreground=cls.COLORS['accent'],
            font=('Segoe UI', 10, 'bold')
        )

    @classmethod
    def style_entry(cls, entry: tk.Entry) -> None:
        """Apply theme to a tk.Entry widget"""
        entry.configure(
            bg=cls.COLORS['bg_light'],
            fg=cls.COLORS['fg_primary'],
            insertbackground=cls.COLORS['fg_primary'],
            relief='flat',
            font=('Segoe UI', 10)
        )

    @classmethod
    def style_listbox(cls, listbox: tk.Listbox) -> None:
        """Apply theme to a tk.Listbox widget"""
        listbox.configure(
            bg=cls.COLORS['bg_medium'],
            fg=cls.COLORS['fg_primary'],
            selectbackground=cls.COLORS['accent'],
            selectforeground='white',
            relief='flat',
            font=('Consolas', 9),
            highlightthickness=1,
            highlightbackground=cls.COLORS['border'],
            highlightcolor=cls.COLORS['accent']
        )

    @classmethod
    def style_scrollbar(cls, scrollbar: tk.Scrollbar) -> None:
        """Apply theme to a tk.Scrollbar widget"""
        scrollbar.configure(
            bg=cls.COLORS['bg_light'],
            troughcolor=cls.COLORS['bg_medium'],
            activebackground=cls.COLORS['accent'],
            highlightthickness=0
        )
