"""Crimson Slate theme for Image People Sorter"""

from tkinter import ttk
from typing import Dict, Any


class CrimsonSlateTheme:
    """Crimson Slate color scheme - dark maroon/red background with lighter accents"""

    # Color definitions
    COLORS = {
        # Backgrounds - Dark Red/Maroon tones
        'bg_main': '#2D0A0A',           # Deep Maroon - main app background
        'bg_surface': '#3D1515',        # Slightly lighter maroon - form containers & cards
        'bg_input': '#1A0505',          # Very dark red for input fields (contrast)

        # Primary action colors
        'button_bg': '#D32F2F',         # Sharp Red - primary action button
        'button_fg': '#FFFFFF',         # Pure White - button text
        'button_hover': '#FF5252',      # Brighter red for hover

        # Borders and accents
        'border': '#5C1A1A',            # Medium maroon - form input borders
        'accent': '#FF6B6B',            # Bright coral - accent/highlights
        'accent_dim': '#4A1212',        # Darker maroon for disabled states

        # Text colors
        'text_primary': '#FFFFFF',      # White text
        'text_secondary': '#FFCCCC',    # Light pink/red tinted text
        'text_muted': '#AA7777',        # Muted red-grey text

        # Status colors
        'success': '#4CAF50',           # Green for success
        'warning': '#FF9800',           # Orange for warnings
        'error': '#FF5252',             # Coral red for errors

        # Progress bar
        'progress_bg': '#1A0505',       # Dark red trough
        'progress_fill': '#D32F2F',     # Bright red fill

        # Input fields
        'input_bg': '#1A0505',          # Very dark red
        'input_fg': '#FFFFFF',          # White text
        'insert_cursor': '#FF6B6B',     # Coral cursor
    }

    # Font definitions
    FONTS = {
        'default': ('Segoe UI', 10),
        'heading': ('Segoe UI', 12, 'bold'),
        'button': ('Segoe UI', 11, 'bold'),
        'small': ('Segoe UI', 9),
        'italic': ('Segoe UI', 9, 'italic'),
        'mono': ('Consolas', 10),
    }

    def __init__(self, style: ttk.Style):
        """
        Initialize and apply the Crimson Slate theme

        Args:
            style: ttk.Style instance to configure
        """
        self.style = style
        self._configure_theme()

    def _configure_theme(self) -> None:
        """Configure all ttk styles for Crimson Slate theme"""
        # Configure base theme
        self.style.theme_use('clam')

        # Frame styles
        self.style.configure(
            'Dark.TFrame',
            background=self.COLORS['bg_main']
        )

        self.style.configure(
            'Surface.TFrame',
            background=self.COLORS['bg_surface']
        )

        # Label styles
        self.style.configure(
            'Dark.TLabel',
            background=self.COLORS['bg_main'],
            foreground=self.COLORS['text_primary'],
            font=self.FONTS['default']
        )

        self.style.configure(
            'Surface.TLabel',
            background=self.COLORS['bg_surface'],
            foreground=self.COLORS['text_primary'],
            font=self.FONTS['default']
        )

        self.style.configure(
            'Heading.TLabel',
            background=self.COLORS['bg_main'],
            foreground=self.COLORS['accent'],
            font=self.FONTS['heading']
        )

        # Checkbutton styles
        self.style.configure(
            'Dark.TCheckbutton',
            background=self.COLORS['bg_main'],
            foreground=self.COLORS['text_primary'],
            font=self.FONTS['default']
        )
        self.style.map(
            'Dark.TCheckbutton',
            background=[('active', self.COLORS['bg_main'])],
            foreground=[('active', self.COLORS['accent'])]
        )

        # Radiobutton styles
        self.style.configure(
            'Dark.TRadiobutton',
            background=self.COLORS['bg_main'],
            foreground=self.COLORS['text_primary'],
            font=self.FONTS['default']
        )
        self.style.map(
            'Dark.TRadiobutton',
            background=[('active', self.COLORS['bg_main'])],
            foreground=[('active', self.COLORS['accent'])]
        )

        # Progress bar style
        self.style.configure(
            'Crimson.Horizontal.TProgressbar',
            troughcolor=self.COLORS['progress_bg'],
            background=self.COLORS['progress_fill'],
            darkcolor=self.COLORS['progress_fill'],
            lightcolor=self.COLORS['accent'],
            bordercolor=self.COLORS['border'],
            thickness=20
        )

        # Entry style (limited ttk support, mainly use tk.Entry)
        self.style.configure(
            'Dark.TEntry',
            fieldbackground=self.COLORS['input_bg'],
            foreground=self.COLORS['input_fg'],
            insertcolor=self.COLORS['insert_cursor'],
            bordercolor=self.COLORS['border']
        )

        # Combobox style
        self.style.configure(
            'Dark.TCombobox',
            fieldbackground=self.COLORS['input_bg'],
            background=self.COLORS['bg_surface'],
            foreground=self.COLORS['input_fg'],
            arrowcolor=self.COLORS['accent'],
            bordercolor=self.COLORS['border']
        )
        self.style.map(
            'Dark.TCombobox',
            fieldbackground=[('readonly', self.COLORS['input_bg'])],
            selectbackground=[('readonly', self.COLORS['button_bg'])],
            selectforeground=[('readonly', self.COLORS['button_fg'])]
        )

        # Scrollbar style
        self.style.configure(
            'Dark.Vertical.TScrollbar',
            background=self.COLORS['bg_surface'],
            troughcolor=self.COLORS['bg_main'],
            bordercolor=self.COLORS['border'],
            arrowcolor=self.COLORS['accent']
        )

    def get_color(self, name: str) -> str:
        """Get a color by name"""
        return self.COLORS.get(name, '#FFFFFF')

    def get_font(self, name: str) -> tuple:
        """Get a font by name"""
        return self.FONTS.get(name, self.FONTS['default'])

    def get_all_colors(self) -> Dict[str, str]:
        """Get all colors"""
        return self.COLORS.copy()

    def get_all_fonts(self) -> Dict[str, tuple]:
        """Get all fonts"""
        return self.FONTS.copy()


class ThemeManager:
    """Theme manager for the application"""

    THEMES = {
        'crimson_slate': CrimsonSlateTheme,
    }

    def __init__(self, style: ttk.Style, theme_name: str = 'crimson_slate'):
        """
        Initialize theme manager

        Args:
            style: ttk.Style instance
            theme_name: Name of theme to use
        """
        theme_class = self.THEMES.get(theme_name, CrimsonSlateTheme)
        self.theme = theme_class(style)

    def get_color(self, name: str) -> str:
        """Get a color by name"""
        return self.theme.get_color(name)

    def get_font(self, name: str) -> tuple:
        """Get a font by name"""
        return self.theme.get_font(name)

    def get_all_colors(self) -> Dict[str, str]:
        """Get all colors"""
        return self.theme.get_all_colors()

    def get_all_fonts(self) -> Dict[str, tuple]:
        """Get all fonts"""
        return self.theme.get_all_fonts()
