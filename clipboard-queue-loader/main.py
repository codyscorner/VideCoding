"""
Clipboard Queue Loader - Prompt Batch Tool for AI Image Generation
Version: 1.2.0
"""

import json
import os
import ctypes
import time

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QCheckBox, QListWidget, QListWidgetItem, QPlainTextEdit, QTextEdit,
    QGroupBox, QVBoxLayout, QHBoxLayout, QStatusBar,
    QFileDialog, QMessageBox,
)
from PyQt6.QtCore import Qt, QByteArray
from PyQt6.QtGui import QIcon, QColor, QFont

APP_TITLE = "Clipboard Queue Loader"
VERSION = "1.2.0"
STATE_FILE = "clipboard_queue_state.json"

# Dark teal/cyan color scheme
COLORS = {
    'bg_dark':      '#0d1f1f',
    'bg_medium':    '#1a3333',
    'bg_light':     '#2a4444',
    'fg_primary':   '#e0f4f4',
    'fg_secondary': '#90c0c0',
    'fg_dim':       '#608080',
    'accent':       '#00897b',
    'accent_hover': '#26a69a',
    'accent_dark':  '#00574b',
    'border':       '#2a5555',
    'used_fg':      '#607070',
    'current_bg':   '#00574b',
}

STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {COLORS['bg_dark']};
    color: {COLORS['fg_primary']};
    font-family: "Segoe UI";
    font-size: 10pt;
}}
QLabel {{
    background-color: transparent;
    color: {COLORS['fg_primary']};
}}
QLabel#subtitle {{
    color: {COLORS['fg_secondary']};
    font-size: 9pt;
}}
QLabel#header {{
    color: {COLORS['accent_hover']};
    font-size: 18pt;
    font-weight: bold;
}}
QLabel#progress {{
    color: {COLORS['accent_hover']};
    font-size: 12pt;
    font-weight: bold;
}}
QGroupBox {{
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    margin-top: 8px;
    padding: 8px;
    color: {COLORS['accent_hover']};
    font-weight: bold;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
}}
QPlainTextEdit, QTextEdit {{
    background-color: {COLORS['bg_light']};
    color: {COLORS['fg_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 3px;
    font-family: Consolas;
    font-size: 10pt;
    padding: 4px;
}}
QPlainTextEdit:focus, QTextEdit:focus {{
    border: 1px solid {COLORS['accent']};
}}
QCheckBox {{
    color: {COLORS['fg_primary']};
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {COLORS['border']};
    border-radius: 2px;
    background-color: {COLORS['bg_light']};
}}
QCheckBox::indicator:checked {{
    background-color: {COLORS['accent']};
    border-color: {COLORS['accent']};
}}
QPushButton {{
    background-color: {COLORS['accent']};
    color: white;
    font-weight: bold;
    border: none;
    border-radius: 4px;
    padding: 8px 18px;
    font-size: 10pt;
}}
QPushButton:hover {{
    background-color: {COLORS['accent_hover']};
}}
QPushButton:disabled {{
    background-color: {COLORS['bg_light']};
    color: {COLORS['fg_dim']};
}}
QPushButton#secondary_btn {{
    background-color: {COLORS['bg_light']};
    color: {COLORS['fg_primary']};
    padding: 6px 14px;
    font-size: 9pt;
    font-weight: normal;
}}
QPushButton#secondary_btn:hover {{
    background-color: {COLORS['accent_dark']};
    color: white;
}}
QPushButton#nav_btn {{
    background-color: {COLORS['bg_medium']};
    color: {COLORS['fg_primary']};
    padding: 8px 16px;
    font-size: 10pt;
    font-weight: normal;
}}
QPushButton#nav_btn:hover {{
    background-color: {COLORS['accent']};
    color: white;
}}
QListWidget {{
    background-color: {COLORS['bg_medium']};
    color: {COLORS['fg_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 3px;
    font-family: Consolas;
    font-size: 9pt;
}}
QListWidget::item:selected {{
    background-color: {COLORS['accent']};
    color: white;
}}
QScrollBar:vertical {{
    background-color: {COLORS['bg_dark']};
    width: 12px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background-color: {COLORS['border']};
    border-radius: 6px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QStatusBar {{
    background-color: {COLORS['bg_medium']};
    color: {COLORS['fg_secondary']};
    border-top: 1px solid {COLORS['border']};
    font-size: 9pt;
    padding: 3px 8px;
}}
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_TITLE} v{VERSION}")
        self.setMinimumSize(700, 680)
        self.setStyleSheet(STYLESHEET)

        self.item_list: list[str] = []
        self.current_index = 0
        self.used_indices: set[int] = set()

        self._build_ui()
        self._load_state()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 8)
        layout.setSpacing(10)

        # Header
        header = QLabel(APP_TITLE)
        header.setObjectName("header")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        subtitle = QLabel("Sequentially copy AI image prompts to clipboard")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        # Input area
        input_group = QGroupBox("Paste Prompts (one per line)")
        input_layout = QVBoxLayout(input_group)
        self.text_input = QPlainTextEdit()
        self.text_input.setPlaceholderText("Paste your prompts here, one per line...")
        self.text_input.setFixedHeight(110)
        input_layout.addWidget(self.text_input)

        input_btn_row = QHBoxLayout()
        load_btn = QPushButton("Load List")
        load_btn.clicked.connect(self._load_list)
        input_btn_row.addWidget(load_btn)

        save_btn = QPushButton("Save to File")
        save_btn.setObjectName("secondary_btn")
        save_btn.clicked.connect(self._save_to_file)
        input_btn_row.addWidget(save_btn)

        open_btn = QPushButton("Load from File")
        open_btn.setObjectName("secondary_btn")
        open_btn.clicked.connect(self._load_from_file)
        input_btn_row.addWidget(open_btn)

        clear_btn = QPushButton("Clear All")
        clear_btn.setObjectName("secondary_btn")
        clear_btn.clicked.connect(self._clear_all)
        input_btn_row.addWidget(clear_btn)
        input_btn_row.addStretch()
        input_layout.addLayout(input_btn_row)
        layout.addWidget(input_group)

        # Options row
        opt_row = QHBoxLayout()
        self.stay_on_top_check = QCheckBox("Stay on Top")
        self.stay_on_top_check.toggled.connect(self._toggle_stay_on_top)
        self.auto_paste_check = QCheckBox("Auto-paste")
        self.select_all_check = QCheckBox("Select All First")
        self.auto_advance_check = QCheckBox("Auto-advance")
        self.auto_advance_check.setChecked(True)
        self.skip_used_check = QCheckBox("Skip Used")
        for w in (self.stay_on_top_check, self.auto_paste_check,
                  self.select_all_check, self.auto_advance_check, self.skip_used_check):
            opt_row.addWidget(w)
        opt_row.addStretch()
        layout.addLayout(opt_row)

        # Prompt list
        list_group = QGroupBox("Loaded Prompts")
        list_layout = QVBoxLayout(list_group)
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._on_double_click)
        self.list_widget.itemClicked.connect(self._on_item_click)
        list_layout.addWidget(self.list_widget)
        layout.addWidget(list_group, stretch=1)

        # Preview
        preview_group = QGroupBox("Current Prompt Preview")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setFixedHeight(80)
        preview_layout.addWidget(self.preview_text)
        layout.addWidget(preview_group)

        # Navigation row
        nav_row = QHBoxLayout()
        self.prev_btn = QPushButton("<< Previous")
        self.prev_btn.setObjectName("nav_btn")
        self.prev_btn.clicked.connect(self._go_previous)
        nav_row.addWidget(self.prev_btn)

        self.progress_label = QLabel("No prompts loaded")
        self.progress_label.setObjectName("progress")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav_row.addWidget(self.progress_label, stretch=1)

        self.copy_btn = QPushButton("Copy Only")
        self.copy_btn.setObjectName("nav_btn")
        self.copy_btn.clicked.connect(self._copy_current)
        nav_row.addWidget(self.copy_btn)

        self.copy_next_btn = QPushButton("COPY && NEXT  [Enter]")
        self.copy_next_btn.clicked.connect(self._copy_and_next)
        nav_row.addWidget(self.copy_next_btn)

        self.next_btn = QPushButton("Next >>")
        self.next_btn.setObjectName("nav_btn")
        self.next_btn.clicked.connect(self._go_next)
        nav_row.addWidget(self.next_btn)
        layout.addLayout(nav_row)

        # Stats row
        stats_row = QHBoxLayout()
        self.stats_label = QLabel("")
        self.stats_label.setObjectName("subtitle")
        stats_row.addWidget(self.stats_label, stretch=1)

        reset_btn = QPushButton("Reset Used Status")
        reset_btn.setObjectName("secondary_btn")
        reset_btn.clicked.connect(self._reset_used)
        stats_row.addWidget(reset_btn)

        first_unused_btn = QPushButton("Go to First Unused")
        first_unused_btn.setObjectName("secondary_btn")
        first_unused_btn.clicked.connect(self._go_to_first_unused)
        stats_row.addWidget(first_unused_btn)
        layout.addLayout(stats_row)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready — paste prompts and click 'Load List'")

    # ── Keyboard shortcuts ────────────────────────────────────────────────────
    def keyPressEvent(self, event):
        key = event.key()
        focused = self.focusWidget()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if focused is not self.text_input:
                self._copy_and_next()
                return
        elif key == Qt.Key.Key_Left:
            self._go_previous()
            return
        elif key == Qt.Key.Key_Right:
            self._go_next()
            return
        elif key == Qt.Key.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)

    # ── Core logic ────────────────────────────────────────────────────────────
    def _toggle_stay_on_top(self, checked: bool):
        flags = self.windowFlags()
        if checked:
            self.setWindowFlags(flags | Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags & ~Qt.WindowType.WindowStaysOnTopHint)
        self.show()
        self.status_bar.showMessage(f"Stay on top {'enabled' if checked else 'disabled'}")

    def _load_list(self):
        text = self.text_input.toPlainText()
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if not lines:
            self.status_bar.showMessage("Warning: no prompts to load (empty or whitespace only)")
            return
        self.item_list = lines
        self.current_index = 0
        self.used_indices = set()
        self._refresh_list()
        self._update_preview()
        self._update_progress()
        self._update_stats()
        self.status_bar.showMessage(f"Loaded {len(self.item_list)} prompts")
        self._save_state()

    def _refresh_list(self):
        self.list_widget.clear()
        for i, item in enumerate(self.item_list):
            display = item[:80] + "..." if len(item) > 80 else item
            if i in self.used_indices:
                display = f"\u2713 {display}"
            else:
                display = f"   {display}"
            list_item = QListWidgetItem(display)
            if i in self.used_indices:
                list_item.setForeground(QColor(COLORS['used_fg']))
            if i == self.current_index:
                list_item.setBackground(QColor(COLORS['current_bg']))
                list_item.setForeground(QColor(COLORS['fg_primary']))
            self.list_widget.addItem(list_item)
        if self.item_list:
            self.list_widget.scrollToItem(self.list_widget.item(self.current_index))

    def _update_preview(self):
        if self.item_list:
            self.preview_text.setPlainText(self.item_list[self.current_index])
        else:
            self.preview_text.setPlainText("(No prompts loaded)")

    def _update_progress(self):
        if self.item_list:
            self.progress_label.setText(
                f"Prompt {self.current_index + 1} of {len(self.item_list)}"
            )
        else:
            self.progress_label.setText("No prompts loaded")

    def _update_stats(self):
        if self.item_list:
            used = len(self.used_indices)
            total = len(self.item_list)
            remaining = total - used
            self.stats_label.setText(f"Used: {used}  |  Remaining: {remaining}  |  Total: {total}")
        else:
            self.stats_label.setText("")

    def _go_previous(self):
        if not self.item_list:
            self.status_bar.showMessage("No prompts loaded")
            return
        if self.skip_used_check.isChecked():
            new_idx = self.current_index - 1
            while new_idx >= 0 and new_idx in self.used_indices:
                new_idx -= 1
            if new_idx < 0:
                self.status_bar.showMessage("No previous unused prompts")
                return
            self.current_index = new_idx
        else:
            if self.current_index > 0:
                self.current_index -= 1
            else:
                self.status_bar.showMessage("Already at first prompt")
                return
        self._refresh_list()
        self._update_preview()
        self._update_progress()
        self.status_bar.showMessage(f"Moved to prompt {self.current_index + 1}")

    def _go_next(self):
        if not self.item_list:
            self.status_bar.showMessage("No prompts loaded")
            return
        if self.skip_used_check.isChecked():
            new_idx = self.current_index + 1
            while new_idx < len(self.item_list) and new_idx in self.used_indices:
                new_idx += 1
            if new_idx >= len(self.item_list):
                self.status_bar.showMessage("No more unused prompts!")
                return
            self.current_index = new_idx
        else:
            if self.current_index < len(self.item_list) - 1:
                self.current_index += 1
            else:
                self.status_bar.showMessage("Already at last prompt")
                return
        self._refresh_list()
        self._update_preview()
        self._update_progress()
        self.status_bar.showMessage(f"Moved to prompt {self.current_index + 1}")

    def _copy_current(self):
        if not self.item_list:
            self.status_bar.showMessage("No prompts to copy")
            return
        prompt = self.item_list[self.current_index]
        QApplication.clipboard().setText(prompt)
        self.used_indices.add(self.current_index)
        self._refresh_list()
        self._update_stats()
        display = prompt[:50] + "..." if len(prompt) > 50 else prompt
        self.status_bar.showMessage(f"Copied: {display}")
        self._save_state()

    def _copy_and_next(self):
        if not self.item_list:
            self.status_bar.showMessage("No prompts to copy")
            return
        prompt = self.item_list[self.current_index]
        QApplication.clipboard().setText(prompt)
        if self.auto_paste_check.isChecked():
            self._send_paste_to_previous_window()
        self.used_indices.add(self.current_index)
        display = prompt[:50] + "..." if len(prompt) > 50 else prompt

        if self.auto_advance_check.isChecked():
            if self.skip_used_check.isChecked():
                new_idx = self.current_index + 1
                while new_idx < len(self.item_list) and new_idx in self.used_indices:
                    new_idx += 1
                if new_idx >= len(self.item_list):
                    self.status_bar.showMessage(f"Copied: {display} | ALL PROMPTS USED!")
                else:
                    self.current_index = new_idx
                    self.status_bar.showMessage(f"Copied: {display} | Advanced to {self.current_index + 1}")
            else:
                if self.current_index < len(self.item_list) - 1:
                    self.current_index += 1
                    self.status_bar.showMessage(f"Copied: {display} | Advanced to {self.current_index + 1}")
                else:
                    self.status_bar.showMessage(f"Copied: {display} | Reached end of list")
        else:
            self.status_bar.showMessage(f"Copied: {display}")

        self._refresh_list()
        self._update_preview()
        self._update_progress()
        self._update_stats()
        self._save_state()

    def _on_double_click(self, item):
        row = self.list_widget.row(item)
        self.current_index = row
        self._copy_current()
        self._update_preview()
        self._update_progress()

    def _on_item_click(self, item):
        row = self.list_widget.row(item)
        self.current_index = row
        self._refresh_list()
        self._update_preview()
        self._update_progress()

    def _reset_used(self):
        self.used_indices = set()
        self._refresh_list()
        self._update_stats()
        self.status_bar.showMessage("Reset all prompts to unused")
        self._save_state()

    def _go_to_first_unused(self):
        if not self.item_list:
            self.status_bar.showMessage("No prompts loaded")
            return
        for i in range(len(self.item_list)):
            if i not in self.used_indices:
                self.current_index = i
                self._refresh_list()
                self._update_preview()
                self._update_progress()
                self.status_bar.showMessage(f"Jumped to first unused prompt ({i + 1})")
                return
        self.status_bar.showMessage("All prompts have been used!")

    def _clear_all(self):
        if self.item_list:
            if QMessageBox.question(
                self, "Confirm", "Clear all prompts and reset?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            ) != QMessageBox.StandardButton.Yes:
                return
        self.item_list = []
        self.current_index = 0
        self.used_indices = set()
        self.text_input.clear()
        self.list_widget.clear()
        self._update_preview()
        self._update_progress()
        self._update_stats()
        self.status_bar.showMessage("Cleared all prompts")
        state_path = os.path.join(os.path.dirname(__file__) or ".", STATE_FILE)
        if os.path.exists(state_path):
            os.remove(state_path)

    def _save_to_file(self):
        if not self.item_list:
            self.status_bar.showMessage("No prompts to save")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Prompts", "",
            "Text files (*.txt);;All files (*.*)"
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(self.item_list))
            self.status_bar.showMessage(
                f"Saved {len(self.item_list)} prompts to {os.path.basename(path)}"
            )

    def _load_from_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Prompts", "",
            "Text files (*.txt);;All files (*.*)"
        )
        if path:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.text_input.setPlainText(content)
            self._load_list()
            self.status_bar.showMessage(f"Loaded prompts from {os.path.basename(path)}")

    def _send_paste_to_previous_window(self):
        VK_CONTROL = 0x11
        VK_V = 0x56
        VK_A = 0x41
        VK_MENU = 0x12
        VK_TAB = 0x09
        KEYEVENTF_KEYUP = 0x0002

        ctypes.windll.user32.keybd_event(VK_MENU, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_TAB, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_TAB, 0, KEYEVENTF_KEYUP, 0)
        ctypes.windll.user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
        time.sleep(0.15)

        if self.select_all_check.isChecked():
            ctypes.windll.user32.keybd_event(VK_CONTROL, 0, 0, 0)
            ctypes.windll.user32.keybd_event(VK_A, 0, 0, 0)
            ctypes.windll.user32.keybd_event(VK_A, 0, KEYEVENTF_KEYUP, 0)
            ctypes.windll.user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
            time.sleep(0.05)

        ctypes.windll.user32.keybd_event(VK_CONTROL, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_V, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
        ctypes.windll.user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)

    # ── State persistence ─────────────────────────────────────────────────────
    def _save_state(self):
        state = {
            "item_list": self.item_list,
            "current_index": self.current_index,
            "used_indices": list(self.used_indices),
        }
        state_path = os.path.join(os.path.dirname(__file__) or ".", STATE_FILE)
        try:
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state, f)
        except Exception:
            pass

    def _load_state(self):
        state_path = os.path.join(os.path.dirname(__file__) or ".", STATE_FILE)
        if not os.path.exists(state_path):
            return
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                state = json.load(f)
            self.item_list = state.get("item_list", [])
            self.current_index = state.get("current_index", 0)
            self.used_indices = set(state.get("used_indices", []))
            if self.item_list:
                self.text_input.setPlainText("\n".join(self.item_list))
                self._refresh_list()
                self._update_preview()
                self._update_progress()
                self._update_stats()
                self.status_bar.showMessage(
                    f"Restored {len(self.item_list)} prompts from previous session"
                )
        except Exception:
            pass

    def closeEvent(self, event):
        self._save_state()
        event.accept()


def main():
    import sys
    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)

    from pathlib import Path
    icon_path = Path(__file__).parent / "app_icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
