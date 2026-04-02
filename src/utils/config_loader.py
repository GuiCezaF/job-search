import yaml
import os
from pathlib import Path
from typing import Any, Dict
from dotenv import load_dotenv
from src.types.schemas import AppConfig
from src.types.exceptions import ConfigError
from src.utils.logger import AppLogger

logger = AppLogger.setup_logger(__name__)

class ConfigLoader:
    """
    Loads and validates application configuration using Pydantic.
    """
    def __init__(self, config_path: str = "config.yaml"):
        load_dotenv()
        self.config_path = Path(config_path)
        self.config = self._load_and_validate()

    def _load_and_validate(self) -> AppConfig:
        """
        Loads YAML and merges with Environment Variables into an AppConfig model.
        """
        if not self.config_path.exists():
            raise ConfigError(f"Arquivo de configuração não encontrado: {self.config_path}")
        
        try:
            with open(self.config_path, "r", encoding="utf-8") as file:
                yaml_data = yaml.safe_load(file) or {}
                
            # Merge Environment Variables into the data structure
            # to be validated by Pydantic
            full_data = self._inject_env_vars(yaml_data)
            
            return AppConfig(**full_data)
        except Exception as e:
            logger.error(f"Erro na validação da configuração: {e}")
            raise ConfigError(f"Falha ao carregar configurações: {e}")

    def _inject_env_vars(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensures essential secrets are present, prioritizing Env Vars.
        """
        # LinkedIn
        if "linkedin" not in data: data["linkedin"] = {}
        data["linkedin"]["username"] = os.getenv("LINKEDIN_USERNAME") or data["linkedin"].get("username")
        data["linkedin"]["password"] = os.getenv("LINKEDIN_PASSWORD") or data["linkedin"].get("password")
        
        # Discord
        if "discord" not in data: data["discord"] = {}
        data["discord"]["webhook_url"] = os.getenv("DISCORD_WEBHOOK_URL") or data["discord"].get("webhook_url")
        
        return data

    @property
    def values(self) -> AppConfig:
        return self.config
