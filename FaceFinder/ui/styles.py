"""Theme and styling management for FaceFinder application"""

from tkinter import ttk
from typing import Dict


class Theme:
    """Base theme class"""

    def __init__(self):
        self.colors = {}
        self.fonts = {}

    def apply_to_style(self, style: ttk.Style) -> None:
        """Apply theme to ttk.Style object"""
        raise NotImplementedError


class YellowBlackTheme(Theme):
    """Yellow and black theme for FaceFinder"""

    def __init__(self):
        super().__init__()
        self.colors = {
            'background': '#1a1a1a',
            'foreground': '#FFD700',
            'input_bg': '#2d2d2d',
            'input_fg': '#FFFF00',
            'button_bg': '#FFD700',
            'button_fg': '#000000',
            'button_active': '#FFA500',
            'button_hover': '#FFED4E',
            'accent': '#333333',
            'insert_cursor': '#FFD700',
            'select_bg': '#FFD700',
            'select_fg': '#000000',
            'scrollbar_bg': '#333333',
            'scrollbar_trough': '#1a1a1a',
            'success': '#00FF00',
            'error': '#FF4444'
        }

        self.fonts = {
            'default': ('Arial', 10),
            'bold': ('Arial', 12, 'bold'),
            'title': ('Arial', 14, 'bold'),
            'italic': ('Arial', 9, 'italic'),
            'button': ('Arial', 12, 'bold')
        }

    def apply_to_style(self, style: ttk.Style) -> None:
        """Apply yellow/black theme to ttk.Style"""
        style.theme_use('clam')

        # Frame
        style.configure(
            'Dark.TFrame',
            background=self.colors['background']
        )

        # Label
        style.configure(
            'Dark.TLabel',
            background=self.colors['background'],
            foreground=self.colors['foreground']
        )

        # Button
        style.configure(
            'Dark.TButton',
            background=self.colors['accent'],
            foreground=self.colors['foreground'],
            borderwidth=1
        )
        style.map(
            'Dark.TButton',
            background=[
                ('active', self.colors['button_hover']),
                ('pressed', self.colors['button_active'])
            ]
        )

        # Progress bar - Yellow/Gold style
        style.configure(
            'Yellow.Horizontal.TProgressbar',
            troughcolor='#333333',
            background=self.colors['foreground'],
            lightcolor=self.colors['button_hover'],
            darkcolor='#B8860B',
            bordercolor='#FFD700',
            thickness=20
        )

        # Scale (slider)
        style.configure(
            'Dark.Horizontal.TScale',
            background=self.colors['background'],
            troughcolor='#333333'
        )


class ThemeManager:
    """Manages application themes"""

    THEMES = {
        'yellow_black': YellowBlackTheme,
    }

    def __init__(self, style: ttk.Style, theme_name: str = 'yellow_black'):
        """
        Initialize theme manager

        Args:
            style: ttk.Style object to apply theme to
            theme_name: Name of theme to use
        """
        self.style = style
        self.current_theme = None
        self.set_theme(theme_name)

    def set_theme(self, theme_name: str) -> None:
        """
        Set the current theme

        Args:
            theme_name: Name of theme to apply

        Raises:
            ValueError: If theme doesn't exist
        """
        if theme_name not in self.THEMES:
            raise ValueError(f"Theme '{theme_name}' not found")

        theme_class = self.THEMES[theme_name]
        self.current_theme = theme_class()
        self.current_theme.apply_to_style(self.style)

    def get_color(self, color_name: str) -> str:
        """
        Get a color value from current theme

        Args:
            color_name: Name of color

        Returns:
            Color hex code
        """
        return self.current_theme.colors.get(color_name, '#000000')

    def get_font(self, font_name: str) -> tuple:
        """
        Get a font tuple from current theme

        Args:
            font_name: Name of font

        Returns:
            Font tuple (family, size, style)
        """
        return self.current_theme.fonts.get(font_name, ('Arial', 10))

    def get_all_colors(self) -> Dict[str, str]:
        """Get all colors from current theme"""
        return self.current_theme.colors.copy()

    def get_all_fonts(self) -> Dict[str, tuple]:
        """Get all fonts from current theme"""
        return self.current_theme.fonts.copy()
