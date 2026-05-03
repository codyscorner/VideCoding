import os
from datetime import datetime


def create_log_file(app_dir):
    logs_dir = os.path.join(app_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
    log_path = os.path.join(logs_dir, f"backup_{timestamp}.log")
    with open(log_path, "w") as f:
        f.write(f"Photo Archive Backup Log\n")
        f.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 50 + "\n")
    return log_path


def write_log(log_path, message):
    ts = datetime.now().strftime("%H:%M:%S")
    with open(log_path, "a") as f:
        f.write(f"[{ts}] {message}\n")
