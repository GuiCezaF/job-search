from pydantic import BaseModel, ConfigDict, Field, SecretStr
from typing import List, Optional

class LinkedInConfig(BaseModel):
    username: str
    password: SecretStr

class DiscordConfig(BaseModel):
    webhook_url: SecretStr

class SearchConfig(BaseModel):
    keywords: List[str]
    experience_levels: List[str]
    locations: List[str]
    schedule: str = "0 9 * * *"

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
