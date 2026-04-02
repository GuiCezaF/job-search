import os
from datetime import datetime
from typing import Any, List, Mapping

import pandas as pd

from src.types.exceptions import ReportingError
from src.utils.logger import AppLogger

logger = AppLogger.setup_logger(__name__)


class FileManager:
    """
    Persiste resultados da busca em CSV sob um diretório configurável.
    """

    def __init__(self, output_dir: str = "output") -> None:
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)

    def save_to_csv(self, data: List[Mapping[str, Any]], prefix: str = "vagas") -> str:
        if not data:
            logger.warning("Nenhum dado para salvar.")
            return ""

        today = datetime.now().strftime("%Y-%m-%d")
        filename = f"{prefix}-{today}.csv"
        filepath = os.path.join(self.output_dir, filename)

        try:
            df = pd.DataFrame(data)
            df.to_csv(filepath, index=False, encoding="utf-8-sig")
        except OSError as err:
            logger.error(
                "Falha ao gravar CSV",
                extra={"extra_fields": {"function": "save_to_csv", "path": filepath, "error": str(err)}},
            )
            raise ReportingError(f"Não foi possível salvar o arquivo: {filepath}") from err

        logger.info(
            "Arquivo salvo com sucesso",
            extra={"extra_fields": {"path": filepath, "rows": len(data)}},
        )
        return filepath
