# Task: Create a Dark Blue PyQt6 Calculator

## Objective
Develop a fully functional desktop calculator application using Python and PyQt6 with a specific "Midnight Dark Blue" theme.

## Technical Specifications
- **Language:** Python 3.x
- **GUI Framework:** PyQt6
- **Theme:** Dark Blue / Navy palette
    - Background: `#1b1e23` or `#12122b`
    - Display: `#252932` with light text
    - Accent/Buttons: `#3d5afe` or `#1e88e5`
    - Hover effects: Subtle lighting changes

## Core Features
1.  **Display:** A digital readout at the top for results and current input.
2.  **Keypad:**
    - Standard digits (0-9).
    - Basic operations (+, -, *, /).
    - Advanced functions: Clear (C), Delete (DEL), Percentage (%), and Equals (=).
3.  **Layout:**
    - Use `QVBoxLayout` for the main container.
    - Use `QGridLayout` for the button matrix.
4.  **Logic:**
    - Handle decimal point precision.
    - Prevent division by zero errors with a friendly message.
    - Ensure the UI is responsive (fixed size is fine, e.g., 350x500px).
    - include a memory funtionallity as well.

## Code Quality Requirements
- Use a Class-based approach (inheriting from `QMainWindow`).
- Implement the styling via **PyQt QSS (Qt Style Sheets)** to keep logic and design separate.
- Include comments explaining the button connection logic.

## Final Output
Please provide the complete `calculator.py` code.
And compile and EXE