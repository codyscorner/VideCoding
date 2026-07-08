Midnight Calculator v1.1.0
=========================

A fully functional desktop calculator with a Midnight Dark Blue theme,
built with Python and PyQt6.


FEATURES
--------
- Dark blue / navy UI (Midnight theme)
- Standard arithmetic: +, -, *, /
- Percentage (%) and sign toggle (+/-)
- Decimal point support
- Expression display above result
- Division-by-zero error handling
- Memory functions: MC, MR, M+, M-
- Comma-formatted number output
- Full keyboard input (digits, operators, Enter, Backspace, Esc)
- Calculation history panel — click any past result to reuse it
- Copy result to clipboard button
- Scientific mode: parentheses, square root (√), power (xʸ)


FILES
-----
  calculator.py         — Full source code (Python 3 / PyQt6)
  THEPLAN.md            — Original design specification
  Refrence Image.png    — UI reference screenshot
  dist/
    MidnightCalculator.exe  — Standalone Windows executable


REQUIREMENTS (to run from source)
----------------------------------
  Python 3.x
  PyQt6

  Install:  pip install PyQt6

  Run:      python calculator.py


BUILD EXE
---------
  pip install pyinstaller
  pyinstaller --onefile --windowed --name MidnightCalculator calculator.py


USAGE
-----
  - Click number buttons or use the keyboard to input values
  - Press an operator (+, -, *, /) to chain calculations
  - Press = (or Enter) to evaluate the expression
  - AC (or Esc) clears everything; Backspace deletes the last character
  - Memory buttons store and recall a value across calculations
  - "Hist" toggles the history panel — click a past entry to reuse its result
  - "Sci" toggles scientific mode: ( ) parentheses, √ square root, xʸ power
  - "Copy" copies the displayed result to the clipboard


VERSION HISTORY
---------------
  v1.0.0  2026-03-18  Initial release
  v1.1.0  2026-07-08  History panel, keyboard input, copy-to-clipboard, scientific mode


FUTURE ENHANCEMENTS
--------------------
  (none currently planned)
