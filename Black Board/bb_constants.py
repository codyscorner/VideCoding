from enum import Enum, auto
from PyQt6.QtGui import QColor

# ── Palette ───────────────────────────────────────────────────────────────────
BACKGROUND    = QColor(25, 25, 25)
GRID_MINOR    = QColor(40, 40, 40)
GRID_MAJOR    = QColor(55, 55, 55)
NODE_BODY     = QColor(45, 45, 58)
NODE_HEADER   = QColor(60, 60, 80)
NODE_BORDER   = QColor(120, 120, 160)
NODE_SELECTED = QColor(100, 160, 255)
PORT_SOURCE   = QColor(80, 200, 120)
PORT_TARGET   = QColor(200, 100, 80)
TEXT_COLOR    = QColor(220, 220, 220)
NOTE_COLOR    = QColor(60, 58, 30)
NOTE_BORDER   = QColor(180, 170, 80)
DEFAULT_DRAW_COLOR = QColor("#C8C8FF")

PALETTE_16 = [
    ("#FFFFFF", "White"),   ("#C8C8FF", "Lavender"), ("#64C896", "Green"),
    ("#C86464", "Red"),     ("#6496C8", "Blue"),      ("#C8A050", "Amber"),
    ("#A050C8", "Purple"),  ("#50C8C8", "Cyan"),      ("#C87850", "Orange"),
    ("#78C850", "Lime"),    ("#C85078", "Pink"),       ("#5078C8", "Indigo"),
    ("#C8C850", "Yellow"),  ("#888888", "Gray"),       ("#444444", "Dark"),
    ("#F0F0F0", "Silver"),
]

THICKNESS_LEVELS = [1, 3, 6]   # Thin / Medium / Thick

GRID_MINOR_SIZE = 20
GRID_MAJOR_MULT = 5
PORT_RADIUS     = 6
NODE_WIDTH      = 180
NODE_HEADER_H   = 28
ROW_H           = 22


class Tool(Enum):
    SELECT        = auto()
    PAN           = auto()
    PEN           = auto()
    RECT          = auto()
    ELLIPSE       = auto()
    ARROW         = auto()
    TEXT          = auto()
    NODE_TABLE    = auto()
    NODE_DECISION = auto()
    NODE_PROC     = auto()
    NODE_API      = auto()
    NODE_NOTE     = auto()
    NODE_GENERIC  = auto()
