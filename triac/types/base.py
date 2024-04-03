from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from triac.types.target import Target

T = TypeVar("T")


class BaseValue(ABC, Generic[T]):
    def __init__(self, val: T) -> None:
        self.val = val
        super().__init__()

    def __repr__(self):
        return f"{self.val}"

    @abstractmethod
    def transform(self, target: Target) -> str:
        pass


class BaseType(ABC, Generic[T]):
    def __init__(self) -> None:
        super().__init__()

    @abstractmethod
    def generate(self) -> BaseValue[T]:
        pass
