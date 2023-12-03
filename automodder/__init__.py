"""AutoModder is a utility that provides tools for Reddit moderators."""
import logging

from .const import COLORS, CONFIG_PATH, DATE_FORMAT, DEFAULT_LOG_FORMAT
from .logger import Loggers, setup_logging
from .models import Config, InvokeContext

__version__ = "1.0.0"

config = Config.load(CONFIG_PATH)

loggers = Loggers()

loggers.add(__name__, logging.INFO)


def set_verbose():
    """Set verbose logging."""
    loggers.add(__name__, logging.DEBUG)
    loggers.add("praw", logging.DEBUG)
    loggers.add("prawcore", logging.DEBUG)
    setup_logging(loggers)


setup_logging(loggers)
