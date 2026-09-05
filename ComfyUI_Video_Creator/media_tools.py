"""ffmpeg helpers: locate the binary, grab frames, probe, and concatenate."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

CREATE_NO_WINDOW = 0x08000000

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


def resolve_ffmpeg(configured: str, base_dir: Path) -> str:
    """Configured path if it exists → ffmpeg.exe next to the app → PATH."""
    configured = (configured or "").strip()
    if configured and Path(configured).exists():
        return configured
    bundled = base_dir / "ffmpeg.exe"
    if bundled.exists():
        return str(bundled)
    return "ffmpeg"


def _run(cmd: list[str], timeout: int | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout,
        creationflags=CREATE_NO_WINDOW, encoding="utf-8", errors="replace",
    )


def extract_last_frame(ffmpeg: str, video: Path, dst: Path) -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    r = _run([ffmpeg, "-y", "-sseof", "-0.1", "-i", str(video), "-vframes", "1", "-q:v", "2", str(dst)])
    if r.returncode != 0 or not dst.exists():
        # Very short clips can fail the seek-from-end; fall back to decoding
        # everything and keeping the final frame.
        r = _run([ffmpeg, "-y", "-i", str(video), "-vf", "reverse", "-vframes", "1", "-q:v", "2", str(dst)])
    if r.returncode != 0 or not dst.exists():
        raise RuntimeError(f"ffmpeg could not extract the last frame of {video.name}:\n{r.stderr[-2000:]}")
    return dst


def extract_thumbnail(ffmpeg: str, video: Path, dst: Path) -> bool:
    try:
        r = _run([ffmpeg, "-y", "-i", str(video), "-vframes", "1", "-q:v", "3", str(dst)], timeout=20)
        return r.returncode == 0 and dst.exists()
    except Exception:
        return False


@dataclass
class VideoProps:
    width: int = 0
    height: int = 0
    fps: float = 0.0
    has_audio: bool = False
    duration: float = 0.0


_RES_RE = re.compile(r"Video:.*?\s(\d{2,5})x(\d{2,5})")
_FPS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*fps")
_DUR_RE = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")


def probe(ffmpeg: str, path: Path) -> VideoProps:
    """Parse ffmpeg's own stream dump so we don't depend on ffprobe."""
    p = VideoProps()
    try:
        r = _run([ffmpeg, "-hide_banner", "-i", str(path)], timeout=30)
    except Exception:
        return p
    text = r.stderr or ""
    m = _RES_RE.search(text)
    if m:
        p.width, p.height = int(m.group(1)), int(m.group(2))
    m = _FPS_RE.search(text)
    if m:
        p.fps = float(m.group(1))
    m = _DUR_RE.search(text)
    if m:
        p.duration = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    p.has_audio = "Audio:" in text
    return p


def concat_videos(ffmpeg: str, parts: list[Path], out_path: Path) -> Path:
    """Append clips back-to-back, normalizing every input to the first
    clip's size/fps/SAR so mixed sources don't warp. Audio is kept only
    when every part has a track (MiniMax H3 clips do, WAN clips don't)."""
    n = len(parts)
    if n == 0:
        raise ValueError("nothing to concatenate")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    first = probe(ffmpeg, parts[0])
    inputs: list[str] = []
    for p in parts:
        inputs += ["-i", str(p)]

    if first.width and first.height and first.fps:
        norm = f"scale={first.width}:{first.height}:flags=lanczos,setsar=1,fps={first.fps:g},format=yuv420p"
        filter_v = "".join(f"[{i}:v]{norm}[v{i}];" for i in range(n))
        concat_v = "".join(f"[v{i}]" for i in range(n))
    else:
        filter_v = ""
        concat_v = "".join(f"[{i}:v]" for i in range(n))

    has_audio = all(probe(ffmpeg, p).has_audio for p in parts)
    if has_audio:
        filter_a = "".join(f"[{i}:a]" for i in range(n))
        filter_complex = f"{filter_v}{concat_v}{filter_a}concat=n={n}:v=1:a=1[out][outa]"
        map_args = ["-map", "[out]", "-map", "[outa]"]
        audio_args = ["-c:a", "aac", "-b:a", "192k"]
    else:
        filter_complex = f"{filter_v}{concat_v}concat=n={n}:v=1[out]"
        map_args = ["-map", "[out]"]
        audio_args = ["-an"]

    r = _run(
        [ffmpeg, "-y"] + inputs + ["-filter_complex", filter_complex] + map_args
        + ["-c:v", "libx264", "-preset", "fast", "-crf", "18", "-movflags", "+faststart"]
        + audio_args + [str(out_path)]
    )
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg concat failed:\n{r.stderr[-3000:]}")
    return out_path
