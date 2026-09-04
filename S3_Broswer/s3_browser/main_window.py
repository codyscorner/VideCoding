import os
from pathlib import Path

from PyQt6.QtCore import Qt, QMimeData
from PyQt6.QtGui import QAction, QDragEnterEvent, QDropEvent, QIcon, QKeySequence
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from . import config as cfg
from . import __version__
from .s3_client import S3Client, S3Entry
from .settings_dialog import SettingsDialog
from .workers import ActionWorker, TransferJob, TransferWorker

COL_NAME, COL_SIZE, COL_TYPE, COL_MODIFIED = range(4)


def human_size(num: int) -> str:
    size = float(num)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


class NumericItem(QTableWidgetItem):
    def __init__(self, text: str, sort_value):
        super().__init__(text)
        self.sort_value = sort_value

    def __lt__(self, other):
        if isinstance(other, NumericItem):
            return self.sort_value < other.sort_value
        return super().__lt__(other)


class S3Table(QTableWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent):
        mime: QMimeData = event.mimeData()
        if mime.hasUrls():
            local_paths = [url.toLocalFile() for url in mime.urls() if url.isLocalFile()]
            if local_paths:
                self.main_window.upload_paths(local_paths)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"S3 Browser v{__version__}")
        self.resize(1000, 640)

        self.config = cfg.load_config()
        self.client: S3Client | None = None
        self.current_prefix = ""
        self.entries: list[S3Entry] = []

        self._build_ui()
        self._connect_client(initial=True)

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        style = self.style()

        self.act_up = QAction(style.standardIcon(QStyle.StandardPixmap.SP_ArrowUp), "Up", self)
        self.act_up.triggered.connect(self.navigate_up)
        toolbar.addAction(self.act_up)

        self.act_refresh = QAction(style.standardIcon(QStyle.StandardPixmap.SP_BrowserReload), "Refresh", self)
        self.act_refresh.setShortcut(QKeySequence("F5"))
        self.act_refresh.triggered.connect(self.refresh)
        toolbar.addAction(self.act_refresh)

        toolbar.addSeparator()

        self.act_new_folder = QAction(style.standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder), "New Folder", self)
        self.act_new_folder.triggered.connect(self.new_folder)
        toolbar.addAction(self.act_new_folder)

        self.act_upload_files = QAction("Upload Files...", self)
        self.act_upload_files.triggered.connect(self.upload_files_dialog)
        toolbar.addAction(self.act_upload_files)

        self.act_upload_folder = QAction("Upload Folder...", self)
        self.act_upload_folder.triggered.connect(self.upload_folder_dialog)
        toolbar.addAction(self.act_upload_folder)

        self.act_download = QAction(style.standardIcon(QStyle.StandardPixmap.SP_ArrowDown), "Download", self)
        self.act_download.triggered.connect(self.download_selected)
        toolbar.addAction(self.act_download)

        self.act_rename = QAction("Rename", self)
        self.act_rename.setShortcut(QKeySequence("F2"))
        self.act_rename.triggered.connect(self.rename_selected)
        toolbar.addAction(self.act_rename)

        self.act_delete = QAction(style.standardIcon(QStyle.StandardPixmap.SP_TrashIcon), "Delete", self)
        self.act_delete.setShortcut(QKeySequence("Delete"))
        self.act_delete.triggered.connect(self.delete_selected)
        toolbar.addAction(self.act_delete)

        toolbar.addSeparator()

        self.act_settings = QAction(style.standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView), "Settings", self)
        self.act_settings.triggered.connect(self.open_settings)
        toolbar.addAction(self.act_settings)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(6, 6, 6, 6)

        self.breadcrumb_widget = QWidget()
        self.breadcrumb_layout = QHBoxLayout(self.breadcrumb_widget)
        self.breadcrumb_layout.setContentsMargins(0, 0, 0, 0)
        self.breadcrumb_layout.addStretch(1)
        layout.addWidget(self.breadcrumb_widget)

        self.table = S3Table(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Name", "Size", "Type", "Last Modified"])
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(COL_NAME, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(COL_SIZE, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(COL_TYPE, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(COL_MODIFIED, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(COL_SIZE, 90)
        self.table.setColumnWidth(COL_TYPE, 70)
        self.table.setColumnWidth(COL_MODIFIED, 160)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)
        self.table.doubleClicked.connect(self._on_double_click)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.table)

        self.setCentralWidget(central)
        self.status = self.statusBar()
        self.status.showMessage("Connecting...")

    def _rebuild_breadcrumb(self):
        while self.breadcrumb_layout.count():
            item = self.breadcrumb_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        bucket_name = self.config.get("bucket_name", "bucket")
        root_btn = QPushButton(bucket_name)
        root_btn.setFlat(True)
        root_btn.clicked.connect(lambda: self.navigate(""))
        self.breadcrumb_layout.addWidget(root_btn)

        parts = [p for p in self.current_prefix.split("/") if p]
        accum = ""
        for part in parts:
            sep = QLabel("/")
            self.breadcrumb_layout.addWidget(sep)
            accum += part + "/"
            target = accum
            btn = QPushButton(part)
            btn.setFlat(True)
            btn.clicked.connect(lambda checked=False, p=target: self.navigate(p))
            self.breadcrumb_layout.addWidget(btn)
        self.breadcrumb_layout.addStretch(1)

    # -------------------------------------------------------------- client
    def _connect_client(self, initial=False):
        if not cfg.has_credentials(self.config["profile_name"]):
            if not self._prompt_settings():
                if initial:
                    QApplication.quit()
                return
        try:
            self.client = S3Client(
                profile_name=self.config["profile_name"],
                region=self.config["region"],
                endpoint_url=self.config["endpoint_url"],
                bucket_name=self.config["bucket_name"],
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Connection error", str(exc))
            return

        self.status.showMessage("Connecting...")
        worker = ActionWorker(self.client.test_connection)
        worker.finished.connect(lambda _: self._on_connected())
        worker.error.connect(self._on_connect_error)
        self._keep(worker)
        worker.start()

    def _on_connected(self):
        self.status.showMessage(f"Connected to {self.config['bucket_name']}")
        self.navigate("")

    def _on_connect_error(self, message: str):
        QMessageBox.critical(self, "Connection failed", message)
        self.status.showMessage("Not connected")
        self._prompt_settings()

    def _prompt_settings(self) -> bool:
        dlg = SettingsDialog(self.config, self)
        if dlg.exec():
            self.config = dlg.result_config
            self._connect_client()
            return True
        return False

    def open_settings(self):
        dlg = SettingsDialog(self.config, self)
        if dlg.exec():
            self.config = dlg.result_config
            self._connect_client()

    # ------------------------------------------------------------ navigate
    def navigate(self, prefix: str):
        self.current_prefix = prefix
        self._rebuild_breadcrumb()
        self.refresh()

    def navigate_up(self):
        if not self.current_prefix:
            return
        parts = self.current_prefix.rstrip("/").split("/")[:-1]
        parent = "/".join(parts)
        self.navigate(parent + "/" if parent else "")

    def refresh(self):
        if not self.client:
            return
        self.status.showMessage("Loading...")
        worker = ActionWorker(self.client.list_entries, self.current_prefix)
        worker.finished.connect(self._on_entries_loaded)
        worker.error.connect(lambda msg: QMessageBox.critical(self, "Error listing objects", msg))
        self._keep(worker)
        worker.start()

    def _on_entries_loaded(self, entries: list[S3Entry]):
        self.entries = entries
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for entry in sorted(entries, key=lambda e: (not e.is_folder, e.name.lower())):
            row = self.table.rowCount()
            self.table.insertRow(row)

            name_item = QTableWidgetItem(entry.name)
            icon = self.style().standardIcon(
                QStyle.StandardPixmap.SP_DirIcon if entry.is_folder else QStyle.StandardPixmap.SP_FileIcon
            )
            name_item.setIcon(icon)
            name_item.setData(Qt.ItemDataRole.UserRole, entry)
            self.table.setItem(row, COL_NAME, name_item)

            size_text = "" if entry.is_folder else human_size(entry.size)
            self.table.setItem(row, COL_SIZE, NumericItem(size_text, 0 if entry.is_folder else entry.size))

            self.table.setItem(row, COL_TYPE, QTableWidgetItem("Folder" if entry.is_folder else "File"))

            mod_text = "" if entry.last_modified is None else entry.last_modified.strftime("%Y-%m-%d %H:%M")
            sort_val = 0 if entry.last_modified is None else entry.last_modified.timestamp()
            self.table.setItem(row, COL_MODIFIED, NumericItem(mod_text, sort_val))

        self.table.setSortingEnabled(True)
        self.status.showMessage(
            f"{self.config['bucket_name']}/{self.current_prefix}  —  {len(entries)} item(s)"
        )

    def _on_double_click(self, index):
        row = index.row()
        entry: S3Entry = self.table.item(row, COL_NAME).data(Qt.ItemDataRole.UserRole)
        if entry.is_folder:
            self.navigate(entry.key)
        else:
            self.download_entries([entry])

    def _selected_entries(self) -> list[S3Entry]:
        rows = {idx.row() for idx in self.table.selectedIndexes()}
        return [self.table.item(r, COL_NAME).data(Qt.ItemDataRole.UserRole) for r in rows]

    # --------------------------------------------------------- context menu
    def _show_context_menu(self, pos):
        selected = self._selected_entries()
        menu = QMenu(self)
        if selected:
            act_dl = menu.addAction("Download...")
            act_dl.triggered.connect(lambda: self.download_entries(selected))
            if len(selected) == 1:
                act_ren = menu.addAction("Rename...")
                act_ren.triggered.connect(self.rename_selected)
                act_copy = menu.addAction("Copy S3 Path")
                act_copy.triggered.connect(lambda: self._copy_s3_path(selected[0]))
            menu.addSeparator()
            act_del = menu.addAction("Delete")
            act_del.triggered.connect(self.delete_selected)
        else:
            act_new = menu.addAction("New Folder...")
            act_new.triggered.connect(self.new_folder)
            act_uf = menu.addAction("Upload Files...")
            act_uf.triggered.connect(self.upload_files_dialog)
            act_ud = menu.addAction("Upload Folder...")
            act_ud.triggered.connect(self.upload_folder_dialog)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _copy_s3_path(self, entry: S3Entry):
        QApplication.clipboard().setText(f"s3://{self.config['bucket_name']}/{entry.key}")

    # -------------------------------------------------------------- create
    def new_folder(self):
        name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")
        if not ok or not name.strip():
            return
        name = name.strip().strip("/")
        key = f"{self.current_prefix}{name}/"
        worker = ActionWorker(self.client.create_folder, key)
        worker.finished.connect(lambda _: self.refresh())
        worker.error.connect(lambda msg: QMessageBox.critical(self, "Error creating folder", msg))
        self._keep(worker)
        worker.start()

    # -------------------------------------------------------------- upload
    def upload_files_dialog(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Select files to upload")
        if paths:
            self.upload_paths(paths)

    def upload_folder_dialog(self):
        path = QFileDialog.getExistingDirectory(self, "Select folder to upload")
        if path:
            self.upload_paths([path])

    def upload_paths(self, local_paths: list[str]):
        jobs: list[TransferJob] = []
        for path in local_paths:
            p = Path(path)
            if p.is_dir():
                base_key = f"{self.current_prefix}{p.name}/"
                for root, _dirs, files in os.walk(p):
                    for fname in files:
                        fpath = Path(root) / fname
                        rel = fpath.relative_to(p).as_posix()
                        key = base_key + rel
                        jobs.append(TransferJob(str(fpath), key, fpath.stat().st_size, "upload", fpath.name))
            elif p.is_file():
                key = f"{self.current_prefix}{p.name}"
                jobs.append(TransferJob(str(p), key, p.stat().st_size, "upload", p.name))
        if jobs:
            self._run_transfer(jobs, "Uploading")

    # ------------------------------------------------------------ download
    def download_selected(self):
        selected = self._selected_entries()
        if not selected:
            QMessageBox.information(self, "Download", "Select one or more items first.")
            return
        self.download_entries(selected)

    def download_entries(self, entries: list[S3Entry]):
        dest_dir = QFileDialog.getExistingDirectory(self, "Choose download destination")
        if not dest_dir:
            return
        jobs: list[TransferJob] = []
        for entry in entries:
            if entry.is_folder:
                for key, size, etag in self.client.list_all_files(entry.key):
                    rel = key[len(entry.key):]
                    local_path = os.path.join(dest_dir, entry.name, *rel.split("/"))
                    jobs.append(
                        TransferJob(local_path, key, size, "download", os.path.basename(local_path), etag=etag)
                    )
            else:
                local_path = os.path.join(dest_dir, entry.name)
                jobs.append(TransferJob(local_path, entry.key, entry.size, "download", entry.name, etag=entry.etag))
        if jobs:
            self._run_transfer(jobs, "Downloading")

    # -------------------------------------------------------------- delete
    def delete_selected(self):
        selected = self._selected_entries()
        if not selected:
            return
        names = ", ".join(e.name for e in selected[:5])
        if len(selected) > 5:
            names += f", and {len(selected) - 5} more"
        reply = QMessageBox.question(
            self,
            "Confirm delete",
            f"Permanently delete {names}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        def do_delete():
            file_keys = [e.key for e in selected if not e.is_folder]
            self.client.delete_keys(file_keys)
            for entry in selected:
                if entry.is_folder:
                    self.client.delete_prefix(entry.key)

        self.status.showMessage("Deleting...")
        worker = ActionWorker(do_delete)
        worker.finished.connect(lambda _: self.refresh())
        worker.error.connect(lambda msg: QMessageBox.critical(self, "Error deleting", msg))
        self._keep(worker)
        worker.start()

    # -------------------------------------------------------------- rename
    def rename_selected(self):
        selected = self._selected_entries()
        if len(selected) != 1:
            QMessageBox.information(self, "Rename", "Select exactly one item to rename.")
            return
        entry = selected[0]
        new_name, ok = QInputDialog.getText(self, "Rename", "New name:", text=entry.name)
        if not ok or not new_name.strip() or new_name.strip() == entry.name:
            return
        new_name = new_name.strip().strip("/")

        def do_rename():
            if entry.is_folder:
                new_prefix = f"{self.current_prefix}{new_name}/"
                old_keys = self.client.list_all_keys(entry.key)
                for key in old_keys:
                    rel = key[len(entry.key):]
                    self.client.copy_key(key, new_prefix + rel)
                self.client.delete_prefix(entry.key)
            else:
                new_key = f"{self.current_prefix}{new_name}"
                self.client.copy_key(entry.key, new_key)
                self.client.delete_keys([entry.key])

        self.status.showMessage("Renaming...")
        worker = ActionWorker(do_rename)
        worker.finished.connect(lambda _: self.refresh())
        worker.error.connect(lambda msg: QMessageBox.critical(self, "Error renaming", msg))
        self._keep(worker)
        worker.start()

    # ------------------------------------------------------------ transfer
    def _run_transfer(self, jobs: list[TransferJob], verb: str):
        progress = QProgressDialog(f"{verb}...", "Cancel", 0, 100, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setAutoClose(True)

        worker = TransferWorker(self.client, jobs)

        def on_progress(bytes_done, bytes_total, filename, files_done, files_total):
            pct = int(bytes_done * 100 / bytes_total) if bytes_total else 100
            progress.setValue(pct)
            progress.setLabelText(f"{verb} {filename}  ({files_done}/{files_total} files)")

        def on_merging(filename):
            progress.setLabelText(
                f"All data sent — waiting on S3 to merge {filename}.\n"
                "No transfer progress during this step; large files\n"
                "can take several minutes. Please be patient."
            )

        def on_merging_status(filename, tmp_bytes, elapsed):
            mins, secs = divmod(elapsed, 60)
            if tmp_bytes >= 0:
                detail = f"S3 merge file present ({human_size(tmp_bytes)}) — still merging"
            else:
                detail = "S3 merge file no longer listed — finishing up"
            progress.setLabelText(
                f"All data sent — waiting on S3 to merge {filename}.\n"
                f"{detail}  ·  {mins}m {secs:02d}s elapsed.\n"
                "No transfer progress during this step. Please be patient."
            )

        def on_finished(errors):
            progress.setValue(100)
            if errors:
                detail = "\n".join(f"{k}: {e}" for k, e in errors[:10])
                QMessageBox.warning(self, f"{verb} completed with errors", detail)
            if worker.skipped or worker.renamed:
                parts = []
                if worker.skipped:
                    names = worker.skipped[:15]
                    if len(worker.skipped) > 15:
                        names.append(f"... and {len(worker.skipped) - 15} more")
                    parts.append(
                        f"{len(worker.skipped)} file(s) skipped - an identical copy (same size and MD5) "
                        "was already in the destination:" + '\n\n' + '\n'.join(names)
                    )
                if worker.renamed:
                    lines = [f"{orig}  ->  {os.path.basename(new)}" for orig, new in worker.renamed[:15]]
                    if len(worker.renamed) > 15:
                        lines.append(f"... and {len(worker.renamed) - 15} more")
                    parts.append(
                        f"{len(worker.renamed)} file(s) had a different file with the same name in the "
                        "destination and were saved under a new name instead of overwriting it:"
                        + '\n\n' + '\n'.join(lines)
                    )
                QMessageBox.information(self, "Existing files", '\n\n'.join(parts))
            self.refresh()

        worker.progress.connect(on_progress)
        worker.merging.connect(on_merging)
        worker.merging_status.connect(on_merging_status)
        worker.finished.connect(on_finished)
        progress.canceled.connect(worker.cancel)
        self._keep(worker)
        worker.start()

    # -------------------------------------------------------------- helper
    def _keep(self, worker):
        """Prevent QThread objects from being garbage-collected mid-run."""
        if not hasattr(self, "_workers"):
            self._workers = []
        self._workers = [w for w in self._workers if w.isRunning()]
        self._workers.append(worker)
