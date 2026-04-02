import os
from pathlib import Path
from typing import Any, Dict, Union

import yaml
from pydantic import ValidationError

from src.types.exceptions import ConfigError
from src.types.schemas import AppConfig
from src.utils.env_bootstrap import bootstrap_dotenv
from src.utils.logger import AppLogger

logger = AppLogger.setup_logger(__name__)


class ConfigLoader:
    """Load YAML, merge environment variables, and validate as ``AppConfig``."""

    def __init__(self, config_path: Union[str, Path] = "config.yaml") -> None:
        """``config_path``: path to the YAML file (default ``config.yaml``)."""
        bootstrap_dotenv()
        self.config_path = Path(config_path)
        self.config = self._load_and_validate()

    def _load_and_validate(self) -> AppConfig:
        """Read YAML from disk, inject env, and return a validated ``AppConfig``."""
        if not self.config_path.exists():
            raise ConfigError(f"Configuration file not found: {self.config_path}")

        try:
            with open(self.config_path, "r", encoding="utf-8") as file:
                yaml_data = yaml.safe_load(file) or {}
        except OSError as err:
            logger.error(
                "Failed to read configuration file",
                extra={"extra_fields": {"path": str(self.config_path), "error": str(err)}},
            )
            raise ConfigError(f"Could not read {self.config_path}") from err

        full_data = self._inject_env_vars(yaml_data)

        try:
            return AppConfig.model_validate(full_data)
        except ValidationError as err:
            logger.error(
                "Pydantic validation failed",
                extra={"extra_fields": {"errors": err.errors()}},
            )
            raise ConfigError("Invalid configuration; check config.yaml and environment variables.") from err

    def _inject_env_vars(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Overlay LINKEDIN_* and DISCORD_WEBHOOK_URL onto the parsed YAML dict."""
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
        """Validated application configuration."""
        return self.config

    @property
    def values(self) -> AppConfig:
        """Alias for ``app_config`` (legacy)."""
        return self.config
