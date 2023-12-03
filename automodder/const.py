"""AutoModder constants."""

from pathlib import Path

CONFIG_PATH = Path("config.json")
DEFAULT_LOG_FORMAT = "{asctime} [{log_color}{levelname:^9}{reset}] [{cyan}{name}{reset}] [{blue}{funcName}{reset}] {message_log_color}{message}{reset}"
DATE_FORMAT = "%m/%d/%Y %I:%M:%S %p"
LOG_COLORS = {
    "DEBUG": "bold_cyan",
    "INFO": "bold_green",
    "WARNING": "bold_yellow",
    "ERROR": "bold_red",
    "CRITICAL": "bold_purple",
}
SECONDARY_LOG_COLORS = {
    "message": {
        **LOG_COLORS,
        "INFO": "light_white",
    }
}
COLORS = {"log_colors": LOG_COLORS, "secondary_log_colors": SECONDARY_LOG_COLORS}
