"""IMDB Photo Downloader — GUI v1.1.1"""

VERSION = "1.1.1"

import csv
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

# When frozen by PyInstaller, Playwright resolves its browser cache relative
# to the ephemeral _MEI extraction folder instead of the normal persistent
# %LOCALAPPDATA%\ms-playwright location. Pin it before importing playwright
# so installed browsers are found across runs.
os.environ.setdefault(
    "PLAYWRIGHT_BROWSERS_PATH",
    str(Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "ms-playwright"),
)

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPlainTextEdit, QPushButton, QListWidget, QFileDialog,
    QProgressBar, QCheckBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 1.0  # seconds, doubles each retry

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
# Pure helpers (unit-testable without a browser)
# ------------------------------------------------------------------ #

def extract_id(url: str) -> tuple[str, str]:
    m = re.search(r"(tt|nm)\d+", url)
    if not m:
        raise ValueError(f"Could not find an IMDB title or name ID in: {url}")
    imdb_id = m.group()
    return imdb_id, "name" if imdb_id.startswith("nm") else "title"


def parse_url_queue(text: str) -> list[str]:
    """Split a multi-line textbox into a deduped, ordered list of non-blank URLs."""
    seen = []
    for line in text.splitlines():
        line = line.strip()
        if line and line not in seen:
            seen.append(line)
    return seen


def parse_gallery_images(html: str) -> list[dict]:
    """Extract (full_res_url, caption, mediaviewer_url) entries from a gallery page's HTML."""
    soup = BeautifulSoup(html, "html.parser")
    found = []
    seen_urls = set()
    for img in soup.find_all("img"):
        src = img.get("src", "") or img.get("data-src", "")
        if "media-amazon.com" not in src or "_V1_" not in src:
            continue
        full = re.sub(r"\._V1_.*\.(jpg|jpeg|png)", r"._V1_.\1", src)
        if full in seen_urls:
            continue
        seen_urls.add(full)
        caption = (img.get("alt") or "").strip()
        mediaviewer_url = ""
        link = img.find_parent("a")
        if link:
            href = link.get("href", "")
            if "/mediaviewer/" in href:
                mediaviewer_url = href
        found.append({"url": full, "caption": caption, "mediaviewer_url": mediaviewer_url})
    return found


def extract_full_res_from_mediaviewer(html: str, fallback_url: str) -> str:
    """Given a mediaviewer page's HTML, find the largest available image URL."""
    soup = BeautifulSoup(html, "html.parser")
    og = soup.find("meta", attrs={"property": "og:image"})
    if og and og.get("content"):
        return og["content"]
    return fallback_url


def write_manifest(out_dir: Path, rows: list[dict]) -> None:
    """Write manifest.csv and manifest.json describing each downloaded/skipped/failed image."""
    csv_path = out_dir / "manifest.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["index", "filename", "source_url", "caption", "status"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    json_path = out_dir / "manifest.json"
    json_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def download_with_retry(url: str, dest: Path, retries: int = MAX_RETRIES) -> bool:
    """Download a URL to dest, retrying with exponential backoff on failure."""
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=DOWNLOAD_HEADERS, timeout=30, stream=True)
            r.raise_for_status()
            dest.write_bytes(r.content)
            return True
        except Exception:
            if attempt < retries - 1:
                time.sleep(RETRY_BACKOFF_BASE * (2 ** attempt))
    return False


# ------------------------------------------------------------------ #
# Worker thread
# ------------------------------------------------------------------ #

