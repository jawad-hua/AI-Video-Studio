import sys
from pathlib import Path
import spaces

backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from app.main import app


@spaces.GPU(duration=1)
def _zerogpu_probe():
    return "ok"


if __name__ == "__main__":
    try:
        from spaces.zero import startup as zero_startup
        zero_startup()
    except Exception as e:
        print(f"ZeroGPU startup: {e}")

    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)