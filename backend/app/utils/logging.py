import logging
from logging.handlers import RotatingFileHandler

from app.config import GENERATED_DIR


def setup_logging() -> None:
    # Technical errors yahan log hote hain, user ko stack trace nahi dikhate
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    root = logging.getLogger()
    if root.handlers:  # reload par dobara add na ho
        return
    root.setLevel(logging.INFO)

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    # File log: max 1 MB x 2 files (disk kam use ho)
    file_handler = RotatingFileHandler(
        GENERATED_DIR / "app.log", maxBytes=1_000_000, backupCount=1, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)
