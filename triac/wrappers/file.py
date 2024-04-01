from triac.values.path import PathType
from triac.types.wrapper import Wrapper, Definition, State


class File(Wrapper):
    def __init__(self) -> None:
        super().__init__()

    @staticmethod
    def definition() -> Definition:
        return {}

    @staticmethod
    def verify() -> State:
        return {}
