"""check_jobs_logic.py isko temp folder mein chalata hai. Seedha mat chalao."""
import subprocess
import threading
import time

from fastapi.testclient import TestClient

from app.config import AUDIO_DIR, MEDIA_DIR, SUBTITLES_DIR, settings
from app.main import app
from app.models.media import MediaItem, MediaResult
from app.models.schemas import Scene, VideoPlan
from app.services import job_service, pipeline_service as ps, voice_service as vs
from app.utils.errors import AppError


def ff(*args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


# ---------------------------------------------------------------- fakes
def fake_plan(req):
    scenes = [Scene(scene_number=i + 1, duration=5, narration=f"dur:2.5 hello from scene {i + 1}",
                    subtitle=f"Scene {i + 1}", search_keywords=["x"], transition=["fade", "slide", "zoom"][i % 3])
              for i in range(5)]
    return VideoPlan(title="Fake Video: Test!", caption="Great caption. Follow!", hashtags=["ai", "#Tech", "ai"], scenes=scenes)


stamps: dict = {}


def fake_media(plan, job_id, on_progress=None):
    stamps["media"] = [time.time(), None]
    time.sleep(0.8)  # voice ke saath overlap dekhne ke liye
    d = MEDIA_DIR / job_id
    d.mkdir(parents=True, exist_ok=True)
    items = []
    for i in range(5):
        n = i + 1
        if i % 2 == 0:
            ff("-f", "lavfi", "-i", "testsrc=s=540x960:d=3", "-pix_fmt", "yuv420p", str(d / f"scene_{n:02d}.mp4"))
            items.append(MediaItem(scene_number=n, type="video", source="pexels", file=f"generated/media/{job_id}/scene_{n:02d}.mp4"))
        else:
            ff("-f", "lavfi", "-i", "testsrc2=s=800x1200", "-frames:v", "1", str(d / f"scene_{n:02d}.jpg"))
            items.append(MediaItem(scene_number=n, type="image", source="fallback" if n == 4 else "pexels",
                                   file=f"generated/media/{job_id}/scene_{n:02d}.jpg"))
    res = MediaResult(job_id=job_id, videos=3, images=2, fallbacks=1, items=items)
    (d / "media.json").write_text(res.model_dump_json())
    stamps["media"][1] = time.time()
    return res


class FakeTTS:
    lock = threading.Lock()

    def synthesize(self, text, voice, out_path):
        with FakeTTS.lock:
            stamps.setdefault("voice_start", time.time())
        secs = float(text.split("dur:")[1].split()[0])
        ff("-f", "lavfi", "-i", f"sine=frequency=440:duration={secs}", "-c:a", "libmp3lame", str(out_path))
        with FakeTTS.lock:
            stamps["voice_end"] = time.time()


ps.create_script = fake_plan
ps.fetch_media_for_plan = fake_media
vs.get_provider = lambda: FakeTTS()
settings.groq_api_key = "test-key"      # preflight ke liye
settings.pexels_api_key = "test-key"


def wait_done(c, job_id, timeout=240):
    seen, last, t0 = [], -1, time.time()
    while time.time() - t0 < timeout:
        s = c.get(f"/api/video/status/{job_id}").json()
        assert s["progress"] >= last, s  # progress kabhi peechhe nahi jata
        last = s["progress"]
        if not seen or seen[-1] != s["status"]:
            seen.append(s["status"])
        if s["status"] in ("completed", "failed"):
            return s, seen
        time.sleep(0.5)
    raise SystemExit("FAIL: job timeout")


body = {"topic": "How generative AI works", "duration": 30, "style": "modern-tech", "voice": "en-US-AndrewNeural",
        "resolution": "720p", "background_music": True, "aspect_ratio": "9:16", "speed": "fast", "watermark": "@mychannel", "sound_effects": True}

with TestClient(app) as c:
    # 1) Happy path
    r = c.post("/api/video/generate", json=body)
    assert r.status_code == 200, r.text
    job_id = r.json()["job_id"]
    s, seen = wait_done(c, job_id)
    assert s["status"] == "completed" and s["progress"] == 100 and s["current_step"] == "Video ready", s
    order = ["queued", "analyzing", "scripting", "fetching_media", "generating_voice",
             "creating_subtitles", "rendering", "completed"]
    idx = [order.index(x) for x in seen]
    assert idx == sorted(idx) and seen[-1] == "completed", seen  # status hamesha aage badhta hai
    print("statuses seen:", " > ".join(seen))

    # Media aur voice ek saath chale (overlap), aur timings/ETA/caption sab bane
    m0, m1 = stamps["media"]
    assert m0 < stamps["voice_end"] and stamps["voice_start"] < m1, stamps
    saved = job_service.load_job(job_id)
    assert {"script", "media_voice", "subtitles", "render", "total"} <= set(saved.timings), saved.timings
    assert saved.elapsed_seconds and saved.elapsed_seconds > 0
    st = c.get(f"/api/video/status/{job_id}").json()
    assert st["elapsed_seconds"] > 0 and st["typical_seconds"] is not None, st
    ass = (SUBTITLES_DIR / job_id / "subtitles.ass").read_text(encoding="utf-8")
    assert "@mychannel" in ass and "Style: Brand" in ass  # brand watermark

    info = c.get(f"/api/video/{job_id}").json()
    assert info["caption"] == "Great caption. Follow!" and info["hashtags"] == ["#ai", "#Tech"], info
    assert info["elapsed_seconds"] > 0
    assert info["title"] == "Fake Video: Test!" and len(info["scenes"]) == 5 and info["duration"] <= 30, info
    assert info["scenes"][0]["start"] == 0 and info["scenes"][3]["media_source"] == "fallback"
    assert info["width"] == 720 and info["height"] == 1280

    for sc in info["scenes"]:
        t = c.get(sc["thumbnail_url"])
        assert t.status_code == 200 and t.headers["content-type"] == "image/jpeg" and len(t.content) > 500, sc

    # Raw clips/audio saaf, thumbnails aur JSON bache
    assert not list((MEDIA_DIR / job_id).glob("scene_*")) and not list((AUDIO_DIR / job_id).glob("scene_*"))
    assert (MEDIA_DIR / job_id / "thumb_01.jpg").exists() and (MEDIA_DIR / job_id / "media.json").exists()

    v = c.get(info["video_url"])
    assert v.status_code == 200 and v.headers["content-type"] == "video/mp4" and v.content[4:8] == b"ftyp"
    rg = c.get(info["video_url"], headers={"Range": "bytes=0-99"})
    assert rg.status_code == 206 and len(rg.content) == 100, rg.status_code  # seek/streaming
    d = c.get(info["download_url"])
    assert "attachment" in d.headers["content-disposition"] and "Fake-Video-Test.mp4" in d.headers["content-disposition"]

    # 2) Unknown / unsafe ids
    assert c.get("/api/video/status/aaaaaaaaaaaa").status_code == 404
    assert c.get("/api/video/status/not-valid").status_code == 404
    assert c.get("/api/video/..%2Fetc").status_code == 404

    # 3) Video ready nahi hai
    j = job_service.create_job(job_service.GenerateVideoRequest(topic="Not started topic"))
    assert c.get(f"/api/video/{j.job_id}").status_code == 409
    assert c.get(f"/api/video/{j.job_id}/file").status_code == 409

    # 4) Request validation
    assert c.post("/api/video/generate", json={**body, "topic": "hi"}).status_code == 422
    assert c.post("/api/video/generate", json={**body, "duration": 50}).status_code == 422

    # 5) Failure: AppError ka message user ko jata hai
    def boom(req):
        raise AppError("Groq is temporarily unavailable. Please try again shortly.", 503)
    ps.create_script = boom
    jid = c.post("/api/video/generate", json=body).json()["job_id"]
    s, _ = wait_done(c, jid)
    assert s["status"] == "failed" and "Groq is temporarily unavailable" in s["error"], s

    # 6) Failure: ajeeb crash -> generic message (technical detail nahi)
    def crash(req):
        raise RuntimeError("secret internal detail /home/x")
    ps.create_script = crash
    jid = c.post("/api/video/generate", json=body).json()["job_id"]
    s, _ = wait_done(c, jid)
    assert s["status"] == "failed" and "secret" not in s["error"] and "Something went wrong" in s["error"], s
    ps.create_script = fake_plan

    # 5b) Media fail ho (voice saath chal rahi ho) to bhi job saaf message ke saath fail, atakti nahi
    def media_boom(plan, job_id, on_progress=None):
        raise AppError("Pexels is temporarily unavailable. Please try again shortly.", 503)
    ps.fetch_media_for_plan = media_boom
    jid = c.post("/api/video/generate", json=body).json()["job_id"]
    s, _ = wait_done(c, jid)
    assert s["status"] == "failed" and "Pexels is temporarily unavailable" in s["error"], s
    ps.fetch_media_for_plan = fake_media

    # 6b) Preflight: key missing to job banne se pehle hi friendly error
    before = len(list(job_service.JOBS_DIR.glob("*.json")))
    settings.groq_api_key = ""
    r = c.post("/api/video/generate", json=body)
    assert r.status_code == 503 and "GROQ_API_KEY" in r.json()["detail"], r.text
    settings.groq_api_key = "test-key"
    assert len(list(job_service.JOBS_DIR.glob("*.json"))) == before  # koi bekaar job file nahi bani

    # 7) Queue limit
    ps.MAX_PENDING = -1
    r = c.post("/api/video/generate", json=body)
    assert r.status_code == 429, r.status_code
    ps.MAX_PENDING = 3

    # 8) Stale job (server restart)
    stale = job_service.create_job(job_service.GenerateVideoRequest(topic="Stale job topic"))
    job_service.update_job(stale.job_id, status="rendering", progress=75)
    job_service.mark_stale_jobs_failed()
    st = c.get(f"/api/video/status/{stale.job_id}").json()
    assert st["status"] == "failed" and "restarted" in st["error"], st

print("OK: saare checks pass")
