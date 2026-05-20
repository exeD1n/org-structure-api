from functools import lru_cache

from pydantic_settings import BaseSettings


class AppConfig(BaseSettings):
    db_url: str
    log_level: str = "INFO"


@lru_cache
def get_app_config() -> AppConfig:
    return AppConfig()


app_config = get_app_config()
