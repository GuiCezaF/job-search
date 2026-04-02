from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_initialized: bool = False


def is_running_in_docker() -> bool:
    """Detect Docker via /.dockerenv or RUNNING_IN_DOCKER."""
    if Path("/.dockerenv").exists():
        return True
    flag = os.getenv("RUNNING_IN_DOCKER", "").strip().lower()
    return flag in ("1", "true", "yes")


def bootstrap_dotenv() -> None:
    """Load the appropriate dotenv file once (Docker: .env.production; local: .env.dev or .env)."""
    global _initialized
    if _initialized:
        return
    _initialized = True

    explicit = os.getenv("DOTENV_FILE", "").strip()
    if explicit:
        path = Path(explicit)
        if path.is_file():
            load_dotenv(path, override=False)
        return

    if is_running_in_docker():
        prod = Path(".env.production")
        if prod.is_file():
            load_dotenv(prod, override=False)
        return

    dev = Path(".env.dev")
    if dev.is_file():
        load_dotenv(dev, override=False)
        return

    legacy = Path(".env")
    if legacy.is_file():
        load_dotenv(legacy, override=False)
