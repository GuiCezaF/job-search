import logging
import json
import socket
from datetime import datetime
from typing import Any, Dict

class JsonFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_records: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "module": record.module,
            "function": record.funcName,
            "message": record.getMessage(),
            "hostname": socket.gethostname()
        }
        
        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_records.update(record.extra_fields)
            
        if record.exc_info:
            log_records["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_records)

class AppLogger:
    @staticmethod
    def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
        """
        Configures and returns a logger with JSON formatting.
        """
        logger = logging.getLogger(name)
        
        # Prevent duplicate handlers if setup multiple times
        if not logger.handlers:
            logger.setLevel(level)
            
            # Console Handler
            handler = logging.StreamHandler()
            formatter = JsonFormatter()
            handler.setFormatter(formatter)
            
            logger.addHandler(handler)
            logger.propagate = False
            
        return logger
