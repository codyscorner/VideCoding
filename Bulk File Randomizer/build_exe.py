"""Build script for Bulk File Randomizer executable"""

import os
import subprocess
import sys
from pathlib import Path


def main():
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    app_name = "BulkFileRandomizer"
    icon_path = script_dir / "app_icon.ico"

    print(f"Building {app_name} executable...")
    print("=" * 50)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        "--onedir",
        "--windowed",
        f"--name={app_name}",
        "--add-data=ui;ui",
    ]

    if icon_path.exists():
        cmd += [f"--icon={icon_path}"]

    cmd.append("main.py")

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        print()
        print("=" * 50)
        print("Build successful!")
        print(f"Executable: {script_dir / 'dist' / app_name / f'{app_name}.exe'}")
    else:
        print("Build failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
