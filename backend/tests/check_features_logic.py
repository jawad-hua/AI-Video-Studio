"""Offline check: nayi features (ideas, hashtags/caption, watermark, ETA history). Internet nahi chahiye.

Run (backend folder se):  python -m tests.check_features_logic
"""
import json
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.models.jobs import GenerateVideoRequest
from app.models.schemas import Scene, VideoPlan
from app.services import idea_service as ideas
from app.services import job_service as js
from app.utils.errors import AppError

# 1) Ideas: dedupe, filter, retry
good = json.dumps({"ideas": ["How AI writes code in seconds", "5 free AI tools for students", "how ai writes code in seconds",
                              "Why Python is loved by beginners", "hi", "What is an AI agent really?"]})
out = ideas.create_ideas("ai", "en", lambda m: good)
assert out == ["How AI writes code in seconds", "5 free AI tools for students", "Why Python is loved by beginners",
               "What is an AI agent really?"], out                # duplicate + chhota "hi" nikal gaye
calls = []


def flaky(m):
    calls.append(1)
    return "not json" if len(calls) == 1 else good


assert len(ideas.create_ideas(None, "en", flaky)) == 4 and len(calls) == 2
try:
    ideas.create_ideas("ai", "en", lambda m: json.dumps({"ideas": ["only one idea here"]}))
    raise SystemExit("FAIL: too few ideas accepted")
except AppError as e:
    assert e.status_code == 502

# 2) Ideas route
c = TestClient(app, raise_server_exceptions=False)
settings.groq_api_key = ""
r = c.post("/api/ideas", json={"niche": "fitness"})
assert r.status_code == 503 and "GROQ_API_KEY" in r.json()["detail"], r.text
assert c.post("/api/ideas", json={"niche": "x" * 80}).status_code == 422
assert c.post("/api/ideas", json={"language": "fr"}).status_code == 422

# 3) Hashtags / caption cleaning
scenes = [Scene(scene_number=i + 1, narration="Some narration.", search_keywords=["a"]) for i in range(5)]
plan = VideoPlan(title="T title", caption="Cap", hashtags="ai, #Tech  machine-learning ai #", scenes=scenes)
assert plan.hashtags == ["#ai", "#Tech", "#machinelearning"], plan.hashtags
assert VideoPlan(title="T title", scenes=scenes).hashtags == [] and VideoPlan(title="T title", scenes=scenes).caption == ""
assert len(VideoPlan(title="T title", hashtags=[f"t{i}" for i in range(20)], scenes=scenes).hashtags) == 8

# 4) Watermark sanitize + speed validation
assert GenerateVideoRequest(topic="Sanitize test", watermark="{x}\\ y\n").watermark == "x y"
assert GenerateVideoRequest(topic="Sanitize test", watermark="   ").watermark is None
assert GenerateVideoRequest(topic="Sanitize test").speed == "fast"
try:
    GenerateVideoRequest(topic="Sanitize test", speed="turbo")
    raise SystemExit("FAIL: bad speed accepted")
except ValueError:
    pass

# 5) ETA history: sirf pichhle 5 ka average
js._history.clear()
assert js.typical_seconds() is None
for t in (100, 100, 100, 100, 100, 40):
    js.record_completion(t)
assert js.typical_seconds() == 88, js.typical_seconds()  # (100*4 + 40) / 5

print("OK: saare checks pass")
