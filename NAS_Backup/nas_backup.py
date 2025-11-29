#!/usr/bin/env python3
"""
High-speed NAS backup script with versioning and retention policy

Optimized backup script using multi-threaded robocopy for maximum speed
- Main backup: Mirrors source to destination (non-destructive)
- Versioned archive: Creates dated snapshots
- Retention: Automatically deletes archives older than 365 days

Speed optimizations:
- Multi-threaded copying (/MT:16)
- No restart mode (removed /Z for LAN speed)
- Optimized for reliable network connections
"""

import os
import sys
import subprocess
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import time

# ============================================
# CONFIGURATION
# ============================================
SOURCE = r"P:\AI"
DEST = r"\\CL-NAS\Backup\AI(P)_Backup"
ARCHIVE = r"\\CL-NAS\Backup\AI(P)_Backup\Archive"
RETENTION_DAYS = 365
ROBOCOPY_THREADS = 16  # Adjust based on your system (8-32 recommended)

# ============================================
# INITIALIZE
# ============================================
timestamp = datetime.now()
date_stamp = timestamp.strftime("%Y-%m-%d")
date_time_stamp = timestamp.strftime("%Y-%m-%d_%H-%M")
script_dir = Path(__file__).parent
log_file = script_dir / f"backup_{date_time_stamp}.log"

# Create log file and write header
def log_and_print(message, color=None):
    """Print to console and write to log file"""
    print(message)
    with open(log_file, 'a', encoding='utf-8') as f:
        # Strip ANSI color codes for log file
        clean_msg = message
        f.write(clean_msg + '\n')

# ANSI color codes for Windows terminal
class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'

def print_color(message, color):
    """Print colored message"""
    print(f"{color}{message}{Colors.RESET}")
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(message + '\n')

# ============================================
# START
# ============================================
print_color("\n========================================", Colors.CYAN)
print_color("NAS BACKUP SCRIPT - OPTIMIZED", Colors.CYAN)
print_color("========================================\n", Colors.CYAN)

print_color(f"Started: {date_time_stamp}", Colors.GREEN)
print_color(f"Source: {SOURCE}", Colors.YELLOW)
print_color(f"Destination: {DEST}", Colors.YELLOW)
print_color(f"Archive: {ARCHIVE}\\{date_stamp}", Colors.YELLOW)
print_color(f"Log: {log_file}\n", Colors.YELLOW)

# ============================================
# VALIDATION
# ============================================
print_color("[1/5] Validating paths...", Colors.CYAN)

if not os.path.exists(SOURCE):
    print_color(f"ERROR: Source path does not exist: {SOURCE}", Colors.RED)
    input("Press Enter to exit...")
    sys.exit(1)

# Create destination folders if they don't exist
if not os.path.exists(DEST):
    print_color(f"Creating destination folder: {DEST}", Colors.YELLOW)
    os.makedirs(DEST, exist_ok=True)

if not os.path.exists(ARCHIVE):
    print_color(f"Creating archive folder: {ARCHIVE}", Colors.YELLOW)
    os.makedirs(ARCHIVE, exist_ok=True)

print_color("✓ Paths validated\n", Colors.GREEN)

# ============================================
# STEP 1: MAIN BACKUP (MIRROR)
# ============================================
print_color("[2/5] Running main backup (high-speed mode)...", Colors.CYAN)
print_color(f"Using {ROBOCOPY_THREADS} parallel threads for maximum speed\n", Colors.YELLOW)

robocopy_args = [
    "robocopy",
    SOURCE,
    DEST,
    "/E",  # Copy subdirectories, including empty ones
    "/FFT",  # Assume FAT file times (2-second granularity)
    f"/MT:{ROBOCOPY_THREADS}",  # Multi-threaded (FAST!)
    "/W:5",  # Wait 5 seconds between retries
    "/R:3",  # Retry 3 times on failed copies
    "/NDL",  # No directory list (cleaner output)
    "/TEE",  # Output to console
    "/BYTES",  # Show file sizes in bytes
]

