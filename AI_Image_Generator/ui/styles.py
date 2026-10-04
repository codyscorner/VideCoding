"""Colours and the extra stylesheet rules the RunPod modules need.

pod_control.py and settings_dialog.py were copied from the ComfyUI Video
Creator / Style Randomizer, which look colours up by name in COLORS. This maps
those names onto AI Image Studio's own purple theme, so the copied files work
unchanged and still match the rest of the app.
"""

BG      = "#13131f"
BG_MED  = "#1c1c2e"
BG_LT   = "#252540"
ACCENT  = "#6c5ce7"
ACCENT2 = "#7d6ff0"
FG      = "#e0e0f0"
FG_DIM  = "#7070a0"
BORDER  = "#2e2e50"
SUCCESS = "#4caf8a"
ERROR   = "#ff6b6b"
WARNING = "#ffb74d"

COLORS = {
    "bg_dark":      BG,
    "bg_medium":    BG_MED,
    "bg_light":     BG_LT,
    "bg_input":     BG_LT,
    "fg_primary":   FG,
    "fg_secondary": "#a0a0c8",
    "fg_dim":       FG_DIM,
    "accent":       ACCENT,
    "accent_hover": ACCENT2,
    "accent_dark":  "#4a3db8",
    "border":       BORDER,
    "success":      SUCCESS,
    "error":        ERROR,
    "warning":      WARNING,
}

# Appended to the main STYLESHEET: object names the copied pod / settings code
# uses, plus widgets the Settings dialog has that the tabs never did.
POD_QSS = f"""
    QLabel#subtitle {{ color: {COLORS['fg_secondary']}; font-size: 9pt; }}
    QLabel#status_dim {{ color: {COLORS['fg_secondary']}; font-size: 9pt; }}
    QLabel#mode_badge {{ color: {FG}; font-weight: bold; }}
    QPushButton#small_btn {{
        background-color: {BG_LT};
        color: {FG};
        border: 1px solid {BORDER};
        padding: 5px 10px;
        font-size: 9pt;
        font-weight: normal;
    }}
    QPushButton#small_btn:hover {{ background-color: {BG_MED}; border: 1px solid {ACCENT}; }}
    QPushButton#secondary_btn {{
        background-color: {BG_LT};
        color: {FG};
        border: 1px solid {BORDER};
        padding: 5px 12px;
        font-size: 10pt;
    }}
    QPushButton#secondary_btn:hover {{ background-color: {COLORS['accent_dark']}; border: 1px solid {ACCENT}; }}
    QDoubleSpinBox {{
        background-color: {BG_LT};
        color: {FG};
        border: 1px solid {BORDER};
        border-radius: 4px;
        padding: 4px 8px;
    }}
    QListWidget {{
        background-color: {BG_LT};
        color: {FG};
        border: 1px solid {BORDER};
        border-radius: 4px;
    }}
    QListWidget::item:selected {{ background-color: {ACCENT}; color: white; }}
    QRadioButton, QCheckBox {{ color: {FG}; }}
    QToolTip {{
        background-color: {BG_MED};
        color: {FG};
        border: 1px solid {ACCENT};
        padding: 6px;
        font-size: 9pt;
    }}
"""
