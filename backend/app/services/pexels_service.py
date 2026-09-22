import logging
import os
import struct
import time
import zlib
from pathlib import Path
from typing import Callable

import httpx

from app.config import MEDIA_DIR, settings
from app.models.media import MediaItem, MediaResult
from app.models.schemas import Scene, VideoPlan
from app.utils.errors import AppError

log = logging.getLogger(__name__)

VIDEOS_URL = "https://api.pexels.com/videos/search"
PHOTOS_URL = "https://api.pexels.com/v1/search"

MAX_QUERIES = 3             # ek scene ke liye max alag search terms
MAX_VIDEO_SECONDS = 40      # bahut lambi clips skip (badi files)
MAX_VIDEO_BYTES = 40_000_000
MAX_IMAGE_BYTES = 10_000_000
MIN_FILE_BYTES = 5_000
MAX_SHORT_SIDE = 1200       # 4K files skip (RAM aur disk bachane ke liye)


def _make_client() -> httpx.Client:
    # NOTE: default headers mein API key nahi hai. Key sirf Pexels API calls ke saath jati hai,
    # download links (CDN) ko nahi.
    return httpx.Client(follow_redirects=True)


# ---------------------------------------------------------------- Pexels API
def _api_get(client: httpx.Client, url: str, params: dict) -> dict:
    key = settings.pexels_api_key.strip()
    for attempt in range(3):
        last = attempt == 2
        try:
            r = client.get(url, params=params, headers={"Authorization": key}, timeout=20)
        except httpx.HTTPError as e:
            log.warning("Pexels network error (attempt %s): %s", attempt + 1, type(e).__name__)
            if last:
                raise AppError("Could not reach Pexels. Check your internet connection and try again.", 503)
            time.sleep(1.5 * (attempt + 1))
            continue

        if r.status_code == 200:
            log.info("Pexels requests remaining this hour: %s", r.headers.get("x-ratelimit-remaining", "?"))
            try:
                return r.json()
            except ValueError:
                log.error("Pexels invalid JSON: %s", r.text[:200])
                return {}
        if r.status_code in (401, 403):
            raise AppError("Pexels rejected the API key. Check PEXELS_API_KEY in backend/.env.", 503)
        if r.status_code == 429 or r.status_code >= 500:
            log.warning("Pexels status %s (attempt %s)", r.status_code, attempt + 1)
            if last:
                if r.status_code == 429:
                    raise AppError("Pexels rate limit reached (200 requests/hour). Try again later.", 429)
                raise AppError("Pexels is temporarily unavailable. Please try again shortly.", 503)
            time.sleep(2.0 * (attempt + 1))
            continue

        log.warning("Pexels status %s for query %r: %s", r.status_code, params.get("query"), r.text[:200])
        return {}  # is query par kuch nahi mila, baaki chalta rahe
    return {}


# ------------------------------------------------------------ choose media
def _queries(scene: Scene) -> list[str]:
    kws = [k.strip() for k in scene.search_keywords if k.strip()]
    qs: list[str] = []
    if len(kws) >= 2:
        qs.append(" ".join(kws[:2]))
    qs += kws
    if scene.visual_description.strip():
        qs.append(" ".join(scene.visual_description.split()[:3]))
    seen, out = set(), []
    for q in qs:
        if q.lower() not in seen:
            seen.add(q.lower())
            out.append(q)
    return out[:MAX_QUERIES]


def _pick_video_file(video: dict, want_short_side: int) -> dict | None:
    files = [
        f for f in video.get("video_files", [])
        if f.get("file_type") == "video/mp4" and f.get("link") and f.get("width") and f.get("height")
        and not (f.get("size") and f["size"] > MAX_VIDEO_BYTES)
    ]
    portrait = [f for f in files if f["height"] > f["width"]]
    pool = portrait or files
    if not pool:
        return None
    short = lambda f: min(f["width"], f["height"])  # noqa: E731
    good = [f for f in pool if want_short_side <= short(f) <= MAX_SHORT_SIDE]
    if good:
        return min(good, key=short)  # kaafi bara, lekin sabse chhoti file
    small = [f for f in pool if short(f) <= MAX_SHORT_SIDE]
    return max(small, key=short) if small else None


