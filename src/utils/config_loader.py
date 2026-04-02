import yaml
import os
from typing import Any, Dict, List
from dotenv import load_dotenv

class ConfigLoader:
    def __init__(self, config_path: str = "config.yaml"):
        # Carrega arquivo .env se existir
        load_dotenv()
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Arquivo de configuração não encontrado: {self.config_path}")
        
        with open(self.config_path, "r", encoding="utf-8") as file:
            config = yaml.safe_load(file)
        
        self._validate_config(config)
        return config

    def _validate_config(self, config: Dict[str, Any]) -> None:
        # Campos que podem estar no YAML OU no Ambiente (os.environ)
        secrets = {
            "LINKEDIN_USERNAME": ("linkedin", "username"),
            "LINKEDIN_PASSWORD": ("linkedin", "password"),
            "DISCORD_WEBHOOK_URL": ("discord", "webhook_url")
        }
        
        # Campos que OBRIGATORIAMENTE devem estar no YAML
        required_yaml = {
            "search": ["keywords", "experience_levels", "locations"]
        }
        
        # Validar obrigatórios do YAML
        for section, keys in required_yaml.items():
            if section not in config:
                raise ValueError(f"Sessão obrigatória '{section}' ausente no config.yaml")
            for key in keys:
                if key not in config[section]:
                    raise ValueError(f"Chave '{key}' ausente na sessão '{section}' do config.yaml")
        
        # Validar segredos (checa ambiente primeiro, depois YAML)
        for env_var, (section, key) in secrets.items():
            if not os.getenv(env_var):
                if section not in config or key not in config[section]:
                    raise ValueError(f"A configuração '{env_var}' (Ambiente) ou '{section}.{key}' (YAML) é obrigatória.")

    @property
    def linkedin_username(self) -> str:
        return os.getenv("LINKEDIN_USERNAME") or self.config.get("linkedin", {}).get("username")

    @property
    def linkedin_password(self) -> str:
        return os.getenv("LINKEDIN_PASSWORD") or self.config.get("linkedin", {}).get("password")

    @property
    def search_keywords(self) -> List[str]:
        return self.config["search"]["keywords"]

    @property
    def experience_levels(self) -> List[str]:
        return self.config["search"]["experience_levels"]

    @property
    def locations(self) -> List[str]:
        return self.config["search"]["locations"]

    @property
    def schedule(self) -> str:
        return self.config["search"].get("schedule", "0 9 * * *")

    @property
    def discord_webhook(self) -> str:
        return os.getenv("DISCORD_WEBHOOK_URL") or self.config.get("discord", {}).get("webhook_url")
