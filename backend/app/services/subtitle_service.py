import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.config import AUDIO_DIR, BASE_DIR, SUBTITLES_DIR
from app.models.schemas import VideoStyle
from app.models.subtitles import Cue, CueWord, SubtitleResult
from app.models.voice import VoiceResult
from app.utils.errors import AppError

log = logging.getLogger(__name__)

# ASS ka apna coordinate system: hamesha 1080x1920. FFmpeg render size (720p/1080p) par khud scale karta hai.
PLAY_W, PLAY_H = 1080, 1920

MAX_WORDS = 4      # ek subtitle mein max lafz (short-form style)
MAX_CHARS = 28
ONE_LINE_MAX = 20  # is se chhota chunk ek hi line mein
END_LINGER = 0.15  # aakhri subtitle awaaz ke baad thodi der rukta hai

# TikTok/Reels ka UI neeche (~25%) aur right side par hota hai: subtitle wahan se door rakha hai
MARGIN_V = 500     # neeche se (1920 mein) -> subtitle ~ 74-80% height par
MARGIN_LR = 120

# BorderStyle 1 = outline, 3 = box. Colours ASS format mein: &HAABBGGRR
STYLES: dict[str, dict] = {
    "modern-tech": dict(size=108, primary="&H00FFFFFF", outline="&H00000000", back="&H80000000",
                        border_style=1, outline_w=9, shadow=2, spacing=0, pop=True),
    "cinematic":   dict(size=100, primary="&H00F2F2F2", outline="&H00000000", back="&H80000000",
                        border_style=1, outline_w=6, shadow=4, spacing=2, pop=False),
    "documentary": dict(size=92, primary="&H00FFFFFF", outline="&HB0000000", back="&HB0000000",
                        border_style=3, outline_w=18, shadow=0, spacing=0, pop=False),
    "minimal":     dict(size=88, primary="&H00FFFFFF", outline="&H00000000", back="&H00000000",
                        border_style=1, outline_w=5, shadow=0, spacing=0, pop=False),
}

FONT_LATIN = "Poppins"      # backend/assets/fonts/Poppins-Bold.ttf
FONT_URDU = "Noto Naskh Arabic"  # backend/assets/fonts/NotoNaskhArabic-Bold.ttf (saath bundled: system font par bharosa nahi)
URDU_SIZE_SCALE = 1.2        # Urdu fonts ki line-height chhoti hoti hai, isliye thoda bada
URDU_BOLD = -1
_ARABIC = re.compile("[\u0600-\u06FF\u0750-\u077F]")
_SENTENCE_END = (".", "!", "?", "\u06d4", "\u061f")  # ... ۔ ؟
_SOFT_END = (",", ";", ":", "\u060c")               # , ; : ،


# Abhi bola ja raha lafz is rang mein (ASS override format BBGGRR). minimal style mein highlight nahi
HIGHLIGHT: dict[str, str | None] = {"modern-tech": "00D4FF", "cinematic": "47B3FF", "documentary": "FCD37D", "minimal": None}


# ------------------------------------------------------------------ chunking
def _chunk_tokens(tokens: list[str]) -> list[list[str]]:
    """Lafzon ko chhote subtitle chunks mein todo (punctuation par prefer karke)."""
    chunks: list[list[str]] = []
    cur: list[str] = []
    for w in tokens:
        cur.append(w)
        joined = " ".join(cur)
        if (
            len(cur) >= MAX_WORDS
            or len(joined) >= MAX_CHARS
            or w.endswith(_SENTENCE_END)
            or (w.endswith(_SOFT_END) and len(cur) >= 2)
        ):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)

    # Akela ek lafz ("it.", "seconds.") pichhle chunk ke saath jod do (agar wo sentence khatam nahi kar raha)
    merged: list[list[str]] = []
    for c in chunks:
        if (
            len(c) == 1 and merged
            and len(merged[-1]) < MAX_WORDS + 2
            and not merged[-1][-1].endswith(_SENTENCE_END)
        ):
            merged[-1].extend(c)
        else:
            merged.append(c)
    return merged


def split_chunks(text: str) -> list[str]:
    return [" ".join(c) for c in _chunk_tokens(text.split())]


def _escape(s: str) -> str:
    return s.replace("\\", "").replace("{", "(").replace("}", ")")


