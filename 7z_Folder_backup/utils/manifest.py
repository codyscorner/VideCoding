import hashlib
import os


def compute_source_manifest(source_folder):
    """
    Hash the (relative path, size, mtime) of every file under source_folder.
    Cheap stat-only walk — no file content is read, so this stays fast even
    on large photo/video archives.
    """
    entries = []
    for root, dirs, files in os.walk(source_folder):
        dirs.sort()
        for name in sorted(files):
            full = os.path.join(root, name)
            try:
                st = os.stat(full)
            except OSError:
                continue
            rel = os.path.relpath(full, source_folder)
            entries.append(f"{rel}|{st.st_size}|{int(st.st_mtime)}")

    h = hashlib.sha256()
    for entry in entries:
        h.update(entry.encode("utf-8", errors="replace"))
        h.update(b"\n")
    return h.hexdigest()


def normalize_source_key(source_folder):
    return os.path.normcase(os.path.normpath(source_folder))
