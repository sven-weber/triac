import logging
import logging.config
from logging import LogRecord

from rich.pretty import Pretty
from rich.text import Text


class UILoggingHandler(logging.Handler):
    def __init__(self, console_out: Text):
        logging.Handler.__init__(self)
        self.__console = console_out

        # Create a formatter
        self.formatter = logging.Formatter("%(message)s\n")

    def emit(self, record):
        formatted = self.format(record)

        # Append the record
        if record.levelno >= 40:
            # Error and above
            self.__console.append(formatted, style="bold red")
        else:
            self.__console.append(formatted)
