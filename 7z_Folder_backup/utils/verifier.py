import hashlib
import os
import subprocess

CREATE_NO_WINDOW = 0x08000000


def run_integrity_test(seven_zip_path, archive_path, log_cb):
    log_cb("Running 7-Zip integrity test...")
    try:
        result = subprocess.run(
            [seven_zip_path, "t", archive_path],
            capture_output=True,
            text=True,
            creationflags=CREATE_NO_WINDOW,
        )
        if result.returncode == 0:
            log_cb("Integrity test passed.")
            return True
        log_cb(f"Integrity test FAILED (code {result.returncode})")
        for line in result.stdout.splitlines():
            if line.strip():
                log_cb(line.strip())
        return False
    except Exception as e:
        log_cb(f"Integrity test error: {e}")
        return False


def generate_sha256(archive_path, log_cb):
    log_cb("Generating SHA-256...")
    sha256 = hashlib.sha256()
    try:
        with open(archive_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        digest = sha256.hexdigest()
        hash_path = archive_path + ".sha256"
        with open(hash_path, "w") as f:
            f.write(f"{digest}  {os.path.basename(archive_path)}\n")
        log_cb(f"SHA-256: {digest[:20]}...{digest[-8:]}")
        log_cb(f"Hash file: {os.path.basename(hash_path)}")
        return digest
    except Exception as e:
        log_cb(f"SHA-256 error: {e}")
        return ""
