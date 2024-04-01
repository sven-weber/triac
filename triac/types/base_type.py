from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from triac.target import Target

T = TypeVar("T")


class BaseValue(ABC, Generic[T]):
    def __init__(self, val: T) -> None:
        self.val = val
        super().__init__()

    @abstractmethod
    def transform(self, target: Target) -> str:
        pass


class BaseType(ABC, Generic[T]):
    def __init__(self) -> None:
        super().__init__()

    @staticmethod
    @abstractmethod
    def generate() -> BaseValue[T]:
        pass
