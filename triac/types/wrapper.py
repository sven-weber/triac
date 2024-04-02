from abc import ABC, abstractmethod
from typing import Dict

from triac.types.base import BaseType, BaseValue
from triac.types.target import Target

Definition = Dict[str, BaseType]
State = Dict[str, BaseValue]


class Wrapper(ABC):
    def __init__(self) -> None:
        super().__init__()

    @staticmethod
    @abstractmethod
    def definition() -> Definition:
        pass

    @staticmethod
    @abstractmethod
    def transform(target: Target, state: State) -> str:
        pass

    @staticmethod
    @abstractmethod
    def verify(state: State) -> State:
        pass
