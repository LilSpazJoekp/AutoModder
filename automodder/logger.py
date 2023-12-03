"""Provide logging functionality."""
import logging
import sys
from collections.abc import Callable, Iterator
from typing import Generic, TypeVar

from colorlog import ColoredFormatter

from .const import COLORS, DATE_FORMAT, DEFAULT_LOG_FORMAT

T = TypeVar("T")


class Loggers:
    """Provide a manager for loggers."""

    def __init__(self):
        """Initialize the Loggers class."""
        self.loggers = {}

    def __iter__(self) -> Iterator[tuple[str, int | None]]:
        """Return an iterator for the loggers."""
        return iter(self.loggers.items())

    def __len__(self) -> int:
        """Return the number of loggers."""
        return len(self.loggers)

    def add(self, name: str, level: int | None = None):
        """Add a logger.

        :param name: The name of the logger.
        :param level: The logging level to use for the logger.

        """
        self.loggers[name] = level


def setup_logging(
    enable_loggers: Loggers | None = None, log_format: str = DEFAULT_LOG_FORMAT
):
    """Initialize logging.

    :param enable_loggers: A Loggers object containing the loggers to enable.
    :param log_format: The format to use for the loggers.

    """
    if not enable_loggers:
        enable_loggers = [(__name__.split(".")[0], logging.INFO)]
    formatter = ColoredFormatter(log_format, DATE_FORMAT, style="{", **COLORS)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    for logger_name, level in enable_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        if not logger.hasHandlers():
            logger.addHandler(handler)


class PrefixLogger(Generic[T]):
    """Logger that adds a prefix to all logged messages."""

    def __init__(
        self, logger: logging.Logger, log_prefix_func: Callable[[T], str]
    ) -> None:
        """Initialize the PrefixLogger.

        :param logger: The logger to use.
        :param log_prefix_func: A function that takes any number of args and returns a
            string to prefix to all logged messages.

        """
        self.logger = logger
        self._log_prefix_func = log_prefix_func

    def _generate_message(self, item: T, msg: str) -> str:
        message = f"{self._log_prefix_func(item)}" if item else ""
        if msg:
            if message:
                message += f": {msg}"
            else:
                message = msg
        return message

    def critical(self, msg: str, item: T | None) -> None:
        """Log a critical message.

        :param msg: The message to log.
        :param item: The item used to generate the prefix.

        """
        self.logger.critical(self._generate_message(item, msg))

    def debug(self, msg: str, item: T | None) -> None:
        """Log a debug message.

        :param msg: The message to log.
        :param item: The item used to generate the prefix.

        """
        self.logger.debug(self._generate_message(item, msg))

    def error(self, msg: str, item: T | None) -> None:
        """Log a error message.

        :param msg: The message to log.
        :param item: The item used to generate the prefix.

        """
        self.logger.error(self._generate_message(item, msg))

    def exception(self, msg: str, item: T | None) -> None:
        """Log a exception message.

        :param msg: The message to log.
        :param item: The item used to generate the prefix.

        """
        self.logger.exception(self._generate_message(item, msg))

    def info(self, msg: str, item: T | None) -> None:
        """Log a info message.

        :param msg: The message to log.
        :param item: The item used to generate the prefix.

        """
        self.logger.info(self._generate_message(item, msg))

    def warning(self, msg: str, item: T | None) -> None:
        """Log a warning message.

        :param msg: The message to log.
        :param item: The item used to generate the prefix.

        """
        self.logger.warning(self._generate_message(item, msg))
