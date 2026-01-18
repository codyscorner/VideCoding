"""Build script for creating the ImageDedupeSearch executable"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    # Get the directory where this script is located
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    print("Building ImageDedupeSearch executable...")
    print("=" * 50)

    # Run PyInstaller with the spec file
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--clean',
        '--noconfirm',
        'ImageDedupeSearch.spec'
    ]

    print(f"Running: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd)

    if result.returncode == 0:
        print()
        print("=" * 50)
        print("Build successful!")
        print(f"Executable located at: {script_dir / 'dist' / 'ImageDedupeSearch'}")
        print()
        print("To distribute, zip the 'dist/ImageDedupeSearch' folder.")
    else:
        print()
        print("Build failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()
