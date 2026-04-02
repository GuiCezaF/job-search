import json
import logging
import os
import socket
from datetime import datetime
from typing import Any, Dict

from src.utils.env_bootstrap import bootstrap_dotenv

bootstrap_dotenv()


def _is_production() -> bool:
    """Return True when APP_ENV indicates a production deployment."""
    env = os.getenv("APP_ENV", "").strip().lower()
    return env in ("production", "prod", "prd")


class JsonFormatter(logging.Formatter):
    """Serialize log records as JSON for ERROR-level and above (via SelectiveFormatter)."""

    def format(self, record: logging.LogRecord) -> str:
        """Build a JSON line; merges ``record.extra_fields`` when present."""
        log_records: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "module": record.module,
            "function": record.funcName,
            "message": record.getMessage(),
            "hostname": socket.gethostname(),
        }

        if hasattr(record, "extra_fields"):
            log_records.update(record.extra_fields)

        if record.exc_info:
            log_records["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_records, ensure_ascii=False)


class SelectiveFormatter(logging.Formatter):
    """Plain text below ERROR; JSON at ERROR and CRITICAL."""

    def __init__(self) -> None:
        super().__init__()
        self._plain = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        self._json = JsonFormatter()

    def format(self, record: logging.LogRecord) -> str:
        """Delegate to JSON formatter for errors; otherwise use the plain template."""
        if record.levelno >= logging.ERROR:
            return self._json.format(record)
        return self._plain.format(record)


class AppLogger:
    """Factory for named loggers with selective formatting and production log levels."""

    @staticmethod
    def setup_logger(name: str, level: int | None = None) -> logging.Logger:
        """Configure and return a logger; production mode clamps to WARNING minimum."""
        logger = logging.getLogger(name)

        if level is None:
            base_level = logging.WARNING if _is_production() else logging.INFO
        else:
            base_level = level

        if _is_production():
            effective_level = max(base_level, logging.WARNING)
        else:
            effective_level = base_level

        if not logger.handlers:
            logger.setLevel(effective_level)
            handler = logging.StreamHandler()
            handler.setLevel(logging.DEBUG)
            handler.setFormatter(SelectiveFormatter())
            logger.addHandler(handler)
            logger.propagate = False
        else:
            logger.setLevel(effective_level)

        return logger
