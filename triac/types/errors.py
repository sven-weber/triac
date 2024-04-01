from triac.types.base import BaseValue
from triac.types.target import Target
from triac.types.wrapper import Wrapper


class UnsupportedTargetValueError(Exception):
    def __init__(self, target: Target, value: BaseValue):
        super().__init__(
            f"Target '{target}' is not supported by value of type {type(value).__name__}"
        )


class UnsupportedTargetWrapperError(Exception):
    def __init__(self, target: Target, wrapper: str):
        super().__init__(f"Target '{target}' is not supported by wrapper {wrapper}")
