import json
import logging

from typing import Any


def _get_base_log_record_keys() -> set[str]:
    """Generates the log attributes to avoid displaying unwanted data."""

    record = logging.LogRecord(
        name="",
        level=logging.DEBUG,
        pathname="",
        lineno=0,
        msg="",
        args=(),
        exc_info=None,
    )

    keys = set(record.__dict__.keys())

    # These are updated during formatting.
    keys.update({"message", "asctime", "exc_text", "color_message"})

    return keys


RESERVED_ATTRIBUTES = _get_base_log_record_keys()


class TextFormatter(logging.Formatter):
    """Formatter for standard logs, appends the JSON fields when present."""

    def __init__(self):
        super().__init__(
            "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
        )

    def format(self, record: logging.LogRecord) -> str:
        processed_log = super().format(record)

        # Extract extra JSON fields & append for text logs.
        extra_data = {
            k: v for k, v in record.__dict__.items() if k not in RESERVED_ATTRIBUTES
        }

        if extra_data:
            json_str = json.dumps(extra_data)
            return f"{processed_log} | {json_str}"

        return processed_log


class JSONFormatter(logging.Formatter):
    """Formats the entire log record as JSON for key based sorting."""

    def format(self, record: logging.LogRecord) -> str:
        processed_log: dict[str, Any] = {
            "asctime": self.formatTime(record, self.datefmt),
            "levelname": record.levelname,
            "filename": f"{record.filename}:{record.lineno}",
            "message": record.getMessage(),
        }

        if record.exc_info:
            processed_log["exception"] = self.formatException(record.exc_info)

        # Extract extra JSON fields & update dictionary for json logs.
        extra_data = {
            k: v for k, v in record.__dict__.items() if k not in RESERVED_ATTRIBUTES
        }

        processed_log.update(extra_data)

        return json.dumps(processed_log)
