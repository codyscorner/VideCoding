# Midnight Calculator

A fully functional desktop calculator with a Midnight Dark Blue theme, built with Python and PyQt6.

## Features

- Dark blue / navy UI (Midnight theme)
- Standard arithmetic: +, -, *, /
- Percentage (%) and sign toggle (+/-)
- Decimal point support
- Expression display above result
- Division-by-zero error handling
- Memory functions: MC, MR, M+, M-
- Comma-formatted number output

## Requirements

```
Python 3.x
PyQt6
```

```bash
pip install PyQt6
```

## Usage

```bash
python calculator.py
```

Or run the standalone `dist/MidnightCalculator.exe` — no Python required.

## Build EXE

```bash
pip install pyinstaller
pyinstaller MidnightCalculator.spec
```

## Version History

| Version | Date | Notes |
|---------|------|-------|
| v1.0.0 | 2026-03-18 | Initial release |
