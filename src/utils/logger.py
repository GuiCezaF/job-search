import logging
import os
from datetime import datetime

class AppLogger:
    @staticmethod
    def setup_logger(name: str):
        logger = logging.getLogger(name)
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            
            # Formato do log
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            
            # Console Handler
            ch = logging.StreamHandler()
            ch.setFormatter(formatter)
            logger.addHandler(ch)
            
            # File Handler (opcional, salva em logs/)
            if not os.path.exists("logs"):
                os.makedirs("logs")
            log_file = f"logs/app-{datetime.now().strftime('%Y-%m-%d')}.log"
            fh = logging.FileHandler(log_file, encoding='utf-8')
            fh.setFormatter(formatter)
            logger.addHandler(fh)
            
        return logger