def _video_candidates(videos: list[dict], need_dur: float, used: set[int], want: int) -> list[tuple[dict, dict]]:
    scored = []
    for idx, v in enumerate(videos):
        dur = v.get("duration") or 0
        if v.get("id") in used or dur > MAX_VIDEO_SECONDS:
            continue
        f = _pick_video_file(v, want)
        if not f:
            continue
        scored.append((not (f["height"] > f["width"]), dur < need_dur, idx, v, f))
    scored.sort(key=lambda t: t[:3])  # vertical pehle, phir kaafi lambi, phir Pexels ka relevance order
    return [(v, f) for *_, v, f in scored]


# ---------------------------------------------------------------- download
class _TooBig(Exception):
    pass


def _valid_file(path: Path, kind: str) -> bool:
    try:
        if path.stat().st_size < MIN_FILE_BYTES:
            return False
        head = path.open("rb").read(12)
    except OSError:
        return False
    if kind == "video":
        return head[4:8] == b"ftyp"  # mp4/mov
    return head.startswith(b"\xff\xd8\xff") or head.startswith(b"\x89PNG")


def _download(client: httpx.Client, url: str, dest: Path, kind: str) -> bool:
    if not url.startswith("https://"):
        return False
    max_bytes = MAX_VIDEO_BYTES if kind == "video" else MAX_IMAGE_BYTES
    tmp = dest.with_name(dest.name + ".part")
    for attempt in range(2):
        try:
            with client.stream("GET", url, timeout=60) as r:
                if r.status_code != 200:
                    log.warning("Download status %s", r.status_code)
                    return False
                if int(r.headers.get("content-length") or 0) > max_bytes:
                    log.warning("Download too large (header)")
                    return False
                total = 0
                with tmp.open("wb") as fh:
                    for chunk in r.iter_bytes(65536):
                        total += len(chunk)
                        if total > max_bytes:
                            raise _TooBig
                        fh.write(chunk)
        except _TooBig:
            log.warning("Download exceeded %s bytes, skipped", max_bytes)
            tmp.unlink(missing_ok=True)
            return False
        except httpx.HTTPError as e:
            log.warning("Download error (attempt %s): %s", attempt + 1, type(e).__name__)
            tmp.unlink(missing_ok=True)
            time.sleep(1.5)
            continue

        if _valid_file(tmp, kind):
            os.replace(tmp, dest)
            return True
        log.warning("Downloaded file failed validation (%s)", kind)
        tmp.unlink(missing_ok=True)
        return False
    return False


# ---------------------------------------------------------------- fallback
_PALETTE = [
    ((30, 27, 75), (14, 116, 144)),
    ((49, 46, 129), (109, 40, 217)),
    ((15, 23, 42), (30, 64, 175)),
    ((24, 24, 27), (91, 33, 182)),
]


def make_placeholder(path: Path, index: int, width: int, height: int) -> None:
    """Pure Python gradient PNG (koi extra library ya FFmpeg nahi chahiye)."""
    top, bottom = _PALETTE[index % len(_PALETTE)]
    rows = []
    for y in range(height):
        t = y / max(1, height - 1)
        px = bytes(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        rows.append(b"\x00" + px * width)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"".join(rows), 6))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(png)


# ---------------------------------------------------------------- per scene
def _rel(path: Path) -> str:
    return path.relative_to(MEDIA_DIR.parent.parent).as_posix()  # backend/ ke relative


def _clear_scene_files(job_dir: Path, n: int) -> None:
    for old in job_dir.glob(f"scene_{n:02d}.*"):
        old.unlink(missing_ok=True)


