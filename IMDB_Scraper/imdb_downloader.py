"""IMDB Photo Downloader — GUI v1.0.0"""

VERSION = "1.0.0"

import json
import re
import subprocess
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QListWidget, QFileDialog, QProgressBar,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

# ------------------------------------------------------------------ #
# Colors / style
# ------------------------------------------------------------------ #

BG       = "#13131f"
BG_MED   = "#1c1c2e"
BG_LIGHT = "#252540"
ACCENT   = "#6c5ce7"
ACCENT_H = "#7d6ff0"
FG       = "#e0e0f0"
FG_DIM   = "#7070a0"
BORDER   = "#2e2e50"
SUCCESS  = "#4caf8a"
ERROR    = "#ff6b6b"

STYLESHEET = f"""
    QMainWindow, QWidget {{
        background-color: {BG};
        color: {FG};
        font-family: "Segoe UI";
        font-size: 10pt;
    }}
    QLabel {{ color: {FG}; }}
    QLineEdit {{
        background-color: {BG_LIGHT};
        color: {FG};
        border: 1px solid {BORDER};
        border-radius: 4px;
        padding: 6px 10px;
        font-size: 10pt;
    }}
    QLineEdit:focus {{ border: 1px solid {ACCENT}; }}
    QPushButton {{
        background-color: {ACCENT};
        color: white;
        font-weight: bold;
        border: none;
        border-radius: 4px;
        padding: 8px 20px;
        font-size: 10pt;
    }}
    QPushButton:hover {{ background-color: {ACCENT_H}; }}
    QPushButton:disabled {{ background-color: {BG_LIGHT}; color: {FG_DIM}; }}
    QPushButton#cancel_btn {{
        background-color: {BG_LIGHT};
        color: {FG_DIM};
        border: 1px solid {BORDER};
    }}
    QPushButton#cancel_btn:hover {{ background-color: {ERROR}; color: white; }}
    QPushButton#browse_btn {{
        background-color: {BG_LIGHT};
        color: {FG_DIM};
        border: 1px solid {BORDER};
        padding: 6px 12px;
    }}
    QPushButton#browse_btn:hover {{ background-color: {BG_MED}; color: {FG}; }}
    QListWidget {{
        background-color: {BG_MED};
        color: {FG};
        border: 1px solid {BORDER};
        border-radius: 4px;
        font-size: 9pt;
        font-family: Consolas;
        padding: 4px;
    }}
    QProgressBar {{
        background-color: {BG_LIGHT};
        border: 1px solid {BORDER};
        border-radius: 4px;
        height: 18px;
        text-align: center;
        color: white;
        font-size: 8pt;
    }}
    QProgressBar::chunk {{
        background-color: {ACCENT};
        border-radius: 3px;
    }}
"""

DOWNLOAD_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}

SETTINGS_FILE = Path(__file__).parent / "imdb_downloader_settings.json"


# ------------------------------------------------------------------ #
# Settings
# ------------------------------------------------------------------ #

def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text())
        except Exception:
            pass
    return {"root_dir": ""}


def save_settings(settings: dict):
    try:
        SETTINGS_FILE.write_text(json.dumps(settings, indent=2))
    except Exception:
        pass


# ------------------------------------------------------------------ #
# Worker thread
# ------------------------------------------------------------------ #