def _line_groups(tokens: list[str]) -> list[list[int]]:
    """Chhota chunk = 1 line. Lamba = 2 balanced lines (akela lafz neeche nahi girta)."""
    if len(" ".join(tokens)) <= ONE_LINE_MAX or len(tokens) == 1:
        return [list(range(len(tokens)))]
    cut = min(range(1, len(tokens)), key=lambda k: abs(len(" ".join(tokens[:k])) - len(" ".join(tokens[k:]))))
    return [list(range(cut)), list(range(cut, len(tokens)))]


def wrap_lines(chunk: str) -> str:
    tokens = chunk.split()
    return "\\N".join(" ".join(_escape(tokens[i]) for i in g) for g in _line_groups(tokens))


# ------------------------------------------------------------------- timing
def _word_times(item) -> list[tuple[str, float, float]]:
    """(lafz, start, end) video timeline par. TTS ke asli timings mile to wahi, warna characters ke hisaab se andaza."""
    tokens = item.text.split()
    if not tokens:
        return []
    if item.words and len(item.words) == len(tokens):
        return [(t, item.start + w.start, item.start + w.end) for t, w in zip(tokens, item.words)]
    # Andaza: lambe lafz ko zyada waqt, punctuation ke baad thodi pause
    weights = [
        max(1, len(re.sub(r"\W", "", t))) + (3 if t.endswith(_SENTENCE_END) else 2 if t.endswith(_SOFT_END) else 0)
        for t in tokens
    ]
    total, t0, out = sum(weights), item.start, []
    for tok, w in zip(tokens, weights):
        d = item.audio_duration * w / total
        out.append((tok, t0, t0 + d))
        t0 += d
    return out


def build_cues(voice: VoiceResult) -> list[Cue]:
    cues: list[Cue] = []
    for item in voice.items:
        times = _word_times(item)
        if not times:
            continue
        groups, pos = [], 0
        for chunk in _chunk_tokens([t for t, _, _ in times]):
            groups.append(times[pos : pos + len(chunk)])
            pos += len(chunk)
        scene_end = item.start + item.duration

        for k, cw in enumerate(groups):
            start = max(item.start, cw[0][1])
            if k + 1 < len(groups):
                nxt = groups[k + 1][0][1]
                end = nxt if nxt - cw[-1][2] < 0.45 else cw[-1][2] + 0.12  # chhoti pause mein subtitle bandhe rahe
            else:
                end = cw[-1][2] + END_LINGER  # aakhri chunk thoda ruke, lekin scene se bahar nahi
            end = min(max(end, start + 0.12), scene_end)

            words = []
            for j, (tok, ws, _) in enumerate(cw):
                ws = max(start, ws)
                we = cw[j + 1][1] if j + 1 < len(cw) else end  # highlight agle lafz tak chalta rahe
                words.append(CueWord(text=tok, start=round(ws, 2), end=round(max(we, ws + 0.05), 2)))
            cues.append(Cue(scene_number=item.scene_number, start=round(start, 2), end=round(end, 2),
                            text=" ".join(t for t, _, _ in cw), words=words))
    return cues


# ---------------------------------------------------------------- ASS output
def _ts(seconds: float) -> str:
    cs = int(round(max(0.0, seconds) * 100))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, cs = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


_RLE, _PDF = "\u202b", "\u202c"  # Unicode "right-to-left embedding": libass ko line ki direction RTL batata hai


def _is_rtl(text: str) -> bool:
    """Chunk mein koi bhi Urdu/Arabic harf ho to poori line RTL (Latin lafz Urdu ke beech mein bhi sahi jagah aayenge)."""
    return bool(_ARABIC.search(text))


def _pure_rtl(tokens: list[str]) -> bool:
    """Sirf Urdu/Arabic-script (koi ASCII harf, number ya nishan nahi). Mixed line mein rang-highlight libass mein
    lafz ulte-seedhe kar deta hai, isliye wahan highlight nahi lagate."""
    return all(not ch.isascii() for t in tokens for ch in t)


_CAL: dict[str, bool | None] = {}


