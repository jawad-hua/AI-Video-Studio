"""Final render: scene clips + narration + subtitles (+ music) -> ek MP4 (H.264 + AAC, <= 60 sec)."""
import hashlib
import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Callable

from app.config import AUDIO_DIR, BASE_DIR, JOBS_DIR, MEDIA_DIR, SUBTITLES_DIR, VIDEOS_DIR, settings
from app.models.media import MediaResult
from app.models.render import RenderResult
from app.models.schemas import VideoPlan
from app.models.voice import VoiceResult
from app.services.effects import SIMPLE, grade_filter, pick_transitions
from app.services.video_service import FFmpegError, FPS, THREADS, TRANSITION, build_segment, run_ffmpeg
from app.utils.errors import AppError

log = logging.getLogger(__name__)

MAX_TOTAL = 60.0
MUSIC_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}
MUSIC_VOLUME = 0.10
QUALITY = {"720p": (720, 1280, 21), "1080p": (1080, 1920, 20)}  # width, height, crf
SFX_VOLUME = 0.30
WHOOSH_SECONDS = 0.7
# Speed presets: fast = tez (draft jaisa, social media ke liye kaafi), balanced = thodi behtar quality
SPEED = {
    "fast": dict(preset="ultrafast", crf_add=2, seg_crf=23, kb=1.5),
    "balanced": dict(preset="veryfast", crf_add=0, seg_crf=20, kb=2.0),
}


# ------------------------------------------------------------------ helpers
def _safe_dir(base: Path, job_id: str) -> Path:
    d = (base / job_id).resolve()
    if not d.is_relative_to(base.resolve()):
        raise AppError("Invalid job id.", 400)
    return d


def _load(path: Path, model, hint: str):
    if not path.exists():
        raise AppError(hint, 404)
    try:
        return model.model_validate_json(path.read_text(encoding="utf-8"))
    except ValueError:
        log.exception("Invalid file %s", path)
        raise AppError(f"{path.name} is invalid. Please generate it again.", 422)


def _resolve_file(rel: str) -> Path:
    base = MEDIA_DIR.parent.parent.resolve()  # backend/
    p = (base / rel).resolve()
    if not p.is_relative_to(base) or not p.exists():
        raise AppError("A media or audio file is missing. Please generate the previous steps again.", 422)
    return p


def _pick_music(job_id: str) -> Path | None:
    folder = BASE_DIR / "assets" / "music"
    tracks = sorted(p for p in folder.glob("*") if p.suffix.lower() in MUSIC_EXTS) if folder.exists() else []
    if not tracks:
        return None
    return tracks[int(hashlib.md5(job_id.encode()).hexdigest(), 16) % len(tracks)]


def probe(path: Path) -> dict | None:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    try:
        r = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height:format=duration",
             "-of", "json", str(path)],
            capture_output=True, text=True, timeout=20,
        )
        return json.loads(r.stdout)
    except (subprocess.SubprocessError, ValueError, OSError):
        return None


# ---------------------------------------------------------------- assemble
def _make_whoosh(work: Path) -> Path | None:
    """Transition ki 'whoosh' awaaz: FFmpeg se pink noise banakar (koi download nahi)."""
    out = work / "whoosh.wav"
    try:
        run_ffmpeg(["-f", "lavfi", "-i", f"anoisesrc=d={WHOOSH_SECONDS}:c=pink:r=44100:a=0.7",
                    "-af", "highpass=f=300,lowpass=f=7000,afade=t=in:st=0:d=0.3,afade=t=out:st=0.3:d=0.4",
                    str(out)], cwd=work, timeout=30)
        return out
    except FFmpegError:
        log.warning("Could not create whoosh sound, continuing without sound effects")
        return None


