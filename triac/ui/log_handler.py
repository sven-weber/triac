import logging
import logging.config
from logging import LogRecord

from rich.text import Text


class UILoggingHandler(logging.Handler):
    def __init__(self, console_out: Text, capture_libs: bool):
        logging.Handler.__init__(self)
        self.__console = console_out
        self.__capture_libs = capture_libs
        self.__allowed_modules = [__name__.split(".")[0], "__main__"]

        # Create a formatter
        self.formatter = logging.Formatter("%(message)s\n")

    def should_handle_record(self, record: LogRecord) -> bool:
        if self.__capture_libs:
            return True
        else:
            # See if it is one of the explicitly allowed modules
            return record.name.split(".")[0] in self.__allowed_modules

    def get_record_rich_format(self, record: LogRecord) -> str:
        if record.levelno >= 40:  # Error and above
            return "bold red"
        else:
            return ""

    def emit(self, record):
        if self.should_handle_record(record) == False:
            return

        # Format the log message and append it to the console
        log_message = self.format(record)
        self.__console.append(log_message, style=self.get_record_rich_format(record))
