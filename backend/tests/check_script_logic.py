"""Offline check: Groq/internet ke bina script logic test karta hai.

Run (backend folder se):  python -m tests.check_script_logic
"""
import json

from app.models.schemas import ScriptRequest
from app.services.script_service import create_script, extract_json
from app.utils.duration import normalize_durations
from app.utils.errors import AppError


def fake_plan(n_scenes: int, dur: float = 8) -> dict:
    return {
        "title": "Test video",
        "scenes": [
            {
                "scene_number": i + 1,
                "duration": dur,
                "narration": f"Narration for scene {i + 1}.",
                "visual_description": "a visual",
                "search_keywords": "city, night" if i == 0 else ["ai", "robot"],  # string bhi chalegi
                "subtitle": "",
                "transition": "wipe" if i == 1 else "fade",  # unknown transition
            }
            for i in range(n_scenes)
        ],
    }


def make_chat(replies):
    calls = {"n": 0}

    def chat(messages):
        r = replies[min(calls["n"], len(replies) - 1)]
        calls["n"] += 1
        return r

    chat.calls = calls
    return chat


req60 = ScriptRequest(topic="What is Generative AI?", duration=60)
req30 = ScriptRequest(topic="What is Generative AI?", duration=30)

# 1) Duration: 10 scenes x 8s = 80s -> 60s
d = normalize_durations([8] * 10, 60)
assert sum(d) <= 60 and abs(sum(d) - 60) < 1e-6 and min(d) >= 2, d
# 2) Chhota total waise hi rehta hai
assert normalize_durations([4, 5, 6], 60) == [4.0, 5.0, 6.0]
# 3) Bahut chhota target: sab barabar, total kabhi zyada nahi
d = normalize_durations([8] * 10, 15)
assert sum(d) <= 15 + 1e-6, d
# 4) 60 se upar target bhi 60 par cap
assert sum(normalize_durations([20] * 10, 100)) <= 60 + 1e-6

# 5) JSON repair: fences + trailing comma
raw = "Here you go:\n```json\n" + json.dumps(fake_plan(9)).replace('"fade"}]', '"fade",}]') + "\n```"
assert extract_json(raw)["title"] == "Test video"

# 6) Normal flow: markdown fence + 80 sec -> total <= 60
chat = make_chat(["```json\n" + json.dumps(fake_plan(10)) + "\n```"])
plan = create_script(req60, chat)
assert len(plan.scenes) == 10 and plan.total_duration <= 60, plan.total_duration
assert [s.scene_number for s in plan.scenes] == list(range(1, 11))
assert plan.scenes[0].search_keywords == ["city", "night"]
assert plan.scenes[1].transition == "fade"  # "wipe" -> fade
assert plan.scenes[0].subtitle  # khali subtitle bhar gaya

# 7) 30 sec request
plan = create_script(req30, make_chat([json.dumps(fake_plan(9))]))
assert plan.total_duration <= 30, plan.total_duration

# 8) Pehli reply kharab JSON, doosri theek -> retry chala
chat = make_chat(["sorry, I cannot do that", json.dumps(fake_plan(8, 6))])
plan = create_script(req60, chat)
assert chat.calls["n"] == 2 and len(plan.scenes) == 8

# 9) 14 scenes (schema limit 12 se zyada) -> retry, phir 9 scenes
chat = make_chat([json.dumps(fake_plan(14)), json.dumps(fake_plan(9, 6))])
plan = create_script(req60, chat)
assert len(plan.scenes) == 9

# 10) 12 scenes -> pehle 9 + aakhri = 10 scenes
plan = create_script(req60, make_chat([json.dumps(fake_plan(12, 5))]))
assert len(plan.scenes) == 10 and plan.scenes[-1].narration.endswith("12.")

# 11) Hamesha kharab reply -> AppError (crash nahi)
try:
    create_script(req60, make_chat(["garbage"]))
    raise SystemExit("FAIL: AppError expected")
except AppError as e:
    assert e.status_code == 502

print("OK: saare checks pass")
