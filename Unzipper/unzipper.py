import json
import os
import shutil
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QLineEdit,
    QPushButton, QTextEdit, QGridLayout, QVBoxLayout,
    QHBoxLayout, QFrame, QFileDialog, QMessageBox,
    QCheckBox, QDialog, QListWidget, QInputDialog,
)
from PyQt6.QtGui import QIcon, QColor, QTextCharFormat
from PyQt6.QtCore import Qt, QThread, pyqtSignal

try:
    import py7zr
    HAS_7Z = True
except ImportError:
    HAS_7Z = False

try:
    import rarfile
    HAS_RAR = True
except ImportError:
    HAS_RAR = False

try:
    from send2trash import send2trash
    HAS_TRASH = True
except ImportError:
    HAS_TRASH = False

VERSION = "1.3.0"
MAX_NESTED_DEPTH = 3

BG_DARK      = "#0d1f0d"
BG_MID       = "#122112"
BG_PANEL     = "#1a3a1a"
ACCENT       = "#39d353"
ACCENT_HOVER = "#57e870"
ACCENT_DIM   = "#1a6b1a"
TEXT_BRIGHT  = "#d4f5d4"
TEXT_DIM     = "#7aaa7a"
BORDER       = "#2d5a2d"
SUCCESS      = "#39d353"
ERROR_COL    = "#e05c5c"
WARNING_COL  = "#e0a020"

STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {BG_DARK};
    color: {TEXT_BRIGHT};
    font-family: "Segoe UI";
    font-size: 9pt;
}}
QLabel {{
    background-color: transparent;
    color: {TEXT_DIM};
}}
QLabel#title {{
    font-size: 13pt;
    font-weight: bold;
    color: {TEXT_BRIGHT};
}}
QLabel#version {{
    font-size: 8pt;
    color: {TEXT_DIM};
}}
QLineEdit {{
    background-color: {BG_PANEL};
    color: {TEXT_BRIGHT};
    border: 1px solid {BORDER};
    border-radius: 3px;
    padding: 5px;
    font-size: 9pt;
}}
QLineEdit:focus {{
    border: 1px solid {ACCENT};
}}
QPushButton {{
    background-color: {ACCENT};
    color: {TEXT_BRIGHT};
    font-weight: bold;
    border: none;
    border-radius: 3px;
    padding: 6px 14px;
    font-size: 9pt;
}}
QPushButton:hover {{
    background-color: {ACCENT_HOVER};
}}
QPushButton:disabled {{
    background-color: {ACCENT_DIM};
    color: {TEXT_DIM};
}}
QPushButton#secondary {{
    background-color: {BG_PANEL};
}}
QPushButton#secondary:hover {{
    background-color: {BORDER};
}}
QPushButton#secondary:disabled {{
    background-color: {BG_MID};
    color: {TEXT_DIM};
}}
QCheckBox {{
    background-color: transparent;
    color: {TEXT_DIM};
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {BORDER};
    border-radius: 3px;
    background-color: {BG_PANEL};
}}
QCheckBox::indicator:checked {{
    background-color: {ACCENT};
    border: 1px solid {ACCENT};
}}
QTextEdit {{
    background-color: {BG_MID};
    color: {TEXT_BRIGHT};
    border: 1px solid {BORDER};
    border-radius: 3px;
    font-family: Consolas;
    font-size: 8pt;
}}
QListWidget {{
    background-color: {BG_MID};
    color: {TEXT_BRIGHT};
    border: 1px solid {BORDER};
    border-radius: 3px;
    font-size: 9pt;
}}
QListWidget::item:selected {{
    background-color: {ACCENT_DIM};
}}
QFrame#divider {{
    background-color: {BORDER};
}}
QFrame#titlebar {{
    background-color: {ACCENT_DIM};
}}
"""


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


PASSWORDS_FILE = app_dir() / "unzipper_passwords.json"


def load_saved_passwords() -> list[str]:
    try:
        with open(PASSWORDS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [p for p in data if isinstance(p, str) and p]
    except (OSError, json.JSONDecodeError):
        pass
    return []


def save_saved_passwords(passwords: list[str]):
    with open(PASSWORDS_FILE, "w", encoding="utf-8") as f:
        json.dump(passwords, f, indent=2)


def configure_rar_backend() -> str:
    """Point rarfile at an available extraction tool. Returns tool description or ''."""
    if not HAS_RAR:
        return ""
    candidates_unrar = [
        r"C:\Program Files\WinRAR\UnRAR.exe",
        r"C:\Program Files (x86)\WinRAR\UnRAR.exe",
    ]
    candidates_7z = [
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
    ]
    if shutil.which(rarfile.UNRAR_TOOL):
        return rarfile.UNRAR_TOOL
    for path in candidates_unrar:
        if os.path.exists(path):
            rarfile.UNRAR_TOOL = path
            return path
    if shutil.which(rarfile.SEVENZIP_TOOL):
        return rarfile.SEVENZIP_TOOL
    for path in candidates_7z:
        if os.path.exists(path):
            rarfile.SEVENZIP_TOOL = path
            return path
    return ""  # rarfile's own auto-detection may still find unar/bsdtar


RAR_TOOL = configure_rar_backend()


def _archive_type(filename: str) -> str:
    """Return archive type tag or empty string if not a supported archive."""
    lower = filename.lower()
    if lower.endswith(".zip"):
        return "ZIP"
    if lower.endswith(".7z"):
        return "7Z"
    if lower.endswith(".tar.gz") or lower.endswith(".tgz"):
        return "TAR.GZ"
    if lower.endswith(".rar"):
        return "RAR"
    return ""


def _strip_archive_ext(filename: str) -> str:
    base = filename
    for ext in (".tar.gz", ".tgz", ".7z", ".zip", ".rar"):
        if base.lower().endswith(ext):
            return base[: len(base) - len(ext)]
    return base


def _list_archives(folder: str) -> list[tuple[str, str]]:
    """Return (filename, type_tag) for all supported archives in folder."""
    results = []
    for f in sorted(os.listdir(folder)):
        tag = _archive_type(f)
        if tag and os.path.isfile(os.path.join(folder, f)):
            results.append((f, tag))
    return results


def _unique_folder(dest: str, base: str) -> str:
    folder_name = base
    counter = 0
    while os.path.exists(os.path.join(dest, folder_name)):
        counter += 1
        folder_name = f"{base}_{counter:06d}"
    return folder_name


class PasswordError(Exception):
    """Archive is encrypted and no supplied password worked."""


# ---------------------------------------------------------------------------
# Extraction engine (UI-independent; log is a callable(message, color))
# ---------------------------------------------------------------------------

def _zip_find_password(zf: zipfile.ZipFile, passwords: list[str]) -> bytes | None:
    encrypted = [i for i in zf.infolist() if not i.is_dir() and i.flag_bits & 0x1]
    if not encrypted:
        return None
    probe = encrypted[0]
    for pwd in passwords:
        try:
            with zf.open(probe, pwd=pwd.encode("utf-8")) as src:
                src.read(16)
            return pwd.encode("utf-8")
        except (RuntimeError, zipfile.BadZipFile):
            continue
    raise PasswordError("password required (no working password found)")


def _zip_extract_flat(path, dest, base, counter, passwords, log):
    created = []
    with zipfile.ZipFile(path, "r") as zf:
        pwd = _zip_find_password(zf, passwords)
        for info in zf.infolist():
            if info.is_dir():
                continue
            ext = os.path.splitext(info.filename)[1]
            new_name = f"{base}_{counter:06d}{ext}"
            new_path = os.path.join(dest, new_name)
            with zf.open(info, pwd=pwd) as src, open(new_path, "wb") as dst:
                shutil.copyfileobj(src, dst)
            log(f"    [ZIP] Extracted: {new_name}", SUCCESS)
            counter += 1
            created.append(new_path)
    return counter, created


def _zip_extract_structured(path, folder_path, passwords, log):
    with zipfile.ZipFile(path, "r") as zf:
        pwd = _zip_find_password(zf, passwords)
        if pwd:
            zf.setpassword(pwd)
        zf.extractall(folder_path)


def _zip_test(path, passwords):
    with zipfile.ZipFile(path, "r") as zf:
        pwd = _zip_find_password(zf, passwords)
        if pwd:
            zf.setpassword(pwd)
        bad = zf.testzip()
        if bad:
            raise RuntimeError(f"corrupt member: {bad}")


def _7z_extract_to(path, out_dir, passwords):
    """Extract entire 7z archive into out_dir, trying passwords. Raises on failure."""
    last_err = None
    for pwd in [None] + passwords:
        try:
            with py7zr.SevenZipFile(path, mode="r", password=pwd) as zf:
                if zf.needs_password() and pwd is None:
                    last_err = PasswordError("password required")
                    continue
                zf.extractall(out_dir)
            return
        except PasswordError:
            raise
        except Exception as e:
            last_err = e
            # wipe partial output before retrying with the next password
            shutil.rmtree(out_dir, ignore_errors=True)
            os.makedirs(out_dir, exist_ok=True)
    if isinstance(last_err, PasswordError) or last_err is None:
        raise PasswordError("password required (no working password found)")
    raise last_err


def _7z_extract_flat(path, dest, base, counter, passwords, log):
    created = []
    temp_dir = tempfile.mkdtemp(prefix="_unz7z_", dir=dest)
    try:
        _7z_extract_to(path, temp_dir, passwords)
        for root, _dirs, files in os.walk(temp_dir):
            for f in sorted(files):
                ext = os.path.splitext(f)[1]
                new_name = f"{base}_{counter:06d}{ext}"
                new_path = os.path.join(dest, new_name)
                shutil.move(os.path.join(root, f), new_path)
                log(f"    [7Z] Extracted: {new_name}", SUCCESS)
                counter += 1
                created.append(new_path)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    return counter, created


def _7z_test(path, passwords):
    last_err = None
    for pwd in [None] + passwords:
        try:
            with py7zr.SevenZipFile(path, mode="r", password=pwd) as zf:
                if zf.needs_password() and pwd is None:
                    last_err = PasswordError("password required")
                    continue
                result = zf.test()
            if result is False:
                raise RuntimeError("CRC check failed")
            return
        except (PasswordError, RuntimeError):
            raise
        except Exception as e:
            last_err = e
    if isinstance(last_err, PasswordError) or last_err is None:
        raise PasswordError("password required (no working password found)")
    raise last_err


def _tar_extract_flat(path, dest, base, counter, passwords, log):
    created = []
    with tarfile.open(path, "r:*") as tf:
        for member in tf.getmembers():
            if not member.isfile():
                continue
            ext = os.path.splitext(member.name)[1]
            new_name = f"{base}_{counter:06d}{ext}"
            new_path = os.path.join(dest, new_name)
            src = tf.extractfile(member)
            if src:
                with open(new_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                log(f"    [TAR.GZ] Extracted: {new_name}", SUCCESS)
                counter += 1
                created.append(new_path)
    return counter, created


def _tar_extract_structured(path, folder_path, passwords, log):
    with tarfile.open(path, "r:*") as tf:
        tf.extractall(folder_path, filter="data")


def _tar_test(path, passwords):
    with tarfile.open(path, "r:*") as tf:
        for member in tf.getmembers():
            if member.isfile():
                src = tf.extractfile(member)
                if src:
                    while src.read(1024 * 1024):
                        pass


def _rar_find_password(rf, passwords: list[str]) -> str | None:
    if not rf.needs_password():
        return None
    probe = next((i for i in rf.infolist() if not i.is_dir()), None)
    for pwd in passwords:
        try:
            rf.setpassword(pwd)
            if probe is not None:
                with rf.open(probe) as src:
                    src.read(16)
            return pwd
        except Exception:
            continue
    raise PasswordError("password required (no working password found)")


def _rar_extract_flat(path, dest, base, counter, passwords, log):
    created = []
    with rarfile.RarFile(path) as rf:
        _rar_find_password(rf, passwords)
        for info in rf.infolist():
            if info.is_dir():
                continue
            ext = os.path.splitext(info.filename)[1]
            new_name = f"{base}_{counter:06d}{ext}"
            new_path = os.path.join(dest, new_name)
            with rf.open(info) as src, open(new_path, "wb") as dst:
                shutil.copyfileobj(src, dst)
            log(f"    [RAR] Extracted: {new_name}", SUCCESS)
            counter += 1
            created.append(new_path)
    return counter, created


def _rar_extract_structured(path, folder_path, passwords, log):
    with rarfile.RarFile(path) as rf:
        _rar_find_password(rf, passwords)
        rf.extractall(folder_path)


def _rar_test(path, passwords):
    with rarfile.RarFile(path) as rf:
        _rar_find_password(rf, passwords)
        for info in rf.infolist():
            if not info.is_dir():
                with rf.open(info) as src:
                    while src.read(1024 * 1024):
                        pass


FLAT_HANDLERS = {
    "ZIP": _zip_extract_flat,
    "7Z": _7z_extract_flat,
    "TAR.GZ": _tar_extract_flat,
    "RAR": _rar_extract_flat,
}
STRUCT_HANDLERS = {
    "ZIP": _zip_extract_structured,
    "7Z": lambda p, f, pw, log: _7z_extract_to(p, f, pw),
    "TAR.GZ": _tar_extract_structured,
    "RAR": _rar_extract_structured,
}
TEST_HANDLERS = {
    "ZIP": _zip_test,
    "7Z": _7z_test,
    "TAR.GZ": _tar_test,
    "RAR": _rar_test,
}


def _format_available(tag: str, log) -> bool:
    if tag == "7Z" and not HAS_7Z:
        log("    [7Z] py7zr not installed — skipping .7z files", WARNING_COL)
        return False
    if tag == "RAR":
        if not HAS_RAR:
            log("    [RAR] rarfile not installed — skipping .rar files", WARNING_COL)
            return False
        if not RAR_TOOL:
            log("    [RAR] No RAR tool found (install WinRAR or 7-Zip) — skipping .rar files", WARNING_COL)
            return False
    return True


def _delete_archive(path: str, log):
    name = os.path.basename(path)
    try:
        if HAS_TRASH:
            send2trash(os.path.normpath(path))
            log(f"    Deleted (recycle bin): {name}", TEXT_DIM)
        else:
            os.remove(path)
            log(f"    Deleted: {name}", TEXT_DIM)
    except Exception as e:
        log(f"    Could not delete {name}: {e}", WARNING_COL)


def run_flat(source, dest, base_name, passwords, delete_after, nested, log) -> tuple[int, int]:
    """Flat-extract every archive in source into dest. Returns (ok, errors)."""
    archives = _list_archives(source)
    if not archives:
        log("No supported archives found in source folder.", ERROR_COL)
        return 0, 0

    log(f"Starting flat unzip — {len(archives)} archive(s) found…", ACCENT)
    counter, ok, errors = 1, 0, 0
    all_created = []

    for archive_file, tag in archives:
        if not _format_available(tag, log):
            continue
        archive_path = os.path.join(source, archive_file)
        log(f"  [{tag}] {archive_file}", TEXT_BRIGHT)
        try:
            counter, created = FLAT_HANDLERS[tag](archive_path, dest, base_name, counter, passwords, log)
            all_created.extend(created)
            ok += 1
            if delete_after:
                _delete_archive(archive_path, log)
        except Exception as e:
            errors += 1
            log(f"    [{tag}] Error extracting {archive_file}: {e}", ERROR_COL)

    if nested:
        counter, n_ok, n_err = _process_nested_flat(all_created, dest, base_name, counter, passwords, log)
        ok += n_ok
        errors += n_err

    log(f"Flat unzip completed — {ok} archive(s) extracted, {errors} error(s).",
        ACCENT if errors == 0 else WARNING_COL)
    return ok, errors


def _process_nested_flat(created_files, dest, base_name, counter, passwords, log):
    ok, errors, depth = 0, 0, 1
    pending = [f for f in created_files if _archive_type(os.path.basename(f))]
    while pending:
        if depth > MAX_NESTED_DEPTH:
            log(f"  Nested depth limit ({MAX_NESTED_DEPTH}) reached — "
                f"{len(pending)} archive(s) left as-is.", WARNING_COL)
            break
        log(f"  Nested pass {depth} — {len(pending)} archive(s)…", ACCENT)
        next_pending = []
        for arc in pending:
            tag = _archive_type(os.path.basename(arc))
            if not _format_available(tag, log):
                continue
            log(f"  [{tag}] (nested) {os.path.basename(arc)}", TEXT_BRIGHT)
            try:
                counter, created = FLAT_HANDLERS[tag](arc, dest, base_name, counter, passwords, log)
                ok += 1
                _delete_archive(arc, log)
                next_pending.extend(f for f in created if _archive_type(os.path.basename(f)))
            except Exception as e:
                errors += 1
                log(f"    [{tag}] Error extracting nested {os.path.basename(arc)}: {e}", ERROR_COL)
        pending = next_pending
        depth += 1
    return counter, ok, errors


def run_structured(source, dest, passwords, delete_after, nested, log) -> tuple[int, int]:
    """Extract each archive in source into its own subfolder of dest."""
    archives = _list_archives(source)
    if not archives:
        log("No supported archives found in source folder.", ERROR_COL)
        return 0, 0

    log(f"Starting structured unzip — {len(archives)} archive(s) found…", ACCENT)
    ok, errors = 0, 0

    for archive_file, tag in archives:
        if not _format_available(tag, log):
            continue
        archive_path = os.path.join(source, archive_file)
        folder_name = _unique_folder(dest, _strip_archive_ext(archive_file))
        folder_path = os.path.join(dest, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        try:
            STRUCT_HANDLERS[tag](archive_path, folder_path, passwords, log)
            log(f"  [{tag}] Extracted  {archive_file}  →  {folder_name}", SUCCESS)
            ok += 1
            if nested:
                n_ok, n_err = _process_nested_structured(folder_path, passwords, log, depth=1)
                ok += n_ok
                errors += n_err
            if delete_after:
                _delete_archive(archive_path, log)
        except Exception as e:
            errors += 1
            log(f"  [{tag}] Error extracting {archive_file}: {e}", ERROR_COL)

    log(f"Structured unzip completed — {ok} archive(s) extracted, {errors} error(s).",
        ACCENT if errors == 0 else WARNING_COL)
    return ok, errors


def _process_nested_structured(folder, passwords, log, depth):
    """Extract archives found inside folder into sibling subfolders, recursively."""
    ok, errors = 0, 0
    found = []
    for root, _dirs, files in os.walk(folder):
        for f in files:
            if _archive_type(f):
                found.append(os.path.join(root, f))
    if found and depth > MAX_NESTED_DEPTH:
        log(f"  Nested depth limit ({MAX_NESTED_DEPTH}) reached — "
            f"{len(found)} archive(s) left as-is.", WARNING_COL)
        return 0, 0
    for arc in found:
        tag = _archive_type(os.path.basename(arc))
        if not _format_available(tag, log):
            continue
        parent = os.path.dirname(arc)
        sub_name = _unique_folder(parent, _strip_archive_ext(os.path.basename(arc)))
        sub_path = os.path.join(parent, sub_name)
        os.makedirs(sub_path, exist_ok=True)
        try:
            STRUCT_HANDLERS[tag](arc, sub_path, passwords, log)
            log(f"  [{tag}] (nested, depth {depth}) Extracted  "
                f"{os.path.basename(arc)}  →  {sub_name}", SUCCESS)
            ok += 1
            _delete_archive(arc, log)
            n_ok, n_err = _process_nested_structured(sub_path, passwords, log, depth + 1)
            ok += n_ok
            errors += n_err
        except Exception as e:
            errors += 1
            log(f"  [{tag}] Error extracting nested {os.path.basename(arc)}: {e}", ERROR_COL)
    return ok, errors


def run_test(source, passwords, log) -> tuple[int, int]:
    """Verify every archive in source without extracting. Returns (ok, errors)."""
    archives = _list_archives(source)
    if not archives:
        log("No supported archives found in source folder.", ERROR_COL)
        return 0, 0

    log(f"Testing {len(archives)} archive(s) — nothing will be extracted…", ACCENT)
    ok, errors = 0, 0
    for archive_file, tag in archives:
        if not _format_available(tag, log):
            continue
        archive_path = os.path.join(source, archive_file)
        try:
            TEST_HANDLERS[tag](archive_path, passwords)
            log(f"  [{tag}] OK      {archive_file}", SUCCESS)
            ok += 1
        except Exception as e:
            errors += 1
            log(f"  [{tag}] FAILED  {archive_file}: {e}", ERROR_COL)
    log(f"Test completed — {ok} OK, {errors} failed.",
        ACCENT if errors == 0 else WARNING_COL)
    return ok, errors


class ExtractWorker(QThread):
    log_sig = pyqtSignal(str, str)
    done_sig = pyqtSignal()

    def __init__(self, mode, source, dest, base_name, passwords, delete_after, nested):
        super().__init__()
        self.mode = mode
        self.source = source
        self.dest = dest
        self.base_name = base_name
        self.passwords = passwords
        self.delete_after = delete_after
        self.nested = nested

    def run(self):
        log = self.log_sig.emit
        try:
            if self.mode == "flat":
                run_flat(self.source, self.dest, self.base_name,
                         self.passwords, self.delete_after, self.nested, log)
            elif self.mode == "struct":
                run_structured(self.source, self.dest,
                               self.passwords, self.delete_after, self.nested, log)
            elif self.mode == "test":
                run_test(self.source, self.passwords, log)
        except Exception as e:
            log(f"Unexpected error: {e}", ERROR_COL)
        self.done_sig.emit()


class SavedPasswordsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Saved Passwords")
        self.setFixedSize(340, 300)
        self.setStyleSheet(STYLESHEET)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Passwords tried automatically on encrypted archives:"))
        self.list_widget = QListWidget()
        for pwd in load_saved_passwords():
            self.list_widget.addItem(pwd)
        layout.addWidget(self.list_widget)
        btns = QHBoxLayout()
        btn_add = QPushButton("Add")
        btn_add.setObjectName("secondary")
        btn_add.clicked.connect(self.add_password)
        btn_remove = QPushButton("Remove")
        btn_remove.setObjectName("secondary")
        btn_remove.clicked.connect(self.remove_selected)
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        btns.addWidget(btn_add)
        btns.addWidget(btn_remove)
        btns.addStretch()
        btns.addWidget(btn_close)
        layout.addLayout(btns)

    def add_password(self):
        text, ok = QInputDialog.getText(self, "Add Password", "Password:")
        if ok and text:
            existing = [self.list_widget.item(i).text() for i in range(self.list_widget.count())]
            if text not in existing:
                self.list_widget.addItem(text)
                self._save()

    def remove_selected(self):
        for item in self.list_widget.selectedItems():
            self.list_widget.takeItem(self.list_widget.row(item))
        self._save()

    def _save(self):
        save_saved_passwords(
            [self.list_widget.item(i).text() for i in range(self.list_widget.count())])


class UnzipperApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Unzipper  V-{VERSION}")
        self.setFixedSize(660, 600)
        self.setStyleSheet(STYLESHEET)
        self.worker = None

        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Title bar
        titlebar = QFrame()
        titlebar.setObjectName("titlebar")
        titlebar.setFixedHeight(42)
        tb_layout = QHBoxLayout(titlebar)
        tb_layout.setContentsMargins(16, 0, 16, 0)
        lbl_title = QLabel("⚡  Unzipper")
        lbl_title.setObjectName("title")
        lbl_ver = QLabel(f"V-{VERSION}")
        lbl_ver.setObjectName("version")
        tb_layout.addWidget(lbl_title)
        tb_layout.addWidget(lbl_ver)
        tb_layout.addStretch()
        outer.addWidget(titlebar)

        # Body
        body = QWidget()
        body_layout = QGridLayout(body)
        body_layout.setContentsMargins(20, 14, 20, 14)
        body_layout.setSpacing(6)
        body_layout.setColumnStretch(0, 1)
        outer.addWidget(body)

        # Source row
        body_layout.addWidget(QLabel("Source Folder"), 0, 0, 1, 3)
        self.source_edit = QLineEdit()
        browse_src = QPushButton("Browse")
        browse_src.setFixedWidth(80)
        browse_src.setObjectName("secondary")
        browse_src.clicked.connect(self.browse_source)
        body_layout.addWidget(self.source_edit, 1, 0, 1, 2)
        body_layout.addWidget(browse_src, 1, 2)

        # Dest row
        body_layout.addWidget(QLabel("Destination Folder"), 2, 0, 1, 3)
        self.dest_edit = QLineEdit()
        browse_dst = QPushButton("Browse")
        browse_dst.setFixedWidth(80)
        browse_dst.setObjectName("secondary")
        browse_dst.clicked.connect(self.browse_dest)
        body_layout.addWidget(self.dest_edit, 3, 0, 1, 2)
        body_layout.addWidget(browse_dst, 3, 2)

        # Filename row
        body_layout.addWidget(QLabel("Filename  (Flat Unzip)"), 4, 0, 1, 3)
        self.filename_edit = QLineEdit("UnzippedFile")
        body_layout.addWidget(self.filename_edit, 5, 0, 1, 3)

        # Password row
        body_layout.addWidget(QLabel("Password  (optional — tried first on encrypted archives)"),
                              6, 0, 1, 3)
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Leave blank to use only saved passwords")
        btn_saved = QPushButton("Saved…")
        btn_saved.setFixedWidth(80)
        btn_saved.setObjectName("secondary")
        btn_saved.clicked.connect(self.manage_passwords)
        body_layout.addWidget(self.password_edit, 7, 0, 1, 2)
        body_layout.addWidget(btn_saved, 7, 2)

        # Options row
        opt_layout = QHBoxLayout()
        self.chk_delete = QCheckBox("Delete archives after successful extraction")
        self.chk_nested = QCheckBox("Extract nested archives")
        opt_layout.addWidget(self.chk_delete)
        opt_layout.addWidget(self.chk_nested)
        opt_layout.addStretch()
        body_layout.addLayout(opt_layout, 8, 0, 1, 3)

        # Action buttons
        btn_layout = QHBoxLayout()
        self.btn_flat = QPushButton("Unzip  —  Flat")
        self.btn_struct = QPushButton("Unzip  —  Keep Structure")
        self.btn_struct.setObjectName("secondary")
        self.btn_test = QPushButton("Test Archives")
        self.btn_test.setObjectName("secondary")
        self.btn_flat.clicked.connect(lambda: self.start_work("flat"))
        self.btn_struct.clicked.connect(lambda: self.start_work("struct"))
        self.btn_test.clicked.connect(lambda: self.start_work("test"))
        btn_layout.addWidget(self.btn_flat)
        btn_layout.addWidget(self.btn_struct)
        btn_layout.addWidget(self.btn_test)
        body_layout.addLayout(btn_layout, 9, 0, 1, 3)

        # Divider
        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFixedHeight(1)
        body_layout.addWidget(divider, 10, 0, 1, 3)

        # Status
        body_layout.addWidget(QLabel("Status"), 11, 0)
        self.status_box = QTextEdit()
        self.status_box.setReadOnly(True)
        body_layout.addWidget(self.status_box, 12, 0, 1, 3)
        body_layout.setRowStretch(12, 1)

        if HAS_RAR and not RAR_TOOL:
            self._log("Note: RAR support needs WinRAR or 7-Zip installed — "
                      ".rar files will be skipped.", WARNING_COL)

    def browse_source(self):
        existing = self.source_edit.text().strip()
        start = existing if existing and os.path.isdir(existing) else ""
        folder = QFileDialog.getExistingDirectory(self, "Select Source Folder", start)
        if folder:
            self.source_edit.setText(folder)

    def browse_dest(self):
        existing = self.dest_edit.text().strip()
        start = existing if existing and os.path.isdir(existing) else ""
        folder = QFileDialog.getExistingDirectory(self, "Select Destination Folder", start)
        if folder:
            self.dest_edit.setText(folder)

    def manage_passwords(self):
        SavedPasswordsDialog(self).exec()

    def _log(self, message: str, color: str = TEXT_BRIGHT):
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        cursor = self.status_box.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(message + "\n", fmt)
        self.status_box.setTextCursor(cursor)
        self.status_box.ensureCursorVisible()

    def _validate_folders(self, source: str, dest: str, need_dest: bool = True) -> bool:
        if not source or (need_dest and not dest):
            QMessageBox.critical(self, "Error", "Please select source and destination folders.")
            return False
        if not os.path.exists(source):
            QMessageBox.critical(self, "Error", f"Source folder does not exist:\n{source}")
            return False
        if need_dest and not os.path.exists(dest):
            os.makedirs(dest)
        return True

    def _gather_passwords(self) -> list[str]:
        passwords = []
        typed = self.password_edit.text()
        if typed:
            passwords.append(typed)
        for pwd in load_saved_passwords():
            if pwd not in passwords:
                passwords.append(pwd)
        return passwords

    def _set_running(self, running: bool):
        for btn in (self.btn_flat, self.btn_struct, self.btn_test):
            btn.setEnabled(not running)

    def start_work(self, mode: str):
        if self.worker is not None and self.worker.isRunning():
            return
        source = self.source_edit.text().strip()
        dest = self.dest_edit.text().strip()
        base_name = self.filename_edit.text().strip()

        if mode == "flat" and not base_name:
            QMessageBox.critical(self, "Error", "Please provide a filename for flat unzip.")
            return
        if not self._validate_folders(source, dest, need_dest=(mode != "test")):
            return

        self.worker = ExtractWorker(
            mode, source, dest, base_name,
            self._gather_passwords(),
            self.chk_delete.isChecked(),
            self.chk_nested.isChecked(),
        )
        self.worker.log_sig.connect(self._log)
        self.worker.done_sig.connect(lambda: self._set_running(False))
        self._set_running(True)
        self.worker.start()


def main():
    app = QApplication(sys.argv)
    window = UnzipperApp()
    icon_path = app_dir() / "app_icon.ico"
    if icon_path.exists():
        window.setWindowIcon(QIcon(str(icon_path)))
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
