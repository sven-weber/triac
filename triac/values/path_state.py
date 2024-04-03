from enum import Enum
from random import choice
from typing import Any, Optional, cast

from triac.types.base import BaseType, BaseValue
from triac.types.errors import UnsupportedTargetValueError
from triac.types.target import Target
from triac.values.path import FileType, PathType, PathValue


class PathState(Enum):
    FILE = "file"
    DIRECTORY = "directory"
    SYMLINK = "symlink"
    ABSENT = "absent"

    def transform(self, target: Target) -> str:
        if target == Target.ANSIBLE:
            return f"'{self.value}'"
        elif target == Target.PYINFRA:
            return f'"{self.value}"'
        else:
            raise UnsupportedTargetValueError(target, cast(Any, self))


class PathStateValue(BaseValue):
    def __init__(self, val: PathValue, state: PathState) -> None:
        super().__init__(val)
        self.__state = state

    @property
    def state(self) -> PathState:
        return self.__state

    def __repr__(self):
        return f"[{self.__state.value}] {self.val.__repr__()}"

    def transform(self, target: Target) -> str:
        return self.val.transform(target)


class PathStateType(BaseType):
    def __init__(
        self,
        root: str = "/",
    ) -> None:
        super().__init__()
        self.__root = root

    @property
    def root(self) -> str:
        return self.__root

    @staticmethod
    def __map(typ: PathState) -> Optional[FileType]:
        if typ == PathState.FILE:
            return FileType.FILE
        elif typ == PathState.DIRECTORY:
            return FileType.DIRECTORY
        elif typ == PathState.SYMLINK:
            return FileType.SYMLINK
        else:
            return None

    def generate(self) -> PathStateValue:
        state = choice(
            [PathState.FILE, PathState.DIRECTORY, PathState.SYMLINK, PathState.ABSENT]
        )
        path = PathType(root=self.__root, filetype=self.__map(state))
        return PathStateValue(path.generate(), state)
