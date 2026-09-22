"""Offline check: Pexels/internet ke bina media logic test karta hai (fake server use hota hai).

Run (backend folder se):  python -m tests.check_pexels_logic
"""
import struct
import tempfile
import zlib
from pathlib import Path

import httpx

from app.config import settings
from app.models.schemas import Scene, VideoPlan
from app.services import pexels_service as ps
from app.utils.errors import AppError

MP4 = b"\x00\x00\x00\x18ftypmp42" + b"0" * 10_000
JPG = b"\xff\xd8\xff\xe0" + b"0" * 10_000
HTML = b"<html>" + b"x" * 10_000

seen_auth: dict[str, bool] = {}  # host -> Authorization header aaya ya nahi


def vfile(w, h, name):
    return {"file_type": "video/mp4", "width": w, "height": h, "link": f"https://videos.pexels.com/{name}.mp4"}


def video(vid, dur, files):
    return {"id": vid, "duration": dur, "url": f"https://pexels.com/video/{vid}", "user": {"name": "Tester"}, "video_files": files}


VIDEOS = {
    # landscape (id 1) pehle, vertical (id 2, 3) baad mein
    "city night skyline": [
        video(1, 20, [vfile(1920, 1080, "l1")]),
        video(2, 10, [vfile(540, 960, "p2_sd"), vfile(1080, 1920, "p2_hd"), vfile(2160, 3840, "p2_uhd")]),
        video(3, 12, [vfile(1080, 1920, "p3_hd")]),
    ],
    "html clip": [video(7, 10, [vfile(1080, 1920, "bad_html")])],
    "huge clip": [video(8, 10, [vfile(1080, 1920, "huge")])],
}
PHOTOS = {
    "only photo": [{"id": 50, "url": "https://pexels.com/photo/50", "photographer": "Pho", "width": 800, "height": 1200,
                    "src": {"portrait": "https://images.pexels.com/p50.jpg"}}],
}


def handler(request: httpx.Request) -> httpx.Response:
    url = request.url
    seen_auth[url.host] = "authorization" in request.headers or seen_auth.get(url.host, False)
    if url.host == "api.pexels.com":
        q = url.params.get("query", "")
        if url.path == "/videos/search":
            return httpx.Response(200, json={"videos": VIDEOS.get(q, [])})
        return httpx.Response(200, json={"photos": PHOTOS.get(q, [])})
    name = url.path.split("/")[-1]
    if name == "bad_html.mp4":
        return httpx.Response(200, content=HTML)
    if name == "huge.mp4":
        return httpx.Response(200, content=MP4, headers={"content-length": "50000000"})
    if name.endswith(".mp4"):
        return httpx.Response(200, content=MP4)
    return httpx.Response(200, content=JPG)


def sc(n, kws, dur=6):
    return Scene(scene_number=n, duration=dur, narration="Some narration.", visual_description="a b c d", search_keywords=kws)


plan = VideoPlan(title="Test", scenes=[
    sc(1, ["city night", "skyline"]),   # vertical video, id 2 (1080x1920 file)
    sc(2, ["city night", "skyline"]),   # id 2 use ho chuki -> id 3
    sc(3, ["only photo"]),              # video nahi, photo hai
    sc(4, ["nothing here"]),            # kuch nahi -> placeholder
    sc(5, ["html clip"]),               # invalid file -> placeholder
    sc(6, ["huge clip"]),               # bahut bari file -> placeholder
])

tmp = Path(tempfile.mkdtemp())
ps.MEDIA_DIR = tmp / "generated" / "media"
ps.MEDIA_DIR.mkdir(parents=True)
ps._make_client = lambda: httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)
ps.time.sleep = lambda s: None
settings.pexels_api_key = "SECRET-KEY"

res = ps.fetch_media_for_plan(plan, "job1")
it = {i.scene_number: i for i in res.items}

assert it[1].type == "video" and it[1].pexels_id == 2 and it[1].width == 1080, it[1]   # vertical + sahi size (4K nahi)
assert it[2].pexels_id == 3, it[2]                                                     # duplicate nahi
assert it[3].type == "image" and it[3].source == "pexels" and it[3].pexels_id == 50, it[3]
assert it[4].source == "fallback" and it[5].source == "fallback" and it[6].source == "fallback"
assert (res.videos, res.images, res.fallbacks) == (2, 1, 3), res

# Files sach mein bani hain aur valid hain
for i in res.items:
    f = tmp / i.file
    assert f.exists() and f.stat().st_size > 5000, i.file
assert not list((ps.MEDIA_DIR / "job1").glob("*.part"))  # temp files saaf
assert (ps.MEDIA_DIR / "job1" / "media.json").exists()

# Placeholder valid PNG (720x1280)
png = (tmp / it[4].file).read_bytes()
assert png[:8] == b"\x89PNG\r\n\x1a\n"
w, h = struct.unpack(">II", png[16:24])
assert (w, h) == (settings.render_width, settings.render_height)
assert zlib.decompress(png[png.index(b"IDAT") + 4 : png.index(b"IEND") - 8])  # data theek se decompress hota hai

# API key sirf api.pexels.com ko gayi, download hosts ko nahi
assert seen_auth["api.pexels.com"] is True
assert seen_auth.get("videos.pexels.com") is False and seen_auth.get("images.pexels.com") is False

# Dobara run: purani files replace hoti hain, error nahi
assert ps.fetch_media_for_plan(plan, "job1").videos == 2

# Unsafe job id
try:
    ps.fetch_media_for_plan(plan, "../evil")
    raise SystemExit("FAIL: unsafe job id allowed")
except AppError as e:
    assert e.status_code == 400

# Key missing
settings.pexels_api_key = ""
try:
    ps.fetch_media_for_plan(plan, "job2")
    raise SystemExit("FAIL: missing key allowed")
except AppError as e:
    assert e.status_code == 503

# 401 -> friendly error (poora fetch rukta hai)
settings.pexels_api_key = "bad"
ps._make_client = lambda: httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(401)))
try:
    ps.fetch_media_for_plan(plan, "job3")
    raise SystemExit("FAIL: 401 not handled")
except AppError as e:
    assert "API key" in e.message

# 429 baar baar -> friendly rate-limit error
ps._make_client = lambda: httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(429)))
try:
    ps.fetch_media_for_plan(plan, "job4")
    raise SystemExit("FAIL: 429 not handled")
except AppError as e:
    assert e.status_code == 429

print("OK: saare checks pass")
