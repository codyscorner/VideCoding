"""Audio alert for events worth walking back to the desk for.

Same approach as the Chain Automator's completion sound: winsound for .wav
(synchronous API, so it runs on a daemon thread and never blocks the UI), and
the shell's default handler for anything else. Failures are swallowed — a
missing or unplayable sound file must never take down whatever it was
announcing.
"""

from __future__ import annotations

import threading
from pathlib import Path

WAV_FILTER = "Audio Files (*.wav *.mp3 *.ogg *.flac *.aac *.m4a *.wma);;All Files (*)"


def play(path: str) -> bool:
    """Fire-and-forget. Returns False when there's nothing playable to try."""
    path = (path or "").strip()
    if not path:
        return False
    sound = Path(path)
    if not sound.exists():
        return False

    def _run():
        try:
            if sound.suffix.lower() == ".wav":
                import winsound
                winsound.PlaySound(str(sound), winsound.SND_FILENAME)
            else:
                import os
                os.startfile(str(sound))     # noqa: S606 — user-chosen file
        except Exception:                     # noqa: BLE001
            pass

    threading.Thread(target=_run, daemon=True).start()
    return True