def _runs_are_ltr() -> bool | None:
    """Asli libass par ek chhota test: Urdu line mein rang badalne wale lafz ki jagah kahan aati hai?

    Kuch libass builds mein alag rang wale hisse (runs) galat tarteeb (left-to-right) mein lagte hain, isliye
    rang wala lafz ulti jagah nazar aata hai. True = ulti tarteeb (hum khud theek karte hain), False = sahi,
    None = test na ho saka (tab Urdu mein highlight band, taake text kabhi ulta na dikhe).
    """
    if "v" in _CAL:
        return _CAL["v"]
    result: bool | None = None
    try:
        with tempfile.TemporaryDirectory() as d:
            work = Path(d)
            fonts_src = BASE_DIR / "assets" / "fonts"
            if fonts_src.exists():
                shutil.copytree(fonts_src, work / "fonts")
            else:
                (work / "fonts").mkdir()
            (work / "cal.ass").write_text(
                "[Script Info]\nScriptType: v4.00+\nPlayResX: 480\nPlayResY: 240\nWrapStyle: 0\n\n[V4+ Styles]\n"
                "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
                "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
                f"MarginR, MarginV, Encoding\nStyle: Main,{FONT_URDU},110,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,"
                "100,100,0,0,1,0,0,5,10,10,10,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, "
                "MarginV, Effect, Text\nDialogue: 0,0:00:00.00,0:00:02.00,Main,,0,0,0,,"
                "\u202b\u0622\u062c {\\1c&H00FF00&}\u06a9\u0648{\\1c}\u202c\n",
                encoding="utf-8",
            )
            r = subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=black:s=480x240:d=2",
                 "-vf", "subtitles=cal.ass:fontsdir=fonts,format=rgb24", "-frames:v", "1", "-f", "rawvideo", "cal.rgb"],
                cwd=work, capture_output=True, timeout=30,
            )
            raw = (work / "cal.rgb").read_bytes() if r.returncode == 0 else b""
            if len(raw) == 480 * 240 * 3:
                gx = gn = wx = wn = 0
                for i in range(0, len(raw), 3):
                    R_, G_, B_ = raw[i], raw[i + 1], raw[i + 2]
                    x = (i // 3) % 480
                    if G_ > 180 and R_ < 90 and B_ < 90:
                        gx, gn = gx + x, gn + 1
                    elif R_ > 200 and G_ > 200 and B_ > 200:
                        wx, wn = wx + x, wn + 1
                if gn > 30 and wn > 30:
                    result = (gx / gn) > (wx / wn)  # hara (aakhri lafz) safed se dayen: ulti tarteeb
    except (OSError, subprocess.SubprocessError):
        log.warning("Subtitle direction check failed")
    if result is None:
        log.warning("Could not verify RTL subtitle order; Urdu word highlight disabled")
    _CAL["v"] = result
    return result


def _colored_text(tokens: list[str], groups: list[list[int]], current: int, color: str, reverse: bool = False) -> str:
    """Poori line ka text, jis mein sirf `current` lafz rang badalta hai. `{\1c}` (bina value) = style ka rang wapas.
    reverse=True (sirf Urdu, jab libass runs ulte lagaye): line ke hisse [baad wale, current, pehle wale] ki tarteeb mein
    likhte hain, taake screen par lafz sahi tarteeb mein aayein."""
    lines = []
    for g in groups:
        if current not in g:
            lines.append(" ".join(_escape(tokens[i]) for i in g))
            continue
        before = [_escape(tokens[i]) for i in g if i < current]
        after = [_escape(tokens[i]) for i in g if i > current]
        now = "{\\1c&H" + color + "&}" + _escape(tokens[current]) + "{\\1c}"
        runs = [" ".join(after), now, " ".join(before)] if reverse else [" ".join(before), now, " ".join(after)]
        lines.append(" ".join(r for r in runs if r))
    return "\\N".join(lines)


def build_ass(cues: list[Cue], style: VideoStyle, watermark: str | None = None) -> str:
    st = STYLES[style]
    is_urdu = any(_ARABIC.search(c.text) for c in cues)
    font = FONT_URDU if is_urdu else FONT_LATIN
    size = int(st["size"] * URDU_SIZE_SCALE) if is_urdu else st["size"]

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {PLAY_W}
PlayResY: {PLAY_H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,{font},{size},{st['primary']},&H000000FF,{st['outline']},{st['back']},{-1 if not is_urdu else URDU_BOLD},0,0,0,100,100,{st['spacing'] if not is_urdu else 0},0,{st['border_style']},{st['outline_w']},{st['shadow']},2,{MARGIN_LR},{MARGIN_LR},{MARGIN_V},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    pop = r"\fscx88\fscy88\t(0,120,\fscx100\fscy100)" if st["pop"] else ""  # sirf chunk ke pehle event par
    color = HIGHLIGHT.get(style)
    runs_ltr: bool | None = False
    if is_urdu and color:
        runs_ltr = _runs_are_ltr()
        if runs_ltr is None:
            color = None  # tarteeb verify nahi hui: Urdu mein highlight ke bajaye saaf sada text

    lines: list[str] = []
    for c in cues:
        tokens = c.text.split()
        groups = _line_groups(tokens)
        rtl = _is_rtl(c.text)
        w_open, w_close = (_RLE, _PDF) if rtl else ("", "")  # RTL line ki direction pakki karo
        if color and len(c.words) == len(tokens) and (not rtl or _pure_rtl(tokens)):
            # Karaoke: har lafz ka apna event (poori line), sirf bola ja raha lafz rang badalta hai. Events aapas mein judte hain.
            n, prev_end = len(tokens), c.start
            for j, w in enumerate(c.words):
                first, last = j == 0, j == n - 1
                start = max(w.start, prev_end)
                end = c.end if last else w.end
                if end - start < 0.02:
                    continue
                prev_end = end
                fx = "{" + rf"\fad({70 if first else 0},{50 if last else 0})" + (pop if first else "") + "}"
                lines.append(f"Dialogue: 0,{_ts(start)},{_ts(end)},Main,,0,0,0,,{fx}{w_open}{_colored_text(tokens, groups, j, color, bool(runs_ltr) and rtl)}{w_close}")
        else:
            base = "\\N".join(" ".join(_escape(tokens[i]) for i in g) for g in groups)
            fx = "{" + r"\fad(70,50)" + pop + "}"
            lines.append(f"Dialogue: 0,{_ts(c.start)},{_ts(c.end)},Main,,0,0,0,,{fx}{w_open}{base}{w_close}")

    if watermark:  # brand handle: upar-left, halka, poori video mein (TikTok ke top bar ke neeche)
        brand = f"Style: Brand,{font},44,&H99FFFFFF,&H000000FF,&H66000000,&H00000000,-1,0,0,0,100,100,1,0,1,3,0,7,60,60,230,1"
        header = header.replace("\n\n[Events]", f"\n{brand}\n\n[Events]", 1)
        lines.append(f"Dialogue: 2,{_ts(0)},{_ts(cues[-1].end)},Brand,,0,0,0,,{{\\fad(500,500)}}{_escape(watermark)}")
    return header + "\n".join(lines) + "\n"


# ---------------------------------------------------------------------- main
def _load_voice(job_id: str) -> VoiceResult:
    path = AUDIO_DIR / job_id / "voice.json"
    if not path.exists():
        raise AppError("No voice-over found for this job. Run POST /api/voice/generate first.", 404)
    try:
        return VoiceResult.model_validate_json(path.read_text(encoding="utf-8"))
    except ValueError:
        log.exception("voice.json invalid for %s", job_id)
        raise AppError("Saved voice data is invalid. Generate the voice-over again.", 422)


def generate_subtitles(job_id: str, style: VideoStyle = "modern-tech", watermark: str | None = None) -> SubtitleResult:
    out_dir = (SUBTITLES_DIR / job_id).resolve()
    if not out_dir.is_relative_to(SUBTITLES_DIR.resolve()):
        raise AppError("Invalid job id.", 400)

    voice = _load_voice(job_id)
    cues = build_cues(voice)
    if not cues:
        raise AppError("No narration text found to make subtitles.", 422)

    out_dir.mkdir(parents=True, exist_ok=True)
    path: Path = out_dir / "subtitles.ass"
    path.write_text(build_ass(cues, style, watermark), encoding="utf-8")  # UTF-8 (Urdu ke liye zaroori)

    return SubtitleResult(
        job_id=job_id,
        style=style,
        file=path.relative_to(SUBTITLES_DIR.parent.parent).as_posix(),
        cue_count=len(cues),
        cues=cues,
    )
