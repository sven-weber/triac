from triac.types.base import BaseValue
from triac.types.target import Target
from triac.types.wrapper import State, Wrapper


class UnsupportedTargetValueError(Exception):
    def __init__(self, target: Target, value: BaseValue):
        super().__init__(
            f"Target '{target}' is not supported by value of type {type(value).__name__}"
        )


class UnsupportedTargetWrapperError(Exception):
    def __init__(self, target: Target, wrapper: str):
        super().__init__(f"Target '{target}' is not supported by wrapper {wrapper}")


class WrappersExhaustedError(Exception):
    def __init__(self):
        super().__init__(
            f"There are no more wrappers to be executed"
        )

class StateMismatchError(Exception):
    def __init__(self, target: State, actual: State):
        super().__init__(f"Found a state mismatch between target and actual state")
        self.__target = target
        self.__actual = actual

    @property
    def target(self):
        return self.__target

    @property
    def actual(self):
        return self.__actual
