"""Offline check: subtitle logic test (voice.json ka fake data use hota hai, internet nahi chahiye).

Run (backend folder se):  python -m tests.check_subtitle_logic
"""
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.models.voice import VoiceItem, VoiceResult, WordTiming
from app.services import subtitle_service as ss
from app.utils.errors import AppError

# 1) Chunking
chunks = ss.split_chunks("Software development is changing faster than ever, and generative AI is at the center of it.")
assert all(len(c.split()) <= ss.MAX_WORDS + 2 for c in chunks), chunks
assert " ".join(chunks) == "Software development is changing faster than ever, and generative AI is at the center of it."
assert chunks[-1] != "it."  # akela lafz pichhle chunk se juda
assert ss.split_chunks("Start today.") == ["Start today."]
assert ss.split_chunks("") == []
# Urdu: '۔' par sentence khatam
ur = ss.split_chunks("یہ پہلا جملہ ہے۔ یہ دوسرا جملہ ہے۔")
assert len(ur) >= 2 and ur[0].endswith("۔"), ur

# 2) Line wrap: chhota = 1 line, lamba = 2 balanced lines, akela lafz neeche nahi
assert ss.wrap_lines("faster than ever,") == "faster than ever,"
w = ss.wrap_lines("write boilerplate code in seconds.")
assert w.count("\\N") == 1
a, b = w.split("\\N")
assert abs(len(a) - len(b)) <= 6, w
assert "{" not in ss.wrap_lines("bad {override} text")

# 3) Timestamp format
assert ss._ts(0) == "0:00:00.00" and ss._ts(65.5) == "0:01:05.50" and ss._ts(3600.01) == "1:00:00.01"

# 4) Cues: scene ke andar rehte hain, overlap nahi
items = [
    VoiceItem(scene_number=1, file="x", text="Software development is changing faster than ever, and generative AI is at the center of it.",
              audio_duration=5.6, duration=6.0, start=0.0),
    VoiceItem(scene_number=2, file="x", text="AI assistants can now write boilerplate code in seconds.",
              audio_duration=3.9, duration=4.3, start=6.0),
]
voice = VoiceResult(job_id="j", voice="v", speed=1.0, total_duration=10.3, items=items)
cues = ss.build_cues(voice)
assert len(cues) >= 4
for c in cues:
    it = items[c.scene_number - 1]
    assert it.start - 0.001 <= c.start < c.end <= it.start + it.duration + 0.001, c
for prev, cur in zip(cues, cues[1:]):
    assert prev.end <= cur.start + 0.001, (prev, cur)  # overlap nahi
assert cues[-1].end <= voice.total_duration + 0.001

# 5) ASS structure + 4 styles
for st_name in ss.STYLES:
    st = st_name
    ass = ss.build_ass(cues, st)
    assert "[Script Info]" in ass and "[V4+ Styles]" in ass and "[Events]" in ass
    assert "PlayResX: 1080" in ass and "PlayResY: 1920" in ass
    n_ev = ass.count("Dialogue: 0,")  # highlight wale styles mein har lafz ka event, minimal mein har cue ka ek
    assert (n_ev == len(cues)) if ss.HIGHLIGHT[st_name] is None else (len(cues) <= n_ev <= sum(len(c.words) for c in cues)), (st_name, n_ev)
    assert f"Style: Main,Poppins," in ass
assert r"\fscx88" in ss.build_ass(cues, "modern-tech") and r"\fscx88" not in ss.build_ass(cues, "minimal")
# Urdu text -> Urdu font
ur_cues = [ss.Cue(scene_number=1, start=0, end=2, text="یہ ایک جملہ ہے")]
assert "Style: Main,Noto Naskh Arabic," in ss.build_ass(ur_cues, "modern-tech")

# 5a) Karaoke highlight: har lafz ka apna event (poori line), sirf usi lafz ka rang badalta hai (overlay layer nahi)
hl = ss.build_ass(cues, "modern-tech")
n_words = sum(len(c.words) for c in cues)
assert n_words == sum(len(c.text.split()) for c in cues)
assert hl.count("Dialogue: 0,") == n_words and hl.count("{\\1c&H00D4FF&}") == n_words and "Dialogue: 1," not in hl
assert "Dialogue: 0," in ss.build_ass(cues, "minimal") and "\\1c&H" not in ss.build_ass(cues, "minimal")  # minimal: highlight nahi
for c in cues:                                                          # lafz ke timings cue ke andar aur tarteeb mein
    assert all(c.start - 0.001 <= w.start < w.end <= c.end + 0.001 for w in c.words), c
    assert [w.start for w in c.words] == sorted(w.start for w in c.words)

