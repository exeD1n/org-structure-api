from functools import lru_cache

from pydantic_settings import BaseSettings


class AppConfig(BaseSettings):
    db_url: str = "sqlite+pysqlite:///:memory:"
    log_level: str = "INFO"


@lru_cache
def get_app_config() -> AppConfig:
    return AppConfig()


app_config = get_app_config()
