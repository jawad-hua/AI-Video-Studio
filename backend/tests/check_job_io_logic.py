"""Offline check: job file ka safe padhna/likhna (Windows "Permission denied" race ke liye).

Run (backend folder se):  python -m tests.check_job_io_logic
"""
import tempfile
import threading
from pathlib import Path

from app.models.jobs import GenerateVideoRequest
from app.services import job_service as js

js.JOBS_DIR = Path(tempfile.mkdtemp())
js.time.sleep = lambda s: None  # retry ka intezar test mein nahi

job = js.create_job(GenerateVideoRequest(topic="Concurrent test topic"))

# 1) Ek thread progress likhta rahe, doosra status padhta rahe: koi error nahi
errors: list[Exception] = []
done = threading.Event()


def writer():
    try:
        for i in range(300):
            js.update_job(job.job_id, progress=i % 100)
    except Exception as e:  # noqa: BLE001
        errors.append(e)
    finally:
        done.set()


def reader():
    try:
        while not done.is_set():
            js.load_job(job.job_id)
    except Exception as e:  # noqa: BLE001
        errors.append(e)


threads = [threading.Thread(target=writer)] + [threading.Thread(target=reader) for _ in range(3)]
for t in threads:
    t.start()
for t in threads:
    t.join()
assert not errors, errors

# 2) Windows jaisa PermissionError do baar aaye, teesri baar chale -> update kaam kare
real_replace, calls = js.os.replace, {"n": 0}


def flaky_replace(src, dst):
    calls["n"] += 1
    if calls["n"] <= 2:
        raise PermissionError(13, "Permission denied")
    return real_replace(src, dst)


js.os.replace = flaky_replace
js.update_job(job.job_id, progress=42)
js.os.replace = real_replace
assert calls["n"] == 3 and js.load_job(job.job_id).progress == 42

# 3) Padhne mein bhi retry
real_read, rc = Path.read_text, {"n": 0}


def flaky_read(self, *a, **k):
    rc["n"] += 1
    if rc["n"] <= 2:
        raise PermissionError(13, "Permission denied")
    return real_read(self, *a, **k)


Path.read_text = flaky_read
assert js.load_job(job.job_id).progress == 42
Path.read_text = real_read

# 4) Hamesha PermissionError ho to andar hi andar atak nahi jata, error upar aata hai
Path.read_text = lambda self, *a, **k: (_ for _ in ()).throw(PermissionError(13, "Permission denied"))
try:
    js.load_job(job.job_id)
    raise SystemExit("FAIL: permanent PermissionError swallowed")
except PermissionError:
    pass
finally:
    Path.read_text = real_read

print("OK: saare checks pass")
