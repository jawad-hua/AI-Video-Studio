import asyncio
import logging
import math
import os
import re
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Protocol

from app.config import AUDIO_DIR, settings
from app.models.schemas import VideoPlan
from app.models.voice import VoiceItem, VoiceResult, WordTiming
from app.utils.errors import AppError

log = logging.getLogger(__name__)

PAD = 0.4
MIN_PAD = 0.15
MAX_SPEEDUP = 1.25
DEFAULT_RATE = "+5%"
MAX_TOTAL = 60
TTS_WORKERS = 3

Words = list[tuple[str, float, float]]


class TTSProvider(Protocol):
    def synthesize(self, text: str, voice: str, out_path: Path) -> Words | None: ...


def gtts_fallback(text: str, voice: str, out_path: Path) -> Words | None:
    """Fallback TTS when Microsoft Edge TTS is unavailable."""
    try:
        from gtts import gTTS

        language = "ur" if voice.lower().startswith("ur-") else "en"
        tts = gTTS(text=text, lang=language, slow=False)
        tts.save(str(out_path))

        if not out_path.exists() or out_path.stat().st_size < 1000:
            raise RuntimeError("gTTS returned empty audio")

        log.info("gTTS fallback generated voice successfully")
        return None

    except Exception as e:
        log.error("gTTS fallback failed: %s: %s", type(e).__name__, str(e)[:200])
        out_path.unlink(missing_ok=True)
        raise AppError(
            "Voice generation failed on both Edge TTS and fallback TTS. Please try again.",
            503,
        )


class EdgeTTSProvider:
    """Free Microsoft Edge voices with automatic gTTS fallback."""

    def synthesize(self, text: str, voice: str, out_path: Path) -> Words | None:
        try:
            import edge_tts
        except ImportError:
            log.warning("edge-tts is not installed; using gTTS fallback")
            return gtts_fallback(text, voice, out_path)

        async def run() -> Words:
            try:
                comm = edge_tts.Communicate(
                    text,
                    voice,
                    rate=DEFAULT_RATE,
                    boundary="WordBoundary",
                )
            except TypeError:
                comm = edge_tts.Communicate(text, voice, rate=DEFAULT_RATE)

            words: Words = []
            with open(out_path, "wb") as fh:
                async for chunk in comm.stream():
                    if chunk["type"] == "audio":
                        fh.write(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        start = chunk["offset"] / 1e7
                        words.append(
                            (
                                chunk["text"],
                                start,
                                start + chunk["duration"] / 1e7,
                            )
                        )
            return words

        last_error: Exception | None = None

        for attempt in range(3):
            try:
                return asyncio.run(run()) or None
            except Exception as e:
                last_error = e
                log.warning(
                    "edge-tts failed (attempt %s): %s: %s",
                    attempt + 1,
                    type(e).__name__,
                    str(e)[:200],
                )
                out_path.unlink(missing_ok=True)

                if attempt < 2:
                    time.sleep(1.5 * (attempt + 1))

        log.warning(
            "Edge TTS failed after 3 attempts (%s). Switching to gTTS fallback.",
            type(last_error).__name__ if last_error else "unknown error",
        )
        return gtts_fallback(text, voice, out_path)


def get_provider() -> TTSProvider:
    name = settings.tts_provider.strip().lower()
    if name == "edge":
        return EdgeTTSProvider()
    raise AppError(
        f"Unknown TTS_PROVIDER '{settings.tts_provider}'. Use 'edge' in backend/.env.",
        500,
    )


_EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F]")


def clean_text(text: str) -> str:
    t = _EMOJI.sub("", text)
    t = re.sub(r"[*_#`~<>|]", "", t)
    return re.sub(r"\s+", " ", t).strip()


def audio_duration(path: Path) -> float:
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        try:
            out = subprocess.run(
                [
                    ffprobe,
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    str(path),
                ],
                capture_output=True,
                text=True,
                timeout=15,
            ).stdout.strip()
            return float(out)
        except (ValueError, subprocess.SubprocessError, OSError):
            log.warning("ffprobe failed for %s, estimating duration", path.name)

    return path.stat().st_size / 6000


def _speed_up(path: Path, speed: float) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise AppError(
            "FFmpeg is required to fit the voice-over. Install FFmpeg and restart the terminal.",
            503,
        )

    tmp = path.with_name(path.stem + "_fast.mp3")
    r = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(path),
            "-filter:a",
            f"atempo={speed:.3f}",
            "-c:a",
            "libmp3lame",
            "-q:a",
            "4",
            str(tmp),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )

    if r.returncode != 0 or not tmp.exists():
        log.error("ffmpeg atempo failed: %s", r.stderr[:300])
        tmp.unlink(missing_ok=True)
        raise AppError(
            "Could not adjust voice speed. Check your FFmpeg installation.",
            500,
        )

    os.replace(tmp, path)


