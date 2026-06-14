import structlog
from app.core.config import settings
import logging 
import sys

def configure_logging():
    processors = [
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level, 
        structlog.stdlib.add_logger_name,
        structlog.processors.format_exc_info, 
    ]

    logging.basicConfig(
        format="%(message)s", 
        stream=sys.stdout,
        level=logging.getLevelName(settings.LOG_LEVEL)
    )

    if settings.LOG_FORMAT == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True
    ) 
    
def get_logger(name: str):
    return structlog.get_logger(name)