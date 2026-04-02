import pandas as pd
import os
from datetime import datetime
from src.utils.logger import AppLogger

logger = AppLogger.setup_logger(__name__)

class FileManager:
    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def save_to_csv(self, data: list, prefix: str = "vagas") -> str:
        if not data:
            logger.warning("Nenhum dado para salvar.")
            return ""

        today = datetime.now().strftime("%Y-%m-%d")
        filename = f"{prefix}-{today}.csv"
        filepath = os.path.join(self.output_dir, filename)

        df = pd.DataFrame(data)
        
        # Sobrescreve o arquivo se ele já existia no mesmo dia
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        logger.info(f"Arquivo salvo com sucesso em: {filepath} (Total: {len(data)} vagas)")
        
        return filepath
