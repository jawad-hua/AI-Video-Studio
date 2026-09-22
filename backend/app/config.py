from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ folder ka path (is file se do level upar)
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # .env se values aati hain, keys kabhi hardcode nahi karni
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    pexels_api_key: str = ""
    tts_provider: str = "edge"
    tts_voice: str = "en-US-AndrewNeural"
    render_width: int = 720
    render_height: int = 1280

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

# generated files ke folders
GENERATED_DIR = BASE_DIR / "generated"
VIDEOS_DIR = GENERATED_DIR / "videos"
AUDIO_DIR = GENERATED_DIR / "audio"
SUBTITLES_DIR = GENERATED_DIR / "subtitles"
MEDIA_DIR = GENERATED_DIR / "media"
JOBS_DIR = GENERATED_DIR / "jobs"


def ensure_dirs() -> None:
    # folder na ho to bana do (server start par ek baar)
    for d in (VIDEOS_DIR, AUDIO_DIR, SUBTITLES_DIR, MEDIA_DIR, JOBS_DIR):
        d.mkdir(parents=True, exist_ok=True)
