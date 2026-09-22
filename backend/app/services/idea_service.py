"""Short-form video topic ideas (ek chhota Groq call)."""
import logging
from typing import Callable

from app.services.groq_service import chat_json
from app.services.script_service import extract_json
from app.utils.errors import AppError

log = logging.getLogger(__name__)


def _messages(niche: str | None, language: str) -> list[dict]:
    topic = niche.strip() if niche and niche.strip() else "technology, AI and learning"
    lang = "Urdu (Urdu script)" if language == "ur" else "English"
    return [
        {"role": "system", "content": "You suggest viral short-form video topics. Reply with ONLY one valid JSON object."},
        {"role": "user", "content": (
            f"Give 8 catchy TikTok/Reels video topics about: {topic}.\n"
            f"Language: {lang}. Each topic is specific and curiosity-driven, max 12 words, no hashtags, no numbering.\n"
            'JSON format: {"ideas": ["...", "..."]}'
        )},
    ]


def create_ideas(niche: str | None, language: str = "en", chat_fn: Callable[[list[dict]], str] = chat_json) -> list[str]:
    for attempt in range(2):
        raw = chat_fn(_messages(niche, language))
        try:
            items = extract_json(raw).get("ideas", [])
        except ValueError:
            log.warning("Ideas attempt %s: invalid JSON", attempt + 1)
            continue
        seen, ideas = set(), []
        for x in items if isinstance(items, list) else []:
            t = str(x).strip().strip('"')
            if 5 <= len(t) <= 120 and t.lower() not in seen:
                seen.add(t.lower())
                ideas.append(t)
        if len(ideas) >= 4:
            return ideas[:8]
    raise AppError("Could not get ideas right now. Please try again.", 502)
