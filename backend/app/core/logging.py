import logging
import sys
from app.core.security import redact_secrets

class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        orig = super().format(record)
        return redact_secrets(orig)

def setup_logger(name: str = "truth_inspector") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        formatter = RedactingFormatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

logger = setup_logger()