class DownloadWorker(QThread):
    log      = pyqtSignal(str)
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(int, int, int, str)  # downloaded, skipped, failed, out_dir
    error    = pyqtSignal(str)

    def __init__(self, url: str, root_dir: Path):
        super().__init__()
        self._url = url
        self._root_dir = root_dir
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            imdb_id, id_type = self._extract_id(self._url)
        except ValueError as e:
            self.error.emit(str(e))
            return

        try:
            title_name, image_urls = self._scrape(imdb_id, id_type)
        except Exception as e:
            self.error.emit(f"Scrape failed: {e}")
            return

        if not image_urls:
            self.error.emit("No images found on that page.")
            return

        # Named subfolder under root
        safe = re.sub(r'[<>:"/\\|?*]', "_", title_name)
        out = self._root_dir / safe
        out.mkdir(parents=True, exist_ok=True)
        self.log.emit(f"Saving to: {out}")

        downloaded = skipped = failed = 0
        total = len(image_urls)

        for i, img_url in enumerate(image_urls, 1):
            if self._cancelled:
                self.log.emit("Cancelled.")
                break

            dest = out / f"{safe}_{i:04d}.jpg"
            if dest.exists():
                skipped += 1
                self.log.emit(f"[{i}/{total}] Skip: {dest.name}")
            else:
                if self._download(img_url, dest):
                    downloaded += 1
                    self.log.emit(f"[{i}/{total}] OK: {dest.name}")
                else:
                    failed += 1
                    self.log.emit(f"[{i}/{total}] FAIL")

            self.progress.emit(i, total)
            time.sleep(0.15)

        self.finished.emit(downloaded, skipped, failed, str(out))

    def _extract_id(self, url: str) -> tuple[str, str]:
        m = re.search(r"(tt|nm)\d+", url)
        if not m:
            raise ValueError("Could not find an IMDB title or name ID in that URL.")
        imdb_id = m.group()
        return imdb_id, "name" if imdb_id.startswith("nm") else "title"

    def _scrape(self, imdb_id: str, id_type: str) -> tuple[str, list[str]]:
        image_urls = []
        title_name = imdb_id
        base = "name" if id_type == "name" else "title"

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_context(
                user_agent=DOWNLOAD_HEADERS["User-Agent"],
                locale="en-US",
            ).new_page()
            page.route("**/*.{woff,woff2,ttf,otf}", lambda r: r.abort())

            self.log.emit("Opening IMDB media gallery...")
            page.goto(f"https://www.imdb.com/{base}/{imdb_id}/mediaindex/",
                      wait_until="domcontentloaded")
            page.wait_for_timeout(2000)

            # Title
            try:
                og = page.query_selector("meta[property='og:title']")
                if og:
                    raw = og.get_attribute("content") or ""
                    title_name = raw.split(" - Photos")[0].strip()
            except Exception:
                pass
            self.log.emit(f"Title: {title_name}")

            # Page count
            total_pages = 1
            try:
                nums = []
                for el in page.query_selector_all("a.page-link, span.page-link"):
                    try:
                        nums.append(int(el.inner_text().strip()))
                    except Exception:
                        pass
                if nums:
                    total_pages = max(nums)
            except Exception:
                pass
            self.log.emit(f"Gallery pages: {total_pages}")

            def collect(pg):
                # Scroll to bottom repeatedly to trigger lazy loading
                prev_count = 0
                for _ in range(20):
                    pg.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    pg.wait_for_timeout(800)
                    soup = BeautifulSoup(pg.content(), "html.parser")
                    count = len([
                        img for img in soup.find_all("img")
                        if "media-amazon.com" in img.get("src", "") and "_V1_" in img.get("src", "")
                    ])
                    if count == prev_count:
                        break  # no new images loaded
                    prev_count = count

                found = []
                for img in soup.find_all("img"):
                    src = img.get("src", "") or img.get("data-src", "")
                    if "media-amazon.com" in src and "_V1_" in src:
                        full = re.sub(r"\._V1_.*\.(jpg|jpeg|png)", r"._V1_.\1", src)
                        if full not in found:
                            found.append(full)
                return found

            urls = collect(page)
            image_urls.extend(urls)
            self.log.emit(f"Page 1/{total_pages} — {len(urls)} images")

            for pg_num in range(2, total_pages + 1):
                if self._cancelled:
                    break
                page.goto(
                    f"https://www.imdb.com/{base}/{imdb_id}/mediaindex/?page={pg_num}",
                    wait_until="domcontentloaded"
                )
                urls = collect(page)
                image_urls.extend(urls)
                self.log.emit(f"Page {pg_num}/{total_pages} — {len(urls)} images")
                time.sleep(0.5)

            browser.close()

        image_urls = list(dict.fromkeys(image_urls))
        self.log.emit(f"Total unique images: {len(image_urls)}")
        return title_name, image_urls

    def _download(self, url: str, dest: Path) -> bool:
        try:
            r = requests.get(url, headers=DOWNLOAD_HEADERS, timeout=30, stream=True)
            r.raise_for_status()
            dest.write_bytes(r.content)
            return True
        except Exception:
            return False