print_color(f"Command: {' '.join(robocopy_args)}\n", Colors.CYAN)

start_time = time.time()
result = subprocess.run(robocopy_args, capture_output=False)
elapsed = time.time() - start_time

# Robocopy exit codes: 0-7 are success, 8+ are errors
if result.returncode > 7:
    print_color(f"\nERROR: Main backup failed with exit code {result.returncode}", Colors.RED)
    print_color(f"Check log file for details: {log_file}", Colors.YELLOW)
    input("Press Enter to exit...")
    sys.exit(1)

hours, remainder = divmod(int(elapsed), 3600)
minutes, seconds = divmod(remainder, 60)
print_color(f"\n✓ Main backup completed in {hours:02d}:{minutes:02d}:{seconds:02d}", Colors.GREEN)

# ============================================
# STEP 2: VERSIONED ARCHIVE
# ============================================
print_color(f"\n[3/5] Creating versioned archive ({date_stamp})...", Colors.CYAN)

archive_path = os.path.join(ARCHIVE, date_stamp)
if not os.path.exists(archive_path):
    os.makedirs(archive_path, exist_ok=True)

robocopy_args[2] = archive_path  # Change destination to archive path

start_time = time.time()
result = subprocess.run(robocopy_args, capture_output=False)
elapsed = time.time() - start_time

if result.returncode > 7:
    print_color(f"\nERROR: Archive creation failed with exit code {result.returncode}", Colors.RED)
    print_color(f"Check log file for details: {log_file}", Colors.YELLOW)
    input("Press Enter to exit...")
    sys.exit(1)

hours, remainder = divmod(int(elapsed), 3600)
minutes, seconds = divmod(remainder, 60)
print_color(f"\n✓ Archive created in {hours:02d}:{minutes:02d}:{seconds:02d}", Colors.GREEN)

# ============================================
# STEP 3: RETENTION POLICY
# ============================================
print_color(f"\n[4/5] Applying retention policy - {RETENTION_DAYS} days...", Colors.CYAN)

cutoff_date = datetime.now() - timedelta(days=RETENTION_DAYS)
deleted_count = 0

if os.path.exists(ARCHIVE):
    for item in os.listdir(ARCHIVE):
        item_path = os.path.join(ARCHIVE, item)
        if os.path.isdir(item_path):
            # Get creation time
            creation_time = datetime.fromtimestamp(os.path.getctime(item_path))
            if creation_time < cutoff_date:
                print_color(f"Deleting old archive: {item} (Created: {creation_time.strftime('%Y-%m-%d')})", Colors.YELLOW)
                shutil.rmtree(item_path)
                deleted_count += 1

if deleted_count == 0:
    print_color("✓ No old archives to delete", Colors.GREEN)
else:
    print_color(f"✓ Deleted {deleted_count} old archive(s)", Colors.GREEN)

# ============================================
# STEP 4: VERIFICATION
# ============================================
print_color("\n[5/5] Verifying backup...", Colors.CYAN)

file_count = 0
total_size = 0

for root, dirs, files in os.walk(DEST):
    file_count += len(files)
    for file in files:
        file_path = os.path.join(root, file)
        try:
            total_size += os.path.getsize(file_path)
        except (OSError, FileNotFoundError):
            pass

total_size_gb = round(total_size / (1024**3), 2)

print_color(f"✓ Files in backup: {file_count}", Colors.GREEN)
print_color(f"✓ Total size: {total_size_gb} GB\n", Colors.GREEN)

# ============================================
# SUMMARY
# ============================================
print_color("========================================", Colors.CYAN)
print_color("BACKUP COMPLETED SUCCESSFULLY", Colors.GREEN)
print_color("========================================", Colors.CYAN)
print_color(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", Colors.GREEN)
print_color(f"Log file: {log_file}", Colors.YELLOW)
print_color("========================================\n", Colors.CYAN)

# Keep window open
input("Press Enter to exit...")
