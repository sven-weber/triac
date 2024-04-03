import logging
import logging.config
from logging import LogRecord

from rich.pretty import Pretty
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

    def emit(self, record):
        if self.should_handle_record(record) == False:
            return

        formatted = self.format(record)

        # Append the record
        if record.levelno >= 40:
            # Error and above
            self.__console.append(formatted, style="bold red")
        else:
            self.__console.append(formatted)
