from logging import LogRecord
from typing import List

def build_log_filter(capture_libs: bool, allowed_modules: List[str]):

    def log_filter(record: LogRecord) -> bool:
        if capture_libs:
            return True
        else:
            # See if it is one of the explicitly allowed modules
            return record.name.split(".")[0] in allowed_modules

    return log_filter
