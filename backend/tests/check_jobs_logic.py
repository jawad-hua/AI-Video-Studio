"""Offline end-to-end check: job system + video API (fake script/media/voice, asli subtitles + FFmpeg render).

Ye backend ki copy temp folder mein banata hai, isliye aap ki asli generated/ files ko haath nahi lagata.
Run (backend folder se):  python -m tests.check_jobs_logic
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

backend = Path(__file__).resolve().parent.parent
if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
    raise SystemExit("FFmpeg/ffprobe not found: is test ke liye chahiye")

tmp = Path(tempfile.mkdtemp())
shutil.copytree(backend / "app", tmp / "app", ignore=shutil.ignore_patterns("__pycache__"))
(tmp / "assets").mkdir()
if (backend / "assets" / "fonts").exists():
    shutil.copytree(backend / "assets" / "fonts", tmp / "assets" / "fonts")
(tmp / "assets" / "music").mkdir()
shutil.copy(backend / "tests" / "_jobs_driver.py", tmp / "driver.py")

r = subprocess.run([sys.executable, "driver.py"], cwd=tmp, env={**os.environ, "PYTHONPATH": str(tmp)})
raise SystemExit(r.returncode)