def _build_filter(n: int, durs: list[float], starts: list[float], total: float,
                  transitions: list[str] | None, has_music: bool,
                  grade: str | None = None, has_sfx: bool = False) -> str:
    parts: list[str] = []

    # ---- Video: xfade chain ya seedhe cuts
    if transitions:
        prev = "0:v"
        for i in range(1, n):
            parts.append(f"[{prev}][{i}:v]xfade=transition={transitions[i]}:duration={TRANSITION}:offset={starts[i]:.3f}[x{i}]")
            prev = f"x{i}"
        vlabel = prev
    else:
        for i in range(n):
            parts.append(f"[{i}:v]trim=duration={durs[i]:.3f},setpts=PTS-STARTPTS[t{i}]")
        parts.append("".join(f"[t{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[cat]")
        vlabel = "cat"
    # Colour grade + fades, phir subtitles (relative paths: Windows "C:" colon filter mein toot jata hai)
    parts.append(f"[{vlabel}]" + (f"{grade}," if grade else "") + "subtitles=subs.ass:fontsdir=fonts,format=yuv420p[v]")

    # ---- Audio: har scene ki narration ko scene ki length tak pad karke jodo
    for i in range(n):
        parts.append(
            f"[{n + i}:a]aresample=44100,aformat=channel_layouts=stereo,"
            f"apad=whole_dur={durs[i]:.3f},atrim=0:{durs[i]:.3f},asetpts=PTS-STARTPTS[a{i}]"
        )
    parts.append("".join(f"[a{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1[narr]")
    mix = ["[narr]"]
    idx = 2 * n
    if has_music:
        fade_start = max(0.0, total - 1.5)
        parts.append(
            f"[{idx}:a]aresample=44100,aformat=channel_layouts=stereo,volume={MUSIC_VOLUME},"
            f"atrim=0:{total:.3f},afade=t=out:st={fade_start:.3f}:d=1.5[mus]"
        )
        mix.append("[mus]")
        idx += 1
    if has_sfx and transitions and n > 1:
        m = n - 1  # har transition par ek whoosh (scene boundary se thoda pehle)
        base = f"[{idx}:a]aresample=44100,aformat=channel_layouts=stereo,volume={SFX_VOLUME}"
        if m == 1:
            parts.append(f"{base}[w0]")
        else:
            parts.append(base + f",asplit={m}" + "".join(f"[w{k}]" for k in range(m)))
        for k in range(m):
            ms = int(max(0.0, starts[k + 1] - 0.05) * 1000)
            parts.append(f"[w{k}]adelay={ms}|{ms}[d{k}]")
        parts.append("".join(f"[d{k}]" for k in range(m)) + f"amix=inputs={m}:duration=longest:dropout_transition=0:normalize=0[sfx]")
        mix.append("[sfx]")
    if len(mix) > 1:
        parts.append("".join(mix) + f"amix=inputs={len(mix)}:duration=first:dropout_transition=0:normalize=0[aout]")
    else:
        parts.append("[narr]anull[aout]")
    return ";".join(parts)


def _assemble(work: Path, segs: list[Path], audios: list[Path], durs: list[float], starts: list[float],
              total: float, crf: int, transitions: list[str] | None, music: Path | None,
              on_progress: Callable[[float], None] | None = None, preset: str = "veryfast",
              grade: str | None = None, sfx: Path | None = None) -> Path:
    n = len(segs)
    inputs: list[str] = []
    for s in segs:
        inputs += ["-i", str(s)]
    for a in audios:
        inputs += ["-i", str(a)]
    if music:
        inputs += ["-stream_loop", "-1", "-i", str(music)]
    if sfx and transitions:
        inputs += ["-i", str(sfx)]

    out = work / "out.mp4"
    out.unlink(missing_ok=True)
    run_ffmpeg(
        [*inputs, "-filter_complex",
         _build_filter(n, durs, starts, total, transitions, music is not None, grade, bool(sfx and transitions)),
         "-map", "[v]", "-map", "[aout]", "-t", f"{total:.3f}",
         "-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-pix_fmt", "yuv420p",
         "-profile:v", "high", "-r", str(FPS), "-c:a", "aac", "-b:a", "128k",
         "-movflags", "+faststart", "-threads", str(THREADS), "-filter_complex_threads", "1", str(out)],
        cwd=work, timeout=900, on_progress=on_progress, total_seconds=total,
    )
    return out


# --------------------------------------------------------------------- main
def render_video(job_id: str, quality: str | None = None, music: bool = True, transitions: bool = True,
                 on_progress: Callable[[float], None] | None = None, speed: str = "fast",
                 style: str = "modern-tech", sfx: bool = True) -> RenderResult:
    sp = SPEED.get(speed, SPEED["fast"])
    report = on_progress or (lambda f: None)  # 0..1: pehle 15% scene clips, baaki final render
    media = _load(_safe_dir(MEDIA_DIR, job_id) / "media.json", MediaResult,
                  "No media found for this job. Run POST /api/media/fetch first.")
    voice = _load(_safe_dir(AUDIO_DIR, job_id) / "voice.json", VoiceResult,
                  "No voice-over found for this job. Run POST /api/voice/generate first.")
    ass = _safe_dir(SUBTITLES_DIR, job_id) / "subtitles.ass"
    if not ass.exists():
        raise AppError("No subtitles found for this job. Run POST /api/subtitles/generate first.", 404)

    by_scene = {m.scene_number: m for m in media.items}
    if any(v.scene_number not in by_scene for v in voice.items):
        raise AppError("Media and voice-over do not match. Generate media and voice again for this job.", 422)

    n = len(voice.items)
    durs = [v.duration for v in voice.items]
    starts, acc = [], 0.0
    for d in durs:
        starts.append(round(acc, 3))
        acc += d
    total = min(round(acc, 3), MAX_TOTAL)  # hard limit: 60 sec

    if quality:
        w, h, crf = QUALITY[quality]
    else:
        w, h = settings.render_width, settings.render_height
        crf = 20 if w >= 1080 else 21
    music_path = _pick_music(job_id) if music else None
    names = pick_transitions(style, n, job_id) if transitions else None  # style ke hisaab se alag alag transitions

    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    work = _safe_dir(VIDEOS_DIR, f"{job_id}_work")
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)

    try:
        # Subtitle file aur font work folder mein: FFmpeg filter mein sirf relative path jayega
        shutil.copy(ass, work / "subs.ass")
        fonts_src = BASE_DIR / "assets" / "fonts"
        if fonts_src.exists():
            shutil.copytree(fonts_src, work / "fonts", dirs_exist_ok=True)
        else:
            (work / "fonts").mkdir()

        # Stage 1: har scene ka clip (transition ke liye non-last clips ko TRANSITION extra lambai)
        segs: list[Path] = []
        for i, v in enumerate(voice.items):
            item = by_scene[v.scene_number]
            length = durs[i] + (TRANSITION if i < n - 1 else 0)
            seg = work / f"seg_{i:02d}.mp4"
            build_segment(_resolve_file(item.file), item.type, length, (w, h), i, seg,
                          preset="ultrafast", crf=sp["seg_crf"], kb_factor=sp["kb"])
            segs.append(seg)
            report(0.15 * (i + 1) / n)
        audios = [_resolve_file(v.file) for v in voice.items]

        # Stage 2: final render. 3 koshishen: (1) poore effects  (2) sirf simple fade  (3) seedhe cuts, bina music
        whoosh = _make_whoosh(work) if (names and sfx) else None
        grade = grade_filter(style, total, vignette=(speed == "balanced")) if names else None
        attempts = [(names, music_path, whoosh, grade)]
        if names or music_path:
            attempts.append(([SIMPLE] * n if names else None, music_path, None, None))
        attempts.append((None, None, None, None))
        out = None
        used = (None, None, None)
        tried = []
        for tr, mu, sf, gr in attempts:
            key = (tuple(tr) if tr else None, mu, sf, gr)
            if key in tried:
                continue
            tried.append(key)
            try:
                out = _assemble(work, segs, audios, durs, starts, total, crf + sp["crf_add"], tr, mu,
                                lambda f: report(0.15 + 0.85 * f), preset=sp["preset"], grade=gr, sfx=sf)
                used = (tr, mu, sf)
                break
            except FFmpegError:
                log.warning("Render attempt failed (transitions=%s, music=%s, sfx=%s)", bool(tr), bool(mu), bool(sf))
        if out is None:
            raise AppError("Video rendering failed. Details are in backend/generated/app.log.", 500)

        # Verify: video+audio stream aur duration <= 60
        info = probe(out)
        duration = total
        if info:
            kinds = {s.get("codec_type") for s in info.get("streams", [])}
            duration = float(info.get("format", {}).get("duration") or total)
            if kinds != {"video", "audio"} or duration > MAX_TOTAL + 0.1:
                log.error("Render verification failed: %s", info)
                raise AppError("Rendered video failed validation. Please try again.", 500)

        final = VIDEOS_DIR / f"{job_id}.mp4"
        shutil.move(str(out), final)
    except FFmpegError:
        raise AppError("Video rendering failed. Details are in backend/generated/app.log.", 500)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    return RenderResult(
        job_id=job_id,
        file=final.relative_to(VIDEOS_DIR.parent.parent).as_posix(),
        duration=round(duration, 2),
        width=w, height=h,
        size_mb=round(final.stat().st_size / 1_000_000, 2),
        transitions=used[0] is not None,
        transition_names=list(used[0][1:]) if used[0] else [],
        music=used[1].name if used[1] else None,
        sound_effects=used[2] is not None and used[0] is not None,
    )
