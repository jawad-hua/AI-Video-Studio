"""Offline check: FFmpeg ka real progress, timeout aur error handling. FFmpeg chahiye, internet nahi.

Run (backend folder se):  python -m tests.check_progress_logic
"""
import shutil
import tempfile
from pathlib import Path

from app.services.video_service import FFmpegError, run_ffmpeg
from app.services import pipeline_service as ps

if not shutil.which("ffmpeg"):
    raise SystemExit("FFmpeg not found: is test ke liye chahiye")

tmp = Path(tempfile.mkdtemp())

# 1) Progress: 0..1 tak badhta hai, kabhi peechhe nahi (encode ke dauran)
seen = []
run_ffmpeg(["-f", "lavfi", "-i", "testsrc=s=320x240:d=4", "-c:v", "libx264", "-preset", "ultrafast", str(tmp / "a.mp4")],
           on_progress=seen.append, total_seconds=4.0)
assert (tmp / "a.mp4").exists() and seen, seen
assert all(0 <= x <= 1 for x in seen) and seen == sorted(seen) and seen[-1] > 0.9, seen

# 2) Bina callback ke purana tareeqa chalta hai
run_ffmpeg(["-f", "lavfi", "-i", "testsrc=s=320x240:d=1", str(tmp / "b.mp4")])
assert (tmp / "b.mp4").exists()

# 3) Galat command -> FFmpegError (progress mode mein bhi)
for kw in ({}, {"on_progress": lambda f: None, "total_seconds": 3.0}):
    try:
        run_ffmpeg(["-i", str(tmp / "missing.mp4"), str(tmp / "c.mp4")], **kw)
        raise SystemExit("FAIL: bad command accepted")
    except FFmpegError:
        pass

# 4) Timeout: real-time (-re) 30 sec ka job 1 sec mein kill hota hai
try:
    run_ffmpeg(["-re", "-f", "lavfi", "-i", "testsrc=s=160x120:d=30", "-f", "null", "-"],
               timeout=1, on_progress=lambda f: None, total_seconds=30.0)
    raise SystemExit("FAIL: timeout not enforced")
except FFmpegError as e:
    assert "timeout" in str(e)

# 5) Reporter: peechhe nahi jata, hi% se aage nahi
ps.job_service.update_job = lambda jid, **f: written.append(f["progress"])
written: list[int] = []
rep = ps._reporter("x", 75, 99)
for f in (0.1, 0.5, 0.3, 1.0, 5.0):
    rep(f)
assert written == sorted(written) and written[-1] == 99 and max(written) <= 99, written

print("OK: saare checks pass")