# ------------------------------------------------------------------ #
# Main window
# ------------------------------------------------------------------ #

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._worker: DownloadWorker | None = None
        self._last_out_dir: Path | None = None
        self._settings = load_settings()

        self.setWindowTitle(f"IMDB Photo Downloader  v{VERSION}")
        self.setMinimumSize(700, 540)
        self.resize(820, 600)
        self.setStyleSheet(STYLESHEET)
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        # Title
        title = QLabel("IMDB Photo Downloader")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"font-size: 16pt; font-weight: bold; color: {ACCENT};")
        root.addWidget(title)

        sub = QLabel("Paste an IMDB title or actor/actress URL — photos save to a named subfolder")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet(f"color: {FG_DIM}; font-size: 9pt;")
        root.addWidget(sub)

        # URL input
        self._url_edit = QLineEdit()
        self._url_edit.setPlaceholderText(
            "https://www.imdb.com/title/tt2543796/  or  https://www.imdb.com/name/nm1760388/"
        )
        self._url_edit.returnPressed.connect(self._start)
        root.addWidget(self._url_edit)

        # Root folder row
        root_row = QHBoxLayout()
        root_lbl = QLabel("Root Folder:")
        root_lbl.setFixedWidth(90)
        root_lbl.setStyleSheet(f"color: {FG_DIM};")
        self._root_edit = QLineEdit(self._settings.get("root_dir", ""))
        self._root_edit.setPlaceholderText("Select a root download folder...")
        self._root_edit.setReadOnly(True)
        browse_btn = QPushButton("...")
        browse_btn.setObjectName("browse_btn")
        browse_btn.setFixedWidth(40)
        browse_btn.clicked.connect(self._browse_root)
        root_row.addWidget(root_lbl)
        root_row.addWidget(self._root_edit)
        root_row.addWidget(browse_btn)
        root.addLayout(root_row)

        # Info label
        self._root_info = QLabel("Downloads will be saved to:  <root folder> / <title name> /")
        self._root_info.setStyleSheet(f"color: {FG_DIM}; font-size: 8pt; font-style: italic;")
        root.addWidget(self._root_info)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._go_btn = QPushButton("⬇  Download")
        self._go_btn.setFixedHeight(42)
        self._go_btn.clicked.connect(self._start)
        self._cancel_btn = QPushButton("✕  Cancel")
        self._cancel_btn.setObjectName("cancel_btn")
        self._cancel_btn.setFixedHeight(42)
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.clicked.connect(self._cancel)
        btn_row.addWidget(self._go_btn)
        btn_row.addSpacing(8)
        btn_row.addWidget(self._cancel_btn)
        btn_row.addStretch()
        root.addLayout(btn_row)

        # Progress bar
        self._progress = QProgressBar()
        self._progress.setRange(0, 1)
        self._progress.setValue(0)
        root.addWidget(self._progress)

        # Status log
        self._log = QListWidget()
        root.addWidget(self._log, stretch=1)

        # Bottom status
        self._status = QLabel("Ready")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setStyleSheet(f"color: {FG_DIM}; font-size: 9pt;")
        root.addWidget(self._status)

        # Clickable output folder link
        self._folder_link = QLabel("")
        self._folder_link.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._folder_link.setStyleSheet(
            f"color: {ACCENT}; font-size: 9pt; text-decoration: underline;"
        )
        self._folder_link.setCursor(Qt.CursorShape.PointingHandCursor)
        self._folder_link.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._folder_link.mousePressEvent = self._open_folder
        self._folder_link.setWordWrap(True)
        root.addWidget(self._folder_link)

    def _browse_root(self):
        current = self._root_edit.text().strip() or str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, "Select Root Download Folder", current)
        if folder:
            self._root_edit.setText(folder)
            self._settings["root_dir"] = folder
            save_settings(self._settings)

    def _start(self):
        url = self._url_edit.text().strip()
        if not url:
            self._status.setText("Paste an IMDB URL first.")
            return

        root_dir_str = self._root_edit.text().strip()
        if not root_dir_str:
            self._status.setText("Please select a root folder first.")
            return

        root_dir = Path(root_dir_str)

        self._log.clear()
        self._folder_link.setText("")
        self._progress.setRange(0, 0)
        self._go_btn.setEnabled(False)
        self._cancel_btn.setEnabled(True)
        self._status.setText("Working...")

        self._worker = DownloadWorker(url, root_dir)
        self._worker.log.connect(self._on_log)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _cancel(self):
        if self._worker:
            self._worker.cancel()
        self._cancel_btn.setEnabled(False)
        self._status.setText("Cancelling...")

    def _on_log(self, msg: str):
        self._log.addItem(msg)
        self._log.scrollToBottom()

    def _on_progress(self, current: int, total: int):
        self._progress.setRange(0, total)
        self._progress.setValue(current)
        self._status.setText(f"Downloading... {current}/{total}")

    def _on_finished(self, downloaded: int, skipped: int, failed: int, out_dir: str):
        self._last_out_dir = Path(out_dir)
        self._progress.setRange(0, 1)
        self._progress.setValue(1)
        self._go_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        self._status.setText(
            f"Done — Downloaded: {downloaded}  Skipped: {skipped}  Failed: {failed}"
        )
        self._on_log(f"✅ Complete — {downloaded} downloaded, {skipped} skipped, {failed} failed")
        self._folder_link.setText(f"📁 {out_dir}  (click to open in Explorer)")

    def _on_error(self, msg: str):
        self._go_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        self._progress.setRange(0, 1)
        self._progress.setValue(0)
        self._status.setText(f"Error: {msg}")
        self._on_log(f"❌ Error: {msg}")

    def _open_folder(self, event=None):
        if self._last_out_dir and self._last_out_dir.exists():
            subprocess.Popen(f'explorer "{self._last_out_dir}"')

    def closeEvent(self, event):
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(3000)
        event.accept()


# ------------------------------------------------------------------ #
# Entry point
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("IMDB Photo Downloader")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
