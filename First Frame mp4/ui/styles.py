"""Theme and styling management for Frame Extractor application"""

from tkinter import ttk
from typing import Dict, Any, Optional


class Theme:
    """Base theme class"""

    def __init__(self):
        self.colors = {}
        self.fonts = {}

    def apply_to_style(self, style: ttk.Style) -> None:
        """Apply theme to ttk.Style object"""
        raise NotImplementedError


class OrangeBlackTheme(Theme):
    """Orange and black theme for Frame Extractor"""

    def __init__(self):
        super().__init__()
        self.colors = {
            'background': '#1a1a1a',  # Black
            'foreground': '#FFA500',  # Orange
            'input_bg': '#2d2d2d',   # Dark gray
            'input_fg': '#FF8C00',   # Dark orange
            'button_bg': '#FFA500',  # Orange
            'button_fg': '#000000',  # Black text
            'button_active': '#FF8C00',  # Dark orange
            'button_hover': '#FFB732',  # Light orange
            'accent': '#333333',
            'insert_cursor': '#FFA500',
            'select_bg': '#FFA500',
            'select_fg': '#000000',
            'scrollbar_bg': '#333333',
            'scrollbar_trough': '#1a1a1a'
        }

        self.fonts = {
            'default': ('Arial', 10),
            'bold': ('Arial', 10, 'bold'),
            'title': ('Arial', 16, 'bold'),
            'italic': ('Arial', 9, 'italic'),
            'button': ('Arial', 10, 'bold')
        }

    def apply_to_style(self, style: ttk.Style) -> None:
        """Apply orange/black theme to ttk.Style"""
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
            borderwidth=1,
            font=self.fonts['button']
        )
        style.map(
            'Dark.TButton',
            background=[
                ('active', self.colors['button_hover']),
                ('pressed', self.colors['button_active'])
            ]
        )

        # Entry
        style.configure(
            'Dark.TEntry',
            fieldbackground=self.colors['input_bg'],
            foreground=self.colors['input_fg'],
            background=self.colors['input_bg'],
            borderwidth=1,
            insertcolor=self.colors['insert_cursor']
        )

        # Combobox
        style.configure(
            'Dark.TCombobox',
            fieldbackground=self.colors['input_bg'],
            background=self.colors['accent'],
            foreground=self.colors['input_fg'],
            arrowcolor=self.colors['foreground'],
            borderwidth=1
        )
        style.map(
            'Dark.TCombobox',
            fieldbackground=[('readonly', self.colors['input_bg'])],
            selectbackground=[('readonly', self.colors['select_bg'])],
            selectforeground=[('readonly', self.colors['select_fg'])]
        )

        # Scrollbar
        style.configure(
            'Dark.Vertical.TScrollbar',
            background=self.colors['scrollbar_bg'],
            troughcolor=self.colors['scrollbar_trough'],
            arrowcolor=self.colors['foreground'],
            bordercolor=self.colors['scrollbar_bg']
        )

class ThemeManager:
    """Manages application themes"""

    THEMES = {
        'orange_black': OrangeBlackTheme,
    }

    def __init__(self, style: ttk.Style, theme_name: str = 'orange_black'):
        """
        Initialize theme manager

        Args:
            style: ttk.Style object to apply theme to
            theme_name: Name of theme to use
        """
        self.style = style
        self.current_theme: 'Theme' = Theme()
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
