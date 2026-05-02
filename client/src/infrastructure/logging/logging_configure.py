import logging
import sys

from datetime import datetime
from pathlib import Path

from src.domain.exceptions.operation_exceptions import ConfigurationError
from src.infrastructure.logging.logging_formatter import TextFormatter, JSONFormatter


def configure_logging(
    level: int = logging.INFO,
    save: bool = False,
    json: bool = False,
    directory: str | Path | None = None,
):
    """
    Configures the root logger.

    Args:
        level (int): Logging level as defined by the logging library.
        json (bool): If True outputs JSON formatted logs, else, uses JSON appended text.
        save (bool): If True saves the logs into the default or specified folder.
        directory (str | None): Directory where logs are saved, defaulted if unknown.
    """

    try:
        root_logger = logging.getLogger()
        root_logger.setLevel(level)

        if root_logger.hasHandlers():
            root_logger.handlers.clear()

        formatter = JSONFormatter() if json else TextFormatter()

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)

        root_logger.addHandler(console_handler)

        if save:
            if directory:
                log_path = Path(directory)

            else:
                log_path = Path(__file__).parent.parent.parent.parent / "logs"

            log_path.mkdir(parents=True, exist_ok=True)

            current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            log_filename = f"log_{current_time}.log"

            file_path = log_path / log_filename
            file_handler = logging.FileHandler(file_path, encoding="utf-8")
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

    except Exception as e:
        raise ConfigurationError("Error during logging configuration") from e
