Midnight Calculator v1.0.0
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
  - Click number buttons or use keyboard to input values
  - Press an operator (+, -, *, /) to chain calculations
  - Press = to evaluate the expression
  - AC clears everything
  - Memory buttons store and recall a value across calculations


VERSION HISTORY
---------------
  v1.0.0  2026-03-18  Initial release


FUTURE ENHANCEMENTS
--------------------
  - Calculation history panel (click to reuse a result)
  - Keyboard input support (if not already complete)
  - Copy result to clipboard button
  - Scientific mode (sqrt, exponents, parentheses)
