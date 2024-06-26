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
    SYMLINK = "link"
    ABSENT = "absent"

    def transform(self, target: Target) -> str:
        if target == Target.ANSIBLE:
            return f"'{self.value}'"
        elif target == Target.PYINFRA:
            return f'"{self.value}"'
        else:
            raise UnsupportedTargetValueError(target, cast(Any, self))


class PathStateValue(BaseValue):
    def __init__(self, val: PathValue, state: PathState, opt: PathValue | None) -> None:
        super().__init__(val)
        self.__state = state
        self.__opt = opt

    @property
    def state(self) -> PathState:
        return self.__state

    @property
    def opt(self) -> PathValue | None:
        return self.__opt

    def __repr__(self):
        if self.__state == PathState.SYMLINK:
            return f"[{self.__state.value}] [dst] {self.val.__repr__()} [src] {self.opt.__repr__()}"
        else:
            return f"[{self.__state.value}] {self.val.__repr__()}"

    def transform(self, target: Target) -> str:
        return self.val.transform(target)

    def transform_opt(self, target: Target) -> str:
        assert self.opt is not None
        return self.opt.transform(target)


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
        if typ.value == PathState.FILE:
            return FileType.FILE
        elif typ.value == PathState.DIRECTORY:
            return FileType.DIRECTORY
        else:
            return None

    def generate(self) -> PathStateValue:
        state = choice(
            [PathState.FILE, PathState.DIRECTORY, PathState.SYMLINK, PathState.ABSENT]
        )
        opt: Optional[PathValue] = None

        if state == PathState.SYMLINK:
            ft = choice([FileType.FILE, FileType.DIRECTORY])
            # dest
            path_type = PathType(
                root=self.__root, filetype=ft, empty=ft == FileType.DIRECTORY
            )
            # src
            opt_type = PathType(root=self.__root, filetype=ft, existing=True)

            path = path_type.generate()
            while opt is None or opt.val == path.val:
                opt = opt_type.generate()
        else:
            path_type = PathType(
                root=self.__root,
                filetype=(
                    FileType.FILE
                    if state == PathState.FILE
                    else FileType.DIRECTORY if state == PathState.DIRECTORY else None
                ),
                deletable=state == PathState.ABSENT,
            )
            path = path_type.generate()

        return PathStateValue(path, state, opt)