# 5a2) TTS ke asli word timings use hon, ginti na mile to andaza
real = VoiceItem(scene_number=1, file="x", text="Hello brave new world", audio_duration=2.0, duration=2.4, start=10.0,
                 words=[WordTiming(text=t, start=s, end=s + 0.4) for t, s in zip("Hello brave new world".split(), (0.1, 0.6, 1.1, 1.5))])
rc = ss.build_cues(VoiceResult(job_id="j", voice="v", speed=1.0, total_duration=12.4, items=[real]))
assert len(rc) == 1 and rc[0].start == 10.1 and [w.start for w in rc[0].words] == [10.1, 10.6, 11.1, 11.5], rc
bad = real.model_copy(update={"words": real.words[:2]})                 # ginti alag -> andaza
bc = ss.build_cues(VoiceResult(job_id="j", voice="v", speed=1.0, total_duration=12.4, items=[bad]))
assert bc[0].start == 10.0 and len(bc[0].words) == 4

# 5b) Watermark (brand handle)
wm = ss.build_ass(cues, "modern-tech", "@brand {x}")
assert "Style: Brand," in wm and "Dialogue: 2," in wm and "@brand (x)" in wm
assert "Style: Brand," not in ss.build_ass(cues, "modern-tech")

# 5c) Urdu: sahi font + lafz screen par sahi tarteeb mein (asli libass render se pixel check)
assert ss.FONT_URDU == "Noto Naskh Arabic"
ur_item = VoiceItem(scene_number=1, file="x", text="\u0622\u062c \u06c1\u0631 \u0634\u0639\u0628\u06d2 \u06a9\u0648", audio_duration=4.0, duration=4.4, start=0.0)
ur_cues = ss.build_cues(VoiceResult(job_id="j", voice="v", speed=1.0, total_duration=4.4, items=[ur_item]))
assert len(ur_cues) == 1 and len(ur_cues[0].words) == 4
ur_ass = ss.build_ass(ur_cues, "modern-tech")
assert "Style: Main,Noto Naskh Arabic," in ur_ass
mixed = VoiceItem(scene_number=1, file="x", text="\u0627\u0648\u0631 AI \u0633\u06cc\u06a9\u06be\u0646\u0627 \u0627\u0628", audio_duration=3.0, duration=3.4, start=0.0)
mx_ass = ss.build_ass(ss.build_cues(VoiceResult(job_id="j", voice="v", speed=1.0, total_duration=3.4, items=[mixed])), "modern-tech")
mx_events = [l for l in mx_ass.split("\n") if l.startswith("Dialogue: 0,")]
assert mx_events and all("\\1c&H" not in l for l in mx_events), mx_events   # Urdu+English chunk: highlight nahi (galat tarteeb se bachao)
assert all("\u202b" in l and "\u202c" in l for l in mx_events)              # lekin RTL direction pakki hai
assert "\u202b" in ur_ass and "\\1c&H00D4FF&" in ur_ass                     # pure Urdu: RTL + highlight dono
order = ss._runs_are_ltr()
assert order in (True, False), "direction check natija nahi de saka"
rev = ss._colored_text(["a", "b", "c", "d"], [[0, 1, 2, 3]], 1, "00D4FF", reverse=True)
assert rev == "c d {\\1c&H00D4FF&}b{\\1c} a", rev                      # [baad wale] [current] [pehle wale]
assert ss._colored_text(["a", "b"], [[0], [1]], 1, "00D4FF", reverse=True) == "a\\N{\\1c&H00D4FF&}b{\\1c}"