class DownloadWorker(QThread):
    log         = pyqtSignal(str)
    progress    = pyqtSignal(int, int)
    url_started = pyqtSignal(int, int, str)   # queue index, total, url
    url_done    = pyqtSignal(int, int, int, str)  # downloaded, skipped, failed, out_dir
    finished    = pyqtSignal(int, int, int, str)  # aggregate downloaded, skipped, failed, last_out_dir
    error       = pyqtSignal(str)

    def __init__(self, urls: list[str], root_dir: Path, full_res: bool = False):
        super().__init__()
        self._urls = urls
        self._root_dir = root_dir
        self._full_res = full_res
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        total_downloaded = total_skipped = total_failed = 0
        last_out_dir = ""

        for qi, url in enumerate(self._urls, 1):
            if self._cancelled:
                self.log.emit("Cancelled.")
                break

            self.url_started.emit(qi, len(self._urls), url)

            try:
                imdb_id, id_type = extract_id(url)
            except ValueError as e:
                self.error.emit(str(e))
                continue

            try:
                title_name, images = self._scrape(imdb_id, id_type)
            except Exception as e:
                self.error.emit(f"Scrape failed for {url}: {e}")
                continue

            if not images:
                self.error.emit(f"No images found on {url}.")
                continue

            safe = re.sub(r'[<>:"/\\|?*]', "_", title_name)
            out = self._root_dir / safe
            out.mkdir(parents=True, exist_ok=True)
            self.log.emit(f"Saving to: {out}")

            downloaded = skipped = failed = 0
            manifest_rows = []
            total = len(images)

            for i, entry in enumerate(images, 1):
                if self._cancelled:
                    self.log.emit("Cancelled.")
                    break

                dest = out / f"{safe}_{i:04d}.jpg"
                status = ""
                if dest.exists():
                    skipped += 1
                    status = "skipped"
                    self.log.emit(f"[{i}/{total}] Skip: {dest.name}")
                else:
                    if download_with_retry(entry["url"], dest):
                        downloaded += 1
                        status = "downloaded"
                        self.log.emit(f"[{i}/{total}] OK: {dest.name}")
                    else:
                        failed += 1
                        status = "failed"
                        self.log.emit(f"[{i}/{total}] FAIL")

                manifest_rows.append({
                    "index": i,
                    "filename": dest.name,
                    "source_url": entry["url"],
                    "caption": entry.get("caption", ""),
                    "status": status,
                })

                self.progress.emit(i, total)
                time.sleep(0.15)

            write_manifest(out, manifest_rows)
            self.log.emit(f"Manifest written: {out / 'manifest.csv'}")

            total_downloaded += downloaded
            total_skipped += skipped
            total_failed += failed
            last_out_dir = str(out)
            self.url_done.emit(downloaded, skipped, failed, str(out))

        self.finished.emit(total_downloaded, total_skipped, total_failed, last_out_dir)

    def _scrape(self, imdb_id: str, id_type: str) -> tuple[str, list[dict]]:
        images: list[dict] = []
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
                prev_html = ""
                for _ in range(20):
                    pg.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    pg.wait_for_timeout(800)
                    html = pg.content()
                    if html == prev_html:
                        break  # no new images loaded
                    prev_html = html
                return parse_gallery_images(prev_html)

            entries = collect(page)
            images.extend(entries)
            self.log.emit(f"Page 1/{total_pages} — {len(entries)} images")

            for pg_num in range(2, total_pages + 1):
                if self._cancelled:
                    break
                page.goto(
                    f"https://www.imdb.com/{base}/{imdb_id}/mediaindex/?page={pg_num}",
                    wait_until="domcontentloaded"
                )
                entries = collect(page)
                images.extend(entries)
                self.log.emit(f"Page {pg_num}/{total_pages} — {len(entries)} images")
                time.sleep(0.5)

            if self._full_res:
                self.log.emit("Fetching full-resolution images (visiting each photo page)...")
                for entry in images:
                    if self._cancelled:
                        break
                    if not entry["mediaviewer_url"]:
                        continue
                    try:
                        mv_url = entry["mediaviewer_url"]
                        if mv_url.startswith("/"):
                            mv_url = f"https://www.imdb.com{mv_url}"
                        page.goto(mv_url, wait_until="domcontentloaded")
                        page.wait_for_timeout(500)
                        entry["url"] = extract_full_res_from_mediaviewer(page.content(), entry["url"])
                    except Exception:
                        pass  # keep gallery-resolution fallback already in entry["url"]

            browser.close()

        # de-dupe by final url, preserving order
        deduped = []
        seen = set()
        for entry in images:
            if entry["url"] not in seen:
                seen.add(entry["url"])
                deduped.append(entry)
        self.log.emit(f"Total unique images: {len(deduped)}")
        return title_name, deduped


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

        sub = QLabel("Paste one or more IMDB title/actor URLs (one per line) — each saves to its own named subfolder")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet(f"color: {FG_DIM}; font-size: 9pt;")
        root.addWidget(sub)

        # URL queue input
        self._url_edit = QPlainTextEdit()
        self._url_edit.setPlaceholderText(
            "https://www.imdb.com/title/tt2543796/\nhttps://www.imdb.com/name/nm1760388/\n..."
        )
        self._url_edit.setFixedHeight(80)
        root.addWidget(self._url_edit)

        # Full-resolution option
        self._full_res_chk = QCheckBox("Grab full-resolution images (slower — visits each photo page)")
        self._full_res_chk.setStyleSheet(f"color: {FG_DIM};")
        root.addWidget(self._full_res_chk)

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
        urls = parse_url_queue(self._url_edit.toPlainText())
        if not urls:
            self._status.setText("Paste at least one IMDB URL first.")
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

        self._worker = DownloadWorker(urls, root_dir, full_res=self._full_res_chk.isChecked())
        self._worker.log.connect(self._on_log)
        self._worker.progress.connect(self._on_progress)
        self._worker.url_started.connect(self._on_url_started)
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

    def _on_url_started(self, index: int, total: int, url: str):
        self._on_log(f"— URL {index}/{total}: {url}")

    def _on_progress(self, current: int, total: int):
        self._progress.setRange(0, total)
        self._progress.setValue(current)
        self._status.setText(f"Downloading... {current}/{total}")

    def _on_finished(self, downloaded: int, skipped: int, failed: int, out_dir: str):
        self._last_out_dir = Path(out_dir) if out_dir else None
        self._progress.setRange(0, 1)
        self._progress.setValue(1)
        self._go_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        self._status.setText(
            f"Done — Downloaded: {downloaded}  Skipped: {skipped}  Failed: {failed}"
        )
        self._on_log(f"✅ Complete — {downloaded} downloaded, {skipped} skipped, {failed} failed")
        if out_dir:
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
