from enum import Enum
from os import walk
from os.path import join, realpath
from random import choice, randint
from re import match
from typing import Any, Dict, Optional, cast

from triac.lib.docker.const import TRIAC_WORKING_DIR
from triac.lib.random import BOOLEANS, Fuzzer, probability_bound
from triac.types.base import BaseType, BaseValue
from triac.types.errors import UnsupportedTargetValueError
from triac.types.target import Target


class FileType(Enum):
    FILE = "file"
    DIRECTORY = "directory"
    SYMLINK = "symlink"


DESCENT_FACTOR = 1.5
BACKTRACK_FACTOR = 2
IGNORE_PATHS = f"/(proc|mnt|run|dev|lib\\w*|sys|boot|srv|bin|usr/bin|usr|{TRIAC_WORKING_DIR}|\\w*sbin)"


class PathValue(BaseValue):
    def __init__(self, val: str) -> None:
        super().__init__(val)

    def transform(self, target: Target) -> str:
        if target == Target.ANSIBLE:
            return f"'{self.val}'"  # single quotes in ansible cannot be evaluated with variables
        elif target == Target.PYINFRA:
            return f'"{self.val}"'
        else:
            raise UnsupportedTargetValueError(target, self)

    def __repr__(self):
        return super().__repr__()


class NoPathError(Exception):
    def __init__(self, existing: bool, filetype: FileType):
        super().__init__(
            f"No path matching the required options: existing={existing}, filetype={filetype}"
        )


def stochastic_walk(
    abs_root: str, root: str, opts: Dict[str, Any], stop_chache: float
) -> str:
    existing = opts["existing"]
    file_type = opts["filetype"]
    stop = randint(0, 100) / 100 < stop_chache
    parent = realpath(join(root, "..")) if root != abs_root else None

    try:
        _, dirs, files = next(walk(root))
    except:
        dirs = []
        files = []

    dirs = list(
        [
            dir
            for dir in map(lambda p: join(root, p), dirs)
            if not match(IGNORE_PATHS, dir)
        ]
    )
    if stop:  # we're done searching, take something from the current directory
        if file_type == FileType.FILE:
            lst = files
        else:
            lst = dirs

        if len(lst) == 0 and root == "/":  # no options
            raise NoPathError(existing, file_type)
        elif len(lst) == 0:  # backtracking
            if abs_root == root:
                raise NoPathError(existing, file_type)
            else:
                return stochastic_walk(
                    abs_root,
                    cast(str, parent),
                    opts,
                    probability_bound(stop_chache * BACKTRACK_FACTOR),
                )
        else:
            return join(root, choice(lst))
    else:  # cd into another folder
        if len(dirs) == 0:  # backtracking
            if abs_root == root:
                raise NoPathError(existing, file_type)
            else:
                return stochastic_walk(
                    abs_root,
                    cast(str, parent),
                    opts,
                    probability_bound(stop_chache * BACKTRACK_FACTOR),
                )
        else:
            dir = choice(dirs)
            return stochastic_walk(
                abs_root,
                join(root, dir),
                opts,
                probability_bound(stop_chache * DESCENT_FACTOR),
            )


class PathType(BaseType):
    def __init__(
        self,
        existing: Optional[bool] = None,
        filetype: Optional[FileType] = None,
        root: str = "/",
    ) -> None:
        super().__init__()
        self.__root = root
        self.opts = {
            "existing": BOOLEANS if existing is None else [existing],
            "filetype": (
                [FileType.FILE, FileType.DIRECTORY, FileType.SYMLINK]
                if filetype is None
                else [filetype]
            ),
        }

    @property
    def root(self) -> str:
        return self.__root

    def generate(self) -> PathValue:
        opts = Fuzzer.fuzz_dict(self.opts)
        path = None
        for _ in range(0, 100):
            try:
                path = stochastic_walk(self.root, self.root, opts, 0.005)
            except NoPathError:
                continue
            break
        if path == None:
            raise NoPathError(opts["existing"], opts["filetype"])
        return PathValue(path)