import shutil as _sh, subprocess as _sp
if _sh.which("ffmpeg") and (Path(__file__).resolve().parent.parent / "assets" / "fonts" / "NotoNaskhArabic-Bold.ttf").exists():
    fonts_dir = Path(__file__).resolve().parent.parent / "assets" / "fonts"

    def gold_vs_white_x(cue_time):
        w = Path(tempfile.mkdtemp())
        _sh.copytree(fonts_dir, w / "fonts")
        (w / "u.ass").write_text(ur_ass.replace("PlayResX: 1080", "PlayResX: 1080"), encoding="utf-8")
        _sp.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=black:s=540x960:d=5",
                 "-vf", "subtitles=u.ass:fontsdir=fonts,format=rgb24", "-ss", str(cue_time), "-frames:v", "1",
                 "-f", "rawvideo", "u.rgb"], cwd=w, check=True)
        raw = (w / "u.rgb").read_bytes()
        gx = gn = wx = wn = 0
        for i in range(0, len(raw), 3):
            r_, g_, b_, x_ = raw[i], raw[i + 1], raw[i + 2], (i // 3) % 540
            if r_ > 200 and 150 < g_ < 240 and b_ < 90:
                gx, gn = gx + x_, gn + 1
            elif r_ > 200 and g_ > 200 and b_ > 200:
                wx, wn = wx + x_, wn + 1
        assert gn > 30 and wn > 30, (gn, wn)
        return gx / gn, wx / wn

    w0 = ur_cues[0].words
    g, wh = gold_vs_white_x(w0[0].start + 0.2)   # pehla lafz (آج) highlight: dayen taraf hona chahiye
    assert g > wh, ("pehla lafz dayen taraf nahi", g, wh)
    g, wh = gold_vs_white_x(w0[3].start + 0.05)   # aakhri lafz (کو): bayen taraf
    assert g < wh, ("aakhri lafz bayen taraf nahi", g, wh)
    print("Urdu order check: OK")

# 6) End-to-end (temp folders) + error cases
tmp = Path(tempfile.mkdtemp())
ss.AUDIO_DIR = tmp / "generated" / "audio"
ss.SUBTITLES_DIR = tmp / "generated" / "subtitles"
(ss.AUDIO_DIR / "job1").mkdir(parents=True)
(ss.AUDIO_DIR / "job1" / "voice.json").write_text(voice.model_dump_json(), encoding="utf-8")

res = ss.generate_subtitles("job1", "documentary")
assert res.cue_count == len(res.cues) >= 4 and res.style == "documentary"
ass_path = tmp / res.file
assert ass_path.exists() and "Dialogue:" in ass_path.read_text(encoding="utf-8")

for bad, code in (("nojob", 404), ("../evil", 400)):
    try:
        ss.generate_subtitles(bad)
        raise SystemExit(f"FAIL: {bad} accepted")
    except AppError as e:
        assert e.status_code == code, (bad, e.status_code)

# 7) Optional: FFmpeg (libass) se ek frame render karke dekho (font + ASS sahi load hota hai?)
# Windows note: filter mein "C:/..." ka colon toot jata hai, isliye cwd + relative paths use karte hain.
font_src = Path(__file__).resolve().parent.parent / "assets" / "fonts"
if shutil.which("ffmpeg") and (font_src / "Poppins-Bold.ttf").exists():
    work = ass_path.parent
    shutil.copytree(font_src, work / "fonts", dirs_exist_ok=True)
    r = subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=0x1e1b4b:s=720x1280:d=8",
         "-vf", "subtitles=subtitles.ass:fontsdir=fonts", "-ss", "1", "-frames:v", "1", "frame.png"],
        cwd=work, capture_output=True, text=True,
    )
    assert r.returncode == 0 and (work / "frame.png").exists(), r.stderr[:300]
    (work / "wm.ass").write_text(ss.build_ass(res.cues, "modern-tech", "@brand"), encoding="utf-8")  # watermark wali file bhi render
    r2 = subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=0x1e1b4b:s=720x1280:d=8",
         "-vf", "subtitles=wm.ass:fontsdir=fonts", "-ss", "1", "-frames:v", "1", "frame2.png"],
        cwd=work, capture_output=True, text=True,
    )
    assert r2.returncode == 0, r2.stderr[:300]
    print("FFmpeg render check: OK")
else:
    print("FFmpeg render check: skipped")

print("OK: saare checks pass")
