import logging

from apps.core.middleware.request_id import get_request_id


class RequestContextFilter(logging.Filter):
    """Inject request_id into log records."""

    def filter(self, record):
        record.request_id = get_request_id() or "-"
        return True


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not any(isinstance(f, RequestContextFilter) for f in logger.filters):
        logger.addFilter(RequestContextFilter())
    return logger


def log_exception(
    logger: logging.Logger, message: str, *, exc: Exception | None = None, **extra
) -> None:
    payload = {"event": message, **extra}
    if exc is not None:
        logger.exception(message, extra=payload, exc_info=exc)
    else:
        logger.error(message, extra=payload)