def _valid_words(words: Words | None, text: str, audio_dur: float) -> Words:
    if not words or len(words) != len(text.split()):
        return []

    last = 0.0
    for _, s, e in words:
        if s < last - 0.05 or e < s:
            return []
        last = e

    if last > audio_dur * 1.35 or last < audio_dur * 0.4:
        return []

    return words


def _too_long(cap: float) -> AppError:
    return AppError(
        f"The narration is too long to fit in {int(cap)} seconds. Generate a new script or choose a longer duration.",
        422,
    )


def compute_timing(audio_durs: list[float], cap: float) -> tuple[float, float]:
    n, total = len(audio_durs), sum(audio_durs)

    if total + n * PAD <= cap:
        return 1.0, PAD

    for pad in (PAD, MIN_PAD):
        room = cap - n * pad
        if room > 0:
            speed = total / room * 1.01
            if speed <= MAX_SPEEDUP:
                return math.ceil(speed * 100) / 100, pad

    raise _too_long(cap)


def final_durations(audio_durs: list[float], cap: float, pad: float) -> list[float]:
    n = len(audio_durs)
    pad = min(pad, (cap - sum(audio_durs)) / n)

    if pad < 0.05:
        raise _too_long(cap)

    return [math.floor((d + pad) * 100) / 100 for d in audio_durs]


def generate_voice(
    plan: VideoPlan,
    job_id: str,
    voice: str | None = None,
    max_total: int = MAX_TOTAL,
    provider: TTSProvider | None = None,
    on_progress: Callable[[float], None] | None = None,
) -> VoiceResult:
    cap = float(min(max_total, MAX_TOTAL))
    voice = voice or settings.tts_voice
    provider = provider or get_provider()

    job_dir = (AUDIO_DIR / job_id).resolve()
    if not job_dir.is_relative_to(AUDIO_DIR.resolve()):
        raise AppError("Invalid job id.", 400)
    job_dir.mkdir(parents=True, exist_ok=True)

    texts: list[str] = []
    paths: list[Path] = []

    for i, scene in enumerate(plan.scenes, start=1):
        text = clean_text(scene.narration)
        if not text:
            raise AppError(f"Scene {i} has no narration text.", 422)

        path = job_dir / f"scene_{i:02d}.mp3"
        path.unlink(missing_ok=True)
        texts.append(text)
        paths.append(path)

    pool = ThreadPoolExecutor(max_workers=TTS_WORKERS)

    try:
        futures = [
            pool.submit(provider.synthesize, t, voice, p)
            for t, p in zip(texts, paths)
        ]

        raw_words: list[Words | None] = []

        for k, f in enumerate(futures, start=1):
            raw_words.append(f.result())

            if on_progress:
                on_progress(k / len(futures))
    finally:
        pool.shutdown(wait=False, cancel_futures=True)

    durs: list[float] = []

    for i, path in enumerate(paths, start=1):
        if not path.exists() or path.stat().st_size < 1000:
            log.error("Scene %s: TTS produced no valid audio", i)
            path.unlink(missing_ok=True)
            raise AppError(
                "Voice generation returned empty audio. Please try again.",
                502,
            )

        durs.append(audio_duration(path))

    good_words = [
        _valid_words(w, t, d)
        for w, t, d in zip(raw_words, texts, durs)
    ]

    speed, pad = compute_timing(durs, cap)

    if speed > 1.0:
        log.info("Voice-over speed-up x%.2f to fit %ss", speed, cap)

        for p in paths:
            _speed_up(p, speed)

        durs = [audio_duration(p) for p in paths]

    scene_durs = final_durations(durs, cap, pad)

    items, start = [], 0.0

    for i, (text, p, a, d, gw) in enumerate(
        zip(texts, paths, durs, scene_durs, good_words),
        start=1,
    ):
        items.append(
            VoiceItem(
                scene_number=i,
                file=p.relative_to(AUDIO_DIR.parent.parent).as_posix(),
                text=text,
                audio_duration=round(a, 2),
                duration=d,
                start=round(start, 2),
                words=[
                    WordTiming(
                        text=wt,
                        start=round(min(ws / speed, a), 3),
                        end=round(min(we / speed, a), 3),
                    )
                    for wt, ws, we in gw
                ],
            )
        )
        start += d

    result = VoiceResult(
        job_id=job_id,
        voice=voice,
        speed=speed,
        total_duration=round(start, 2),
        items=items,
    )

    (job_dir / "voice.json").write_text(
        result.model_dump_json(indent=2),
        encoding="utf-8",
    )

    return result
