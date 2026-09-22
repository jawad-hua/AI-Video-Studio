"""Har scene ka media (video/image) -> ek normalize kiya hua 9:16 clip (bina audio)."""
import logging
import os
import re
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Callable

from app.utils.errors import AppError

log = logging.getLogger(__name__)

FPS = 30
THREADS = max(2, min(4, os.cpu_count() or 2))  # kam RAM ke liye max 4
TRANSITION = 0.4  # xfade ki length (sec)


class FFmpegError(Exception):
    """Internal: ffmpeg fail hua (detail log mein hai, user ko generic message jata hai)."""


def ffmpeg_bin() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise AppError("FFmpeg not found. Install FFmpeg and restart the terminal.", 503)
    return path


_PROGRESS_KEYS = re.compile(r"^(frame|fps|stream_\d+_\d+_q|bitrate|total_size|out_time(_ms|_us)?|dup_frames|drop_frames|speed|progress)=")


def _run_with_progress(cmd: list[str], cwd: Path | None, timeout: int,
                       on_progress: Callable[[float], None], total_seconds: float) -> None:
    """ffmpeg ko '-progress pipe:1' ke saath chalao aur out_time se 0..1 progress report karo."""
    proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    timed_out = threading.Event()

    def _kill() -> None:
        timed_out.set()
        proc.kill()

    timer = threading.Timer(timeout, _kill)
    timer.start()
    tail: list[str] = []
    try:
        for line in proc.stdout or []:
            line = line.strip()
            if line.startswith(("out_time_us=", "out_time_ms=")):
                try:
                    secs = int(line.split("=", 1)[1]) / 1_000_000  # dono keys microseconds hain
                except ValueError:
                    continue  # shuru mein "N/A" aata hai
                on_progress(min(1.0, max(0.0, secs / total_seconds)))
            elif line and not _PROGRESS_KEYS.match(line):
                tail = (tail + [line])[-25:]  # asli error lines
        proc.wait()
    finally:
        timer.cancel()
    if timed_out.is_set():
        log.error("ffmpeg timeout after %ss", timeout)
        raise FFmpegError("timeout")
    if proc.returncode != 0:
        log.error("ffmpeg failed (code %s): %s", proc.returncode, "\n".join(tail)[-1500:])
        raise FFmpegError(f"exit {proc.returncode}")


def run_ffmpeg(args: list[str], cwd: Path | None = None, timeout: int = 300,
               on_progress: Callable[[float], None] | None = None, total_seconds: float | None = None) -> None:
    base = [ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error", "-nostdin"]
    if on_progress and total_seconds:
        _run_with_progress([*base, "-progress", "pipe:1", "-nostats", *args], cwd, timeout, on_progress, total_seconds)
        return
    cmd = [*base, *args]
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        log.error("ffmpeg timeout after %ss", timeout)
        raise FFmpegError("timeout")
    if r.returncode != 0:
        log.error("ffmpeg failed (code %s): %s", r.returncode, r.stderr[-1500:])
        raise FFmpegError(f"exit {r.returncode}")


def _video_filter(w: int, h: int, length: float, index: int) -> str:
    """9:16 bharo + halka slow pan (10% bada karke crop window sarkate hain): clip 'zinda' lagti hai, kharcha kam."""
    sw, sh = int(w * 1.10) // 2 * 2, int(h * 1.10) // 2 * 2
    u = f"min(1,t/{max(length, 0.1):.2f})"
    xs = [f"(iw-ow)*{u}", f"(iw-ow)*(1-{u})", "(iw-ow)/2", "(iw-ow)/2"]
    ys = ["(ih-oh)/2", "(ih-oh)/2", f"(ih-oh)*{u}", f"(ih-oh)*(1-{u})"]
    k = index % 4  # left->right, right->left, up->down, down->up
    return (
        f"scale={sw}:{sh}:force_original_aspect_ratio=increase,"
        f"crop={w}:{h}:x='{xs[k]}':y='{ys[k]}',setsar=1,fps={FPS},format=yuv420p"
    )


def _image_filter(w: int, h: int, frames: int, zoom_in: bool, factor: float = 2.0) -> str:
    # Ken Burns: 2x bada karke halka zoom (smooth, jitter kam). Toggle: zoom in / zoom out
    z = f"1+0.12*on/{frames}" if zoom_in else f"1.12-0.12*on/{frames}"
    bw, bh = int(w * factor) // 2 * 2, int(h * factor) // 2 * 2  # bada canvas (factor kam = tez)
    return (
        f"scale={bw}:{bh}:force_original_aspect_ratio=increase,crop={bw}:{bh},"
        f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={w}x{h}:fps={FPS},"
        f"setsar=1,format=yuv420p"
    )


def build_segment(src: Path, kind: str, length: float, size: tuple[int, int], index: int, out: Path,
                  preset: str = "ultrafast", crf: int = 23, kb_factor: float = 1.5) -> None:
    """kind: 'video' ya 'image'. length seconds mein. Output: H.264, bina audio."""
    w, h = size
    frames = max(1, round(length * FPS))
    common = ["-an", "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
              "-pix_fmt", "yuv420p", "-r", str(FPS), "-threads", str(THREADS)]
    if kind == "video":
        # Clip chhoti ho to loop hoti hai, lambi ho to shuru ka hissa
        args = ["-stream_loop", "-1", "-i", str(src), "-t", f"{length:.3f}",
                "-vf", _video_filter(w, h, length, index), *common, str(out)]
    else:
        args = ["-i", str(src), "-vf", _image_filter(w, h, frames, zoom_in=index % 2 == 1, factor=kb_factor),
                "-frames:v", str(frames), *common, str(out)]
    run_ffmpeg(args, timeout=240)
