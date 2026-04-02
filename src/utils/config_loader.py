import os
from pathlib import Path
from typing import Any, Dict, Union

import yaml
from dotenv import load_dotenv
from pydantic import ValidationError

from src.types.exceptions import ConfigError
from src.types.schemas import AppConfig
from src.utils.logger import AppLogger

logger = AppLogger.setup_logger(__name__)


class ConfigLoader:
    """
    Carrega YAML, mescla variáveis de ambiente e valida com Pydantic v2.
    """

    def __init__(self, config_path: Union[str, Path] = "config.yaml") -> None:
        load_dotenv()
        self.config_path = Path(config_path)
        self.config = self._load_and_validate()

    def _load_and_validate(self) -> AppConfig:
        if not self.config_path.exists():
            raise ConfigError(f"Arquivo de configuração não encontrado: {self.config_path}")

        try:
            with open(self.config_path, "r", encoding="utf-8") as file:
                yaml_data = yaml.safe_load(file) or {}
        except OSError as err:
            logger.error(
                "Falha ao ler arquivo de configuração",
                extra={"extra_fields": {"path": str(self.config_path), "error": str(err)}},
            )
            raise ConfigError(f"Não foi possível ler {self.config_path}") from err

        full_data = self._inject_env_vars(yaml_data)

        try:
            return AppConfig.model_validate(full_data)
        except ValidationError as err:
            logger.error(
                "Validação Pydantic falhou",
                extra={"extra_fields": {"errors": err.errors()}},
            )
            raise ConfigError("Configuração inválida; confira config.yaml e variáveis de ambiente.") from err

    def _inject_env_vars(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prioriza secrets vindos do ambiente sobre o YAML."""
        if "linkedin" not in data:
            data["linkedin"] = {}
        data["linkedin"]["username"] = os.getenv("LINKEDIN_USERNAME") or data["linkedin"].get("username")
        data["linkedin"]["password"] = os.getenv("LINKEDIN_PASSWORD") or data["linkedin"].get("password")

        if "discord" not in data:
            data["discord"] = {}
        data["discord"]["webhook_url"] = os.getenv("DISCORD_WEBHOOK_URL") or data["discord"].get("webhook_url")

        return data

    @property
    def app_config(self) -> AppConfig:
        return self.config

    @property
    def values(self) -> AppConfig:
        """Alias legado; preferir app_config."""
        return self.config
