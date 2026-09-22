"""Offline check: internet/edge-tts ke bina voice logic test karta hai.

Fake voice provider FFmpeg se beep-mp3 banata hai (narration text mein "dur:5" = 5 sec).
Run (backend folder se):  python -m tests.check_voice_logic
"""
import json
import shutil
import time
import subprocess
import tempfile
from pathlib import Path

from app.models.schemas import Scene, VideoPlan
from app.services import voice_service as vs
from app.utils.errors import AppError

if not shutil.which("ffmpeg"):
    raise SystemExit("FFmpeg not found: is test ke liye FFmpeg chahiye")


class FakeProvider:
    def synthesize(self, text, voice, out_path):
        secs = float(text.split("dur:")[1].split()[0])
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"sine=frequency=440:duration={secs}",
             "-c:a", "libmp3lame", "-b:a", "48k", str(out_path)],
            check=True,
        )


class FailingProvider:
    def synthesize(self, text, voice, out_path):
        raise AppError("Voice generation failed.", 503)


def make_plan(seconds, n=8):
    scenes = [
        Scene(scene_number=i + 1, duration=5, narration=f"dur:{seconds} **hello** 🚀", search_keywords=["a"])
        for i in range(n)
    ]
    return VideoPlan(title="Test", scenes=scenes)


tmp = Path(tempfile.mkdtemp())
vs.AUDIO_DIR = tmp / "generated" / "audio"
vs.AUDIO_DIR.mkdir(parents=True)

# 1) compute_timing
assert vs.compute_timing([5] * 8, 60) == (1.0, vs.PAD)              # aaram se fit
speed, pad = vs.compute_timing([7.5] * 8, 60)                       # thoda tez karna padega
assert 1.0 < speed < 1.1 and pad == vs.PAD, (speed, pad)
speed, pad = vs.compute_timing([9] * 8, 60)                         # pad kam + speed
assert speed <= vs.MAX_SPEEDUP and pad == vs.MIN_PAD, (speed, pad)
try:
    vs.compute_timing([12] * 8, 60)
    raise SystemExit("FAIL: too-long narration accepted")
except AppError as e:
    assert e.status_code == 422

# 2) clean_text
assert vs.clean_text("**Hi**  there 🚀 #tag") == "Hi there tag"

# 3) Normal: 8 x 5s -> speed 1.0, total = 8*(5+0.4) = 43.2
res = vs.generate_voice(make_plan(5), "job1", voice="en-US-AndrewNeural", max_total=60, provider=FakeProvider())
assert res.speed == 1.0 and len(res.items) == 8
assert abs(res.total_duration - 43.2) < 0.5, res.total_duration
assert res.items[0].start == 0 and abs(res.items[1].start - res.items[0].duration) < 0.02
assert all(abs(i.audio_duration - 5) < 0.3 for i in res.items)
assert all((tmp / i.file).exists() for i in res.items)
assert (vs.AUDIO_DIR / "job1" / "voice.json").exists()
assert res.items[0].text == "dur:5 hello"  # markdown/emoji saaf

# 4) 8 x 7.5s = 60s audio -> speed-up, total <= 60
res = vs.generate_voice(make_plan(7.5), "job2", max_total=60, provider=FakeProvider())
assert res.speed > 1.0 and res.total_duration <= 60.0, (res.speed, res.total_duration)
assert all(i.audio_duration < 7.5 for i in res.items)  # audio sach mein chhota hua

# 5) 30 sec cap: 8 x 3.5s = 28s audio
res = vs.generate_voice(make_plan(3.5), "job3", max_total=30, provider=FakeProvider())
assert res.total_duration <= 30.0, res.total_duration

# 6) Bahut lambi narration -> friendly error
try:
    vs.generate_voice(make_plan(12), "job4", max_total=60, provider=FakeProvider())
    raise SystemExit("FAIL: too-long accepted")
except AppError as e:
    assert e.status_code == 422

# 7) Provider fail -> AppError (crash nahi)
try:
    vs.generate_voice(make_plan(5), "job5", provider=FailingProvider())
    raise SystemExit("FAIL: provider error ignored")
except AppError as e:
    assert e.status_code == 503

# 8) Unsafe job id
try:
    vs.generate_voice(make_plan(5), "../evil", provider=FakeProvider())
    raise SystemExit("FAIL: unsafe job id allowed")
except AppError as e:
    assert e.status_code == 400

# 9) Parallel TTS: 6 scenes x 0.5s = 3s sequential, 3 workers mein ~1s. Order/durations sahi rehne chahiye
sound = {}
for secs in (2, 3):
    p = tmp / f"s{secs}.mp3"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"sine=frequency=440:duration={secs}",
                    "-c:a", "libmp3lame", str(p)], check=True)
    sound[secs] = p


class SlowProvider:
    def synthesize(self, text, voice, out_path):
        time.sleep(0.5)
        secs = int(float(text.split("dur:")[1].split()[0]))
        shutil.copy(sound[secs], out_path)


scenes = [Scene(scene_number=i + 1, duration=5, narration=f"dur:{2 + i % 2} scene {i}", search_keywords=["a"]) for i in range(6)]
t0 = time.time()
res = vs.generate_voice(VideoPlan(title="Slow", scenes=scenes), "job6", max_total=60, provider=SlowProvider())
took = time.time() - t0
assert took < 2.4, f"parallel nahi chala: {took:.1f}s"
assert [round(i.audio_duration) for i in res.items] == [2, 3, 2, 3, 2, 3], [i.audio_duration for i in res.items]

# 10) Word timings: sahi ho to use hon (speed-up par scale), galat ho to khali (subtitles fallback lengi)
class WordProvider(FakeProvider):
    mode = "good"

    def synthesize(self, text, voice, out_path):
        super().synthesize(text, voice, out_path)
        secs = float(text.split("dur:")[1].split()[0])
        toks = text.split()
        if self.mode == "good":
            step = secs / len(toks)
            return [(t, i * step, (i + 1) * step - 0.05) for i, t in enumerate(toks)]
        if self.mode == "count":
            return [("x", 0.0, 1.0)]                       # lafz ginti alag
        return [(t, 0.0, secs * 5) for t in toks]          # unit galat (bahut lamba)


wp = WordProvider()
res = vs.generate_voice(make_plan(5), "job7", max_total=60, provider=wp)
w = res.items[0].words
assert [x.text for x in w] == ["dur:5", "hello"] and w[0].start == 0 and 5.0 > w[-1].end > 4.0, w
res = vs.generate_voice(make_plan(7.5), "job8", max_total=60, provider=wp)      # speed-up: timings chhoti honi chahiye
assert res.speed > 1.0 and res.items[0].words[-1].end <= res.items[0].audio_duration + 0.01
assert res.items[0].words[-1].end < 7.5 * 0.96, res.items[0].words
for bad in ("count", "unit"):
    wp.mode = bad
    assert vs.generate_voice(make_plan(5), "job9", max_total=60, provider=wp).items[0].words == [], bad

print("OK: saare checks pass")
