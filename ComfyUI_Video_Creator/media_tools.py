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
    r = _run([ffmpeg, "-y", "-sseof", "-0.1", "-i", str(video), "-vframes", "1", "-q:v", "2", str(dst)],
             timeout=30)
    if r.returncode != 0 or not dst.exists():
        # Very short clips can fail the seek-from-end; fall back to decoding
        # everything and keeping the final frame.
        r = _run([ffmpeg, "-y", "-i", str(video), "-vf", "reverse", "-vframes", "1", "-q:v", "2", str(dst)],
                 timeout=60)
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
    vcodec: str = ""          # ffmpeg's name: h264, hevc, av1, vp9, prores...


_RES_RE = re.compile(r"Video:.*?\s(\d{2,5})x(\d{2,5})")
_VCODEC_RE = re.compile(r"Video:\s*([A-Za-z0-9_]+)")
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
    m = _VCODEC_RE.search(text)
    if m:
        p.vcodec = m.group(1).lower()
    p.has_audio = "Audio:" in text
    return p


AUDIO_RATE = 48000
AUDIO_NORM = (
    f"aresample=async=1:first_pts=0,"
    f"aformat=sample_fmts=fltp:sample_rates={AUDIO_RATE}:channel_layouts=stereo"
)


def _even(n: int) -> int:
    """libx264 + yuv420p refuse odd dimensions."""
    return n - (n % 2)


def concat_videos(ffmpeg: str, parts: list[Path], out_path: Path) -> Path:
    """Append clips back-to-back, normalizing every input to the first clip's
    frame size / fps / SAR / pixel format so mixed sources can join.

    A clip whose aspect differs is fitted inside the first clip's frame and
    padded with black rather than stretched. Audio is resampled to one common
    format, and a part with no track gets matching silence so a silent clip
    can't strip the sound off the whole stitch."""
    n = len(parts)
    if n == 0:
        raise ValueError("nothing to concatenate")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    props = [probe(ffmpeg, p) for p in parts]
    first = props[0]
    inputs: list[str] = []
    for p in parts:
        inputs += ["-i", str(p)]

    # --- video: every part fitted into the first clip's frame -------------
    chains: list[str] = []
    w, h = _even(first.width), _even(first.height)
    fps = first.fps or 24.0
    if w > 0 and h > 0:
        norm = (
            f"scale={w}:{h}:force_original_aspect_ratio=decrease:flags=lanczos,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"setsar=1,fps={fps:g},format=yuv420p"
        )
        chains += [f"[{i}:v]{norm}[v{i}];" for i in range(n)]
        v_pads = [f"[v{i}]" for i in range(n)]
    else:
        v_pads = [f"[{i}:v]" for i in range(n)]

    # --- audio: one common format, silence where a track is missing -------
    a_pads: list[str] = []
    if any(pr.has_audio for pr in props) and all(pr.has_audio or pr.duration > 0 for pr in props):
        for i, pr in enumerate(props):
            if pr.has_audio:
                chains.append(f"[{i}:a]{AUDIO_NORM}[a{i}];")
            else:
                chains.append(
                    f"anullsrc=channel_layout=stereo:sample_rate={AUDIO_RATE}:d={pr.duration:g}[a{i}];"
                )
            a_pads.append(f"[a{i}]")

    # concat wants each segment's streams together: v0 a0 v1 a1 ...
    if a_pads:
        pads = "".join(v_pads[i] + a_pads[i] for i in range(n))
        filter_complex = f"{''.join(chains)}{pads}concat=n={n}:v=1:a=1[out][outa]"
        map_args = ["-map", "[out]", "-map", "[outa]"]
        audio_args = ["-c:a", "aac", "-b:a", "192k", "-ar", str(AUDIO_RATE)]
    else:
        filter_complex = f"{''.join(chains)}{''.join(v_pads)}concat=n={n}:v=1[out]"
        map_args = ["-map", "[out]"]
        audio_args = ["-an"]

    # Keep the first clip's codec family so extending an h265 source doesn't
    # silently produce a much larger h264 file.
    if first.vcodec == "hevc":
        video_args = ["-c:v", "libx265", "-preset", "fast", "-crf", "20", "-tag:v", "hvc1"]
    else:
        video_args = ["-c:v", "libx264", "-preset", "fast", "-crf", "18"]

    r = _run(
        [ffmpeg, "-y"] + inputs + ["-filter_complex", filter_complex] + map_args
        + video_args + ["-movflags", "+faststart"]
        + audio_args + [str(out_path)]
    )
    if r.returncode != 0:
        detail = "\n".join(
            f"  {p.name}: {pr.width}x{pr.height} {pr.fps:g}fps {pr.duration:.2f}s "
            f"{'audio' if pr.has_audio else 'no audio'}"
            for p, pr in zip(parts, props)
        )
        raise RuntimeError(
            f"ffmpeg concat failed:\n{r.stderr[-2500:]}\n\nParts:\n{detail}\n\nFilter:\n{filter_complex}"
        )
    return out_path
