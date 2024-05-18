from abc import ABC, abstractmethod
from typing import Dict, List

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
    def supported_targets() -> List[Target]:
        pass

    @staticmethod
    @abstractmethod
    def enabled() -> bool:
        pass

    @staticmethod
    @abstractmethod
    def verify(exp: State) -> State:
        pass

    @staticmethod
    def can_execute() -> bool:
        return True
