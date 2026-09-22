import logging
import time

import httpx

from app.config import settings
from app.utils.errors import AppError

log = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def chat_json(messages: list[dict], *, max_retries: int = 2, timeout: float = 45.0) -> str:
    """Groq ko messages bhejo, JSON text wapas lo. Network/rate-limit par retry karta hai."""
    key = settings.groq_api_key.strip()
    if not key:
        raise AppError("Groq API key is missing. Add GROQ_API_KEY to backend/.env and restart the server.", 503)

    payload = {
        "model": settings.groq_model,
        "messages": messages,
        "temperature": 0.7,
        "max_completion_tokens": 4000,  # reasoning models mein thinking tokens bhi isi limit se jaate hain
        "response_format": {"type": "json_object"},
    }
    # gpt-oss reasoning model hai: "low" effort = tez jawab, kam tokens
    if "gpt-oss" in settings.groq_model:
        payload["reasoning_effort"] = "low"
    headers = {"Authorization": f"Bearer {key}"}  # key kabhi log nahi hoti

    for attempt in range(max_retries + 1):
        last = attempt == max_retries
        try:
            with httpx.Client(timeout=timeout) as client:
                r = client.post(GROQ_URL, json=payload, headers=headers)
        except httpx.HTTPError as e:
            log.warning("Groq network error (attempt %s): %s", attempt + 1, type(e).__name__)
            if last:
                raise AppError("Could not reach Groq. Check your internet connection and try again.", 503)
            time.sleep(1.5 * (attempt + 1))
            continue

        if r.status_code == 200:
            try:
                return r.json()["choices"][0]["message"]["content"] or ""
            except (KeyError, IndexError, ValueError):
                log.error("Groq unexpected response body: %s", r.text[:300])
                raise AppError("Groq sent an unexpected response. Please try again.", 502)

        if r.status_code in (401, 403):
            log.error("Groq auth error %s", r.status_code)
            raise AppError("Groq rejected the API key. Check GROQ_API_KEY in backend/.env.", 503)

        if r.status_code == 429 or r.status_code >= 500:
            log.warning("Groq status %s (attempt %s)", r.status_code, attempt + 1)
            if last:
                if r.status_code == 429:
                    raise AppError("Groq rate limit reached. Wait a minute and try again.", 429)
                raise AppError("Groq is temporarily unavailable. Please try again shortly.", 503)
            try:
                wait = min(float(r.headers.get("retry-after", "")), 15.0)
            except ValueError:
                wait = 2.0 * (attempt + 1)
            time.sleep(wait)
            continue

        # 400/404 etc: aksar galat model naam
        log.error("Groq request failed %s: %s", r.status_code, r.text[:300])
        raise AppError("Groq request failed. Check GROQ_MODEL in backend/.env.", 502)

    raise AppError("Groq request failed. Please try again.", 502)  # yahan tak nahi pahunchna chahiye
