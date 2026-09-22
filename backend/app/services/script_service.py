import json
import logging
import re
from typing import Callable

from app.models.schemas import ScriptRequest, VideoPlan
from app.services.groq_service import chat_json
from app.utils.duration import normalize_durations
from app.utils.errors import AppError

log = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
WORDS_PER_SEC = 2.4  # voice-over ki average speed

STYLE_GUIDE = {
    "cinematic": "dramatic, emotional, evocative; slow wide cinematic visuals",
    "modern-tech": "energetic, clear, modern; futuristic technology visuals",
    "documentary": "calm, factual, informative; real-world documentary visuals",
    "minimal": "simple short sentences, quiet tone; clean minimal visuals",
}


def build_messages(req: ScriptRequest) -> list[dict]:
    words = int(req.duration * WORDS_PER_SEC)
    lang = (
        "Urdu (Urdu script) for narration and subtitle"
        if req.language == "ur"
        else "English for narration and subtitle"
    )
    system = (
        "You are a short-form video scriptwriter for TikTok and Facebook Reels. "
        "Reply with ONLY one valid JSON object. No markdown, no comments, no extra text."
    )
    user = f"""Create a video plan.

Topic: {req.topic}
Style: {STYLE_GUIDE[req.style]}
Language: {lang}. visual_description and search_keywords must always be in English.

Rules:
- 8 to 10 scenes. Scene 1 is a strong hook. The last scene is a short closing line.
- Each scene duration is 4 to 8 seconds. All durations added together must be at most {req.duration} seconds.
- Total narration about {words} words (about {WORDS_PER_SEC} words per second).
- search_keywords: 2 or 3 concrete English terms good for stock footage search (no brand names, no abstract words).
- subtitle: short on-screen text, max 6 words.
- transition: one of fade, slide, zoom.
- caption: one engaging post caption (max 150 characters) that ends with a call to action.
- hashtags: 5 to 8 relevant hashtags, each starting with #.

JSON format:
{{"title": "...", "caption": "...", "hashtags": ["#..."], "scenes": [{{"scene_number": 1, "duration": 6, "narration": "...", "visual_description": "...", "search_keywords": ["...", "..."], "subtitle": "...", "transition": "fade"}}]}}"""
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def extract_json(text: str) -> dict:
    """LLM reply se JSON nikalo: ```json fences hatao, trailing comma aur smart quotes theek karo."""
    t = (text or "").strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.IGNORECASE)
    start, end = t.find("{"), t.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("No JSON object found in reply")
    t = t[start : end + 1]

    try:
        data = json.loads(t)
    except json.JSONDecodeError:
        fixed = t.replace("\u201c", '"').replace("\u201d", '"').replace("\u2019", "'")
        fixed = re.sub(r",\s*([}\]])", r"\1", fixed)  # trailing commas
        data = json.loads(fixed)  # ab bhi fail ho to ValueError upar jayega

    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object")
    return data


def _short_error(e: Exception) -> str:
    errors = getattr(e, "errors", None)
    if callable(errors):
        parts = [f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}" for err in errors()[:3]]
        return "; ".join(parts)
    return str(e)[:200]


def _fit_scene_count(plan: VideoPlan) -> VideoPlan:
    # 10 se zyada scenes: pehle 9 + aakhri (closing line) rakho
    if len(plan.scenes) > 10:
        plan.scenes = plan.scenes[:9] + [plan.scenes[-1]]
    return plan


def _finalize(plan: VideoPlan, target: int) -> VideoPlan:
    for i, s in enumerate(plan.scenes, start=1):
        s.scene_number = i
    durations = normalize_durations([s.duration for s in plan.scenes], target)
    for s, d in zip(plan.scenes, durations):
        s.duration = d
    return plan


def create_script(req: ScriptRequest, chat_fn: Callable[[list[dict]], str] = chat_json) -> VideoPlan:
    base = build_messages(req)
    messages = base
    best: VideoPlan | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        raw = chat_fn(messages)  # Groq down/key missing ho to AppError seedha upar jata hai
        try:
            plan = _fit_scene_count(VideoPlan.model_validate(extract_json(raw)))
        except ValueError as e:  # bad JSON aur Pydantic ValidationError dono
            problem = _short_error(e)
            log.warning("Script attempt %s invalid: %s", attempt, problem)
            feedback = f"That reply was invalid ({problem}). Return ONLY the corrected, complete JSON."
        else:
            if 8 <= len(plan.scenes) <= 10:
                best = plan
                break
            best = best or plan  # 5-7 scenes: fallback ke taur par rakho
            feedback = f"You returned {len(plan.scenes)} scenes. Return exactly 8 to 10 scenes as complete JSON."
            log.warning("Script attempt %s scene count %s", attempt, len(plan.scenes))

        messages = base + [
            {"role": "assistant", "content": (raw or "")[:3000]},
            {"role": "user", "content": feedback},
        ]

    if best is None:
        raise AppError("The AI returned an invalid script. Please try again.", 502)

    return _finalize(best, req.duration)
