"""
Centralized logging configuration.
"""

import logging
import sys
from app.core.config import settings


def setup_logging() -> logging.Logger:
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Silence noisy third-party loggers
    for noisy in ("httpx", "httpcore", "neo4j"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    return logging.getLogger("offshoreiq")


logger = setup_logging()
