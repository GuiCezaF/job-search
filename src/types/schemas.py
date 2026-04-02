from typing import List

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class LinkedInConfig(BaseModel):
    username: str = Field(min_length=1)
    password: SecretStr

    @field_validator("password")
    @classmethod
    def password_not_empty(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value():
            raise ValueError("password do LinkedIn é obrigatório")
        return value


class DiscordConfig(BaseModel):
    webhook_url: SecretStr

    @field_validator("webhook_url")
    @classmethod
    def webhook_not_empty(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("URL do webhook Discord é obrigatória")
        return value


class SearchConfig(BaseModel):
    keywords: List[str] = Field(min_length=1)
    experience_levels: List[str]
    locations: List[str]
    schedule: str = Field(default="0 9 * * *", min_length=1)
    # Máximo de vagas aceitas por combinação keyword+local (exclui promovidas/visualizadas)
    max_jobs_per_query: int = Field(default=32, ge=1, le=200)

class AppConfig(BaseModel):
    linkedin: LinkedInConfig
    discord: DiscordConfig
    search: SearchConfig

class JobResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str = Field(alias="Título")
    company: str = Field(alias="Empresa")
    location: str = Field(alias="Local")
    link: str = Field(alias="Link")
    search_date: str = Field(alias="Data de Busca")
    keyword: str = Field(alias="Keyword")
    experience_filter: str = Field(alias="Filtro Experiência")
