import logging

from app.core.app_config import app_config


def setup_logging() -> None:
    logging.basicConfig(
        level=app_config.log_level.upper(),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
