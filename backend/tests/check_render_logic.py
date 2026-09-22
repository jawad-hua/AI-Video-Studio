"""Offline check: FFmpeg render pipeline (fake media/voice se). Internet nahi chahiye, FFmpeg chahiye.

Run (backend folder se):  python -m tests.check_render_logic
"""
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.models.media import MediaItem, MediaResult
from app.models.voice import VoiceItem, VoiceResult
from app.services import render_service as rs
from app.services import subtitle_service as ss
from app.utils.errors import AppError

if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
    raise SystemExit("FFmpeg/ffprobe not found: is test ke liye chahiye")


def ff(*args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


def info(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height:format=duration",
         "-of", "json", str(path)], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


# ---- Fake project folder (temp)
base = Path(tempfile.mkdtemp())
for name in ("media", "audio", "subtitles", "videos", "jobs"):
    (base / "generated" / name).mkdir(parents=True)
(base / "assets" / "music").mkdir(parents=True)
real_fonts = Path(__file__).resolve().parent.parent / "assets" / "fonts"
if real_fonts.exists():
    shutil.copytree(real_fonts, base / "assets" / "fonts")

rs.BASE_DIR = base
rs.MEDIA_DIR, rs.AUDIO_DIR = base / "generated" / "media", base / "generated" / "audio"
rs.SUBTITLES_DIR, rs.VIDEOS_DIR, rs.JOBS_DIR = base / "generated" / "subtitles", base / "generated" / "videos", base / "generated" / "jobs"

ff("-f", "lavfi", "-i", "sine=frequency=220:duration=10", "-c:a", "libmp3lame", str(base / "assets" / "music" / "track.mp3"))

job = "j1"
mdir, adir, sdir = rs.MEDIA_DIR / job, rs.AUDIO_DIR / job, rs.SUBTITLES_DIR / job
for d in (mdir, adir, sdir):
    d.mkdir(parents=True)

ff("-f", "lavfi", "-i", "testsrc=s=540x960:d=4", "-pix_fmt", "yuv420p", str(mdir / "scene_01.mp4"))    # vertical
ff("-f", "lavfi", "-i", "testsrc2=s=1280x720:d=1", "-pix_fmt", "yuv420p", str(mdir / "scene_02.mp4"))   # landscape + chhoti (loop)
ff("-f", "lavfi", "-i", "testsrc2=s=800x1200", "-frames:v", "1", str(mdir / "scene_03.jpg"))            # image (Ken Burns)
ff("-f", "lavfi", "-i", "color=c=0x312e81:s=720x1280", "-frames:v", "1", str(mdir / "scene_04.png"))    # placeholder
ff("-f", "lavfi", "-i", "testsrc=s=720x1280:d=4", "-pix_fmt", "yuv420p", str(mdir / "scene_05.mp4"))

types = ["video", "video", "image", "image", "video"]
exts = ["mp4", "mp4", "jpg", "png", "mp4"]
media_items, voice_items, start = [], [], 0.0
for i in range(5):
    n = i + 1
    ff("-f", "lavfi", "-i", "sine=frequency=440:duration=2.6", "-c:a", "libmp3lame", str(adir / f"scene_{n:02d}.mp3"))
    media_items.append(MediaItem(scene_number=n, type=types[i], source="pexels",
                                 file=f"generated/media/{job}/scene_{n:02d}.{exts[i]}"))
    voice_items.append(VoiceItem(scene_number=n, file=f"generated/audio/{job}/scene_{n:02d}.mp3",
                                 text=f"This is the narration text of scene {n}.", audio_duration=2.6, duration=3.0, start=start))
    start += 3.0
(mdir / "media.json").write_text(MediaResult(job_id=job, videos=3, images=2, fallbacks=0, items=media_items).model_dump_json())
voice = VoiceResult(job_id=job, voice="v", speed=1.0, total_duration=15.0, items=voice_items)
(adir / "voice.json").write_text(voice.model_dump_json())
(sdir / "subtitles.ass").write_text(ss.build_ass(ss.build_cues(voice), "modern-tech"), encoding="utf-8")

# 1) Normal render: transitions + music, 720p
res = rs.render_video(job, quality="720p")
out = base / res.file
i = info(out)
kinds = {s["codec_type"]: s for s in i["streams"]}
assert kinds["video"]["codec_name"] == "h264" and kinds["audio"]["codec_name"] == "aac", kinds
assert (kinds["video"]["width"], kinds["video"]["height"]) == (720, 1280)
assert abs(float(i["format"]["duration"]) - 15.0) < 0.4, i["format"]
assert res.transitions is True and res.music == "track.mp3" and res.duration <= 60
assert res.sound_effects is True and len(res.transition_names) == 4, res
assert all(a != b for a, b in zip(res.transition_names, res.transition_names[1:])), res.transition_names  # lagatar repeat nahi
assert set(res.transition_names) <= set(rs.pick_transitions.__globals__["POOLS"]["modern-tech"]), res.transition_names
assert not (rs.VIDEOS_DIR / f"{job}_work").exists()  # temp folder saaf

# 2) Pro transitions fail -> simple fade + music wapas (video phir bhi ban jati hai)
real_pick = rs.pick_transitions
rs.pick_transitions = lambda style, n, seed: ["bogus_transition"] * n
res = rs.render_video(job, quality="720p")
assert res.transitions is True and res.transition_names == ["fade"] * 4 and res.music == "track.mp3" and res.sound_effects is False
assert abs(float(info(base / res.file)["format"]["duration"]) - 15.0) < 0.4

# 2b) Fade bhi fail -> seedhe cuts, bina music
rs.SIMPLE = "bogus_transition"
res = rs.render_video(job, quality="720p")
rs.SIMPLE, rs.pick_transitions = "fade", real_pick
assert res.transitions is False and res.music is None and res.transition_names == []
assert abs(float(info(base / res.file)["format"]["duration"]) - 15.0) < 0.4

# 2c) Alag styles: cinematic pool se transitions
res = rs.render_video(job, quality="720p", style="cinematic")
assert set(res.transition_names) <= set(rs.pick_transitions.__globals__["POOLS"]["cinematic"]), res.transition_names

# 3) transitions=False, music=False (tez mode)
res = rs.render_video(job, transitions=False, music=False)
assert res.transitions is False and res.music is None

# 4) 60 sec cap: limit ko 10 sec kar ke dekho, video usse lambi nahi honi chahiye
rs.MAX_TOTAL = 10.0
res = rs.render_video(job, quality="720p")
assert float(info(base / res.file)["format"]["duration"]) <= 10.1
rs.MAX_TOTAL = 60.0

# 5) Errors
for bad_job, code in (("nojob", 404), ("../evil", 400)):
    try:
        rs.render_video(bad_job)
        raise SystemExit(f"FAIL: {bad_job} accepted")
    except AppError as e:
        assert e.status_code == code, (bad_job, e.status_code)

(sdir / "subtitles.ass").unlink()
try:
    rs.render_video(job)
    raise SystemExit("FAIL: missing subtitles accepted")
except AppError as e:
    assert e.status_code == 404

print("OK: saare checks pass")
