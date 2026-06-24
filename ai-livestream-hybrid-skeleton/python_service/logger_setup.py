import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logger(level: str = "INFO") -> logging.Logger:
    os.makedirs("../logs", exist_ok=True)
    logger = logging.getLogger("ai_livestream")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    file_handler = RotatingFileHandler(
        "../logs/ai_livestream.log",
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger
