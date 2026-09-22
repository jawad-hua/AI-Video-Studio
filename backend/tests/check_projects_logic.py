"""Offline check: Projects list + delete (fake jobs, temp folders).

Run (backend folder se):  python -m tests.check_projects_logic
"""
import tempfile
import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.models.render import RenderResult
from app.services import job_service as js
from app.services import project_service as ps
from app.models.jobs import GenerateVideoRequest

tmp = Path(tempfile.mkdtemp())
dirs = {n: tmp / n for n in ("jobs", "media", "audio", "subtitles", "videos")}
for d in dirs.values():
    d.mkdir()
js.JOBS_DIR, js.AUDIO_DIR, js.MEDIA_DIR = dirs["jobs"], dirs["audio"], dirs["media"]
ps.JOBS_DIR, ps.MEDIA_DIR, ps.AUDIO_DIR = dirs["jobs"], dirs["media"], dirs["audio"]
ps.SUBTITLES_DIR, ps.VIDEOS_DIR = dirs["subtitles"], dirs["videos"]


def make(topic, status, **kw):
    job = js.create_job(GenerateVideoRequest(topic=topic))
    time.sleep(0.01)  # created_at alag ho
    js.update_job(job.job_id, status=status, **kw)
    for name in ("media", "audio", "subtitles"):
        (dirs[name] / job.job_id).mkdir()
        (dirs[name] / job.job_id / "x.txt").write_text("x")
    (dirs["videos"] / f"{job.job_id}.mp4").write_bytes(b"x")
    (dirs["jobs"] / f"{job.job_id}_plan.json").write_text("{}")
    return job.job_id


result = RenderResult(job_id="x", file="f", duration=42.5, width=720, height=1280, size_mb=3.1, transitions=True, music=None)
done = make("First topic here", "completed", title="Done Video", progress=100, result=result)
bad = make("Second topic here", "failed", error="Groq is down")
run = make("Third topic here", "rendering", progress=75)
(dirs["jobs"] / "last_plan.json").write_text("{}")   # ye list mein nahi aani chahiye
(dirs["jobs"] / "broken0000ab.json").write_text("{not json")  # kharab file list nahi rokti

items = ps.list_projects()
assert [i.job_id for i in items] == [run, bad, done], [i.topic for i in items]  # naya pehle
by = {i.job_id: i for i in items}
assert by[done].title == "Done Video" and by[done].duration == 42.5
assert by[done].thumbnail_url == f"/api/video/{done}/thumb/1" and by[done].download_url.endswith("/download")
assert by[bad].error == "Groq is down" and by[bad].video_url is None
assert by[run].title == "Third topic here"  # title nahi to topic

c = TestClient(app, raise_server_exceptions=False)
assert len(c.get("/api/projects").json()) == 3
assert c.delete(f"/api/projects/{run}").status_code == 409        # chal raha hai: delete nahi
assert c.delete(f"/api/projects/{done}").status_code == 204
assert c.delete("/api/projects/aaaaaaaaaaaa").status_code == 404
assert c.delete("/api/projects/not-valid").status_code == 404
for name in ("media", "audio", "subtitles"):
    assert not (dirs[name] / done).exists()
assert not (dirs["videos"] / f"{done}.mp4").exists() and not (dirs["jobs"] / f"{done}.json").exists()
assert (dirs["videos"] / f"{bad}.mp4").exists()                    # doosre jobs safe
assert c.delete(f"/api/projects/{bad}").status_code == 204
assert [i.job_id for i in ps.list_projects()] == [run]
# Prune: sirf naye `keep` finished jobs bachte hain, chalta hua job kabhi delete nahi hota
extra = [make(f"Old topic number {i}", "completed", progress=100) for i in range(4)]
assert ps.prune_old_projects(keep=2) == 2      # 4 finished mein se 2 purane hatenge
left = [i.job_id for i in ps.list_projects()]
assert run in left and len(left) == 3, left    # run + 2 sabse naye
assert extra[-1] in left and extra[-2] in left and extra[0] not in left
print("OK: saare checks pass")
