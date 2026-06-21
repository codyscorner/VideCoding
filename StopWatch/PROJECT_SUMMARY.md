# StopWatch

**Version:** 1.0.0 | **Status:** Active | **Language:** Python

A desktop stopwatch and countdown timer app with sound alerts, built with PyQt6 and pygame for audio.

## Features

- **Stopwatch tab**: Start, pause, reset; lap time recording; session log display
- **Countdown timer tab**: Set hours/minutes/seconds; plays a sound alert when time expires
- Dark purple-themed UI
- Standalone EXE via PyInstaller

## Tech Stack

- Python 3.10+
- PyQt6
- pygame (sound playback)

## Files

```
StopWatch/
├── stopwatch.py        — Main application
├── build_stopwatch.bat — PyInstaller build script
└── app_icon.ico
```

## Building

```bash
build_stopwatch.bat
```
