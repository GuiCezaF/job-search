from typing import List

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class LinkedInConfig(BaseModel):
    """LinkedIn credentials for scraping."""

    username: str = Field(min_length=1)
    password: SecretStr

    @field_validator("password")
    @classmethod
    def password_not_empty(cls, value: SecretStr) -> SecretStr:
        """Reject empty LinkedIn passwords."""
        if not value.get_secret_value():
            raise ValueError("LinkedIn password is required")
        return value


class DiscordConfig(BaseModel):
    """Discord incoming webhook (secret)."""

    webhook_url: SecretStr

    @field_validator("webhook_url")
    @classmethod
    def webhook_not_empty(cls, value: SecretStr) -> SecretStr:
        """Reject blank Discord webhook URLs."""
        if not value.get_secret_value().strip():
            raise ValueError("Discord webhook URL is required")
        return value


class SearchConfig(BaseModel):
    """Search terms, filters, schedule, and per-query job cap."""

    keywords: List[str] = Field(min_length=1)
    experience_levels: List[str]
    locations: List[str]
    schedule: str = Field(default="0 9 * * *", min_length=1)
    max_jobs_per_query: int = Field(default=32, ge=1, le=200)


class AppConfig(BaseModel):
    """Root configuration model validated from YAML plus environment."""

    linkedin: LinkedInConfig
    discord: DiscordConfig
    search: SearchConfig


class JobResult(BaseModel):
    """One scraped job row (aliases match Portuguese CSV headers)."""

    model_config = ConfigDict(populate_by_name=True)

    title: str = Field(alias="Título")
    company: str = Field(alias="Empresa")
    location: str = Field(alias="Local")
    link: str = Field(alias="Link")
    search_date: str = Field(alias="Data de Busca")
    keyword: str = Field(alias="Keyword")
    experience_filter: str = Field(alias="Filtro Experiência")
