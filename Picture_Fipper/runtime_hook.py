"""
runtime_hook.py — Executed by PyInstaller before app code starts.

Redirects DEEPFACE_HOME so weights are found in the app's own folder
(deepface_weights/ next to the EXE) instead of the user's home dir.
"""
import os
import sys

if getattr(sys, 'frozen', False):
    # Running as PyInstaller bundle — EXE folder is sys._MEIPASS parent
    _app_dir = os.path.dirname(sys.executable)
    os.environ.setdefault('DEEPFACE_HOME', _app_dir)
    # deepface constructs:  <DEEPFACE_HOME>/.deepface/weights/<file>
    # So place weights at:  dist/PictureFlipper/.deepface/weights/