def _fetch_scene(client: httpx.Client, scene: Scene, job_dir: Path,
                 used_v: set[int], used_p: set[int]) -> MediaItem:
    n = scene.scene_number
    _clear_scene_files(job_dir, n)
    queries = _queries(scene)
    want = min(settings.render_width, settings.render_height)

    # 1) Video: pehle vertical (3 queries tak), phir koi bhi orientation (sirf pehli query)
    for orientation, qs in (("portrait", queries), (None, queries[:1])):
        for q in qs:
            params = {"query": q, "per_page": 15, "size": "small"}
            if orientation:
                params["orientation"] = orientation
            data = _api_get(client, VIDEOS_URL, params)
            for v, f in _video_candidates(data.get("videos", []), scene.duration, used_v, want)[:2]:
                dest = job_dir / f"scene_{n:02d}.mp4"
                if _download(client, f["link"], dest, "video"):
                    used_v.add(v["id"])
                    return MediaItem(
                        scene_number=n, type="video", source="pexels", file=_rel(dest), query=q,
                        pexels_id=v["id"], pexels_url=v.get("url"), credit=(v.get("user") or {}).get("name"),
                        width=f["width"], height=f["height"], duration=v.get("duration"),
                    )

    # 2) Photo (vertical)
    for q in queries:
        data = _api_get(client, PHOTOS_URL, {"query": q, "per_page": 10, "orientation": "portrait"})
        for p in data.get("photos", []):
            if p.get("id") in used_p:
                continue
            src = p.get("src") or {}
            link = src.get("portrait") or src.get("large")
            dest = job_dir / f"scene_{n:02d}.jpg"
            if link and _download(client, link, dest, "image"):
                used_p.add(p["id"])
                return MediaItem(
                    scene_number=n, type="image", source="pexels", file=_rel(dest), query=q,
                    pexels_id=p["id"], pexels_url=p.get("url"), credit=p.get("photographer"),
                    width=p.get("width"), height=p.get("height"),
                )

    # 3) Fallback placeholder
    log.warning("Scene %s: no Pexels media found, using placeholder", n)
    dest = job_dir / f"scene_{n:02d}.png"
    make_placeholder(dest, n, settings.render_width, settings.render_height)
    return MediaItem(
        scene_number=n, type="image", source="fallback", file=_rel(dest),
        query=queries[0] if queries else None, width=settings.render_width, height=settings.render_height,
    )


def fetch_media_for_plan(plan: VideoPlan, job_id: str, on_progress: Callable[[float], None] | None = None) -> MediaResult:
    if not settings.pexels_api_key.strip():
        raise AppError("Pexels API key is missing. Add PEXELS_API_KEY to backend/.env and restart the server.", 503)

    job_dir = (MEDIA_DIR / job_id).resolve()
    if not job_dir.is_relative_to(MEDIA_DIR.resolve()):  # unsafe path se bachao
        raise AppError("Invalid job id.", 400)
    job_dir.mkdir(parents=True, exist_ok=True)

    for i, sc in enumerate(plan.scenes, start=1):
        sc.scene_number = i  # file names ke liye 1..N pakka karo

    items: list[MediaItem] = []
    used_v: set[int] = set()
    used_p: set[int] = set()
    with _make_client() as client:
        for k, scene in enumerate(plan.scenes):
            if on_progress:
                on_progress(k / len(plan.scenes))
            try:
                items.append(_fetch_scene(client, scene, job_dir, used_v, used_p))
            except AppError:
                raise  # key galat / rate limit / Pexels down: poora fetch rok do, saaf message do
            except Exception:
                # Ek scene ki koi ajeeb galti poori video ko na roke
                log.exception("Scene %s media fetch failed, using placeholder", scene.scene_number)
                n = scene.scene_number
                _clear_scene_files(job_dir, n)
                dest = job_dir / f"scene_{n:02d}.png"
                make_placeholder(dest, n, settings.render_width, settings.render_height)
                items.append(MediaItem(scene_number=n, type="image", source="fallback", file=_rel(dest)))

    result = MediaResult(
        job_id=job_id,
        videos=sum(i.type == "video" for i in items),
        images=sum(i.type == "image" and i.source == "pexels" for i in items),
        fallbacks=sum(i.source == "fallback" for i in items),
        items=items,
    )
    (job_dir / "media.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return result
