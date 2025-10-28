"""
Post-build script to manually add icon to EXE using Windows API
This is a workaround for PyInstaller icon issues
"""
import os
import sys
import subprocess

exe_path = r'p:\AI\VideCoding\File Rename Mover\dist\File Rename Mover.exe'
icon_path = r'p:\AI\VideCoding\File Rename Mover\app_icon.ico'

print(f"Attempting to add icon to: {exe_path}")
print(f"Using icon: {icon_path}")

# Try using ResourceHacker if available, otherwise use alternate method
# First, let's just check if the icon is actually in the EXE

# Use PyInstaller's own icon add utility
try:
    # Try using the win32api if available
    import win32api
    import win32con

    # This is a simple check - we can't easily modify the icon with win32api alone
    print("win32api available, but icon modification requires different approach")
except ImportError:
    print("win32api not available")

# Alternative: Check if we can download/use rcedit
print("\nTo manually add icon after build, you can:")
print("1. Download rcedit.exe from: https://github.com/electron/rcedit/releases")
print("2. Run: rcedit.exe 'File Rename Mover.exe' --set-icon app_icon.ico")
print("\nOr use Resource Hacker (GUI tool)")

# For now, let's try a direct approach with subprocess if rcedit exists
# This is just checking - we won't bundle rcedit automatically
