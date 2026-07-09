import logging
import os
import sys


def get_logger(name: str = "my_crew") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(os.getenv("MY_CREW_LOG_LEVEL", "INFO").upper())
    logger.propagate = False
    return logger
