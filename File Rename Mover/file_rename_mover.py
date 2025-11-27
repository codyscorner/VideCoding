"""
File Rename Mover - Legacy Entry Point

This file is kept for backward compatibility.
The application has been refactored into a modular structure.

New structure:
- main.py: New entry point
- config.py: Configuration management
- file_operations.py: File handling logic
- ui/: UI components (main_window, settings_dialog, styles)

To run the application, use: python main.py
"""

# Import the main function from the new entry point
from main import main

# Keep old VERSION for reference
VERSION = "2.1.2"  # Updated to reflect refactoring

if __name__ == "__main__":
    print("Note: This file is now a legacy entry point.")
    print("The application has been refactored into modular components.")
    print("Consider using 'python main.py' in the future.\n")
    print("Starting application...\n")
    main()
