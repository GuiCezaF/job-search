import json
import logging
import os
import socket
from datetime import datetime
from typing import Any, Dict

from dotenv import load_dotenv

# Antes de qualquer `setup_logger`, para APP_ENV do .env valer nos imports.
load_dotenv()


def _is_production() -> bool:
    """Considera produção quando APP_ENV indica ambiente publicado (sem logs INFO)."""
    env = os.getenv("APP_ENV", "").strip().lower()
    return env in ("production", "prod", "prd")


class JsonFormatter(logging.Formatter):
    """
    JSON apenas para níveis ERROR+ (SIEM); use via SelectiveFormatter.

    Extras: `extra={"extra_fields": {...}}`.
    """

    def format(self, record: logging.LogRecord) -> str:
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
    """
    INFO/DEBUG/WARNING: linha legível para terminal.
    ERROR/CRITICAL: JSON estruturado.
    """

    def __init__(self) -> None:
        super().__init__()
        self._plain = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        self._json = JsonFormatter()

    def format(self, record: logging.LogRecord) -> str:
        if record.levelno >= logging.ERROR:
            return self._json.format(record)
        return self._plain.format(record)


class AppLogger:
    """Configura loggers com formato misto e política de nível conforme APP_ENV."""

    @staticmethod
    def setup_logger(name: str, level: int | None = None) -> logging.Logger:
        """
        Em desenvolvimento: nível padrão INFO (mensagens em texto).
        Em produção (APP_ENV=production|prod|prd): nível mínimo WARNING — sem logs INFO.
        Erros sempre serializados em JSON no handler.
        """
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
