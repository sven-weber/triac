from enum import Enum
from os import listdir, walk
from os.path import islink, join, realpath
from random import choice, randint, randrange
from re import match
from string import ascii_letters, digits
from typing import Any, Dict, Optional, cast

from triac.lib.docker.const import TRIAC_WORKING_DIR
from triac.lib.random import BOOLEANS, Fuzzer, probability_bound
from triac.types.base import BaseType, BaseValue
from triac.types.errors import UnsupportedTargetValueError
from triac.types.target import Target


class FileType(Enum):
    FILE = "file"
    DIRECTORY = "directory"


DESCENT_FACTOR = 1.5
BACKTRACK_FACTOR = 2
IGNORE_PATHS = f"^/(tmp|proc|mnt|run|dev|lib\\w*|sys|{TRIAC_WORKING_DIR}|\\.socket$)"
IGNORE_PATHS_DELETE = (
    f"^/(etc$|etc/hostname$|sbin|usr/sbin|usr/app/triac|usr/lib.*|boot|bin|usr/bin|root/.ssh$)"
)


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
    def __init__(
        self,
        existing: bool,
        filetype: FileType,
        deletable: bool,
        empty: bool,
        cause: int,
    ):
        super().__init__(
            f"No path matching the required options: existing={existing}, filetype={filetype}, deletable={deletable}, empty={empty}, cause={cause}"
        )


def random_name(size: int, chars=ascii_letters + digits):
    return "".join(choice(chars) for _ in range(size))


def stochastic_walk(
    abs_root: str,
    root: str,
    deletable: bool,
    empty: bool,
    existing: bool,
    file_type: FileType,
    stop_chance: float,
) -> str:
    # empty ==> file_type == FileType.DIRECTORY
    assert not empty or file_type == FileType.DIRECTORY
    stop = randint(0, 100) / 100 < stop_chance
    parent = realpath(join(root, "..")) if root != abs_root else None

    try:
        _, dirs, files = next(walk(root))
    except:
        dirs = []
        files = []

    ddirs = [
        dir
        for (dir, abs) in map(lambda p: (p, join(root, p)), dirs)
        if not match(IGNORE_PATHS, abs)
    ]
    print(set(dirs) - set(ddirs))
    dirs = ddirs
    if stop:  # we're done searching, take something from the current directory
        if existing:
            if stop and empty and len(dirs) == 0 and len(files) == 0:
                return root

            if file_type == FileType.DIRECTORY:
                lst = [
                    dir
                    for (dir, abs) in map(lambda p: (p, join(root, p)), dirs)
                    # deletable ==> not match(..)
                    if (not deletable or not match(IGNORE_PATHS_DELETE, abs))
                    # empty ==> len(listdir(abs)) == 0
                    and (not empty or len(listdir(abs)) == 0)
                    # ignore links
                    and not islink(abs)
                ]
            elif file_type == FileType.FILE:
                lst = [
                    file
                    for (file, abs) in map(lambda p: (p, join(root, p)), files)
                    if not islink(abs)
                ]
            else:
                assert False

            if len(lst) == 0:  # backtracking
                if abs_root == root:
                    raise NoPathError(existing, file_type, deletable, empty, 1)
                else:
                    return stochastic_walk(
                        abs_root=abs_root,
                        root=cast(str, parent),
                        deletable=deletable,
                        empty=empty,
                        existing=existing,
                        file_type=file_type,
                        stop_chance=probability_bound(stop_chance * BACKTRACK_FACTOR),
                    )
            else:
                return join(root, choice(lst))
        else:  # file/folder should not exist, give a random name
            return join(root, random_name(randrange(5, 15, 1)))
    else:  # cd into another folder
        if len(dirs) == 0:  # backtracking
            if abs_root == root:
                raise NoPathError(existing, file_type, deletable, empty, 2)
            else:
                return stochastic_walk(
                    abs_root=abs_root,
                    root=cast(str, parent),
                    deletable=deletable,
                    empty=empty,
                    existing=existing,
                    file_type=file_type,
                    stop_chance=probability_bound(stop_chance * BACKTRACK_FACTOR),
                )
        else:
            dir = choice(dirs)
            return stochastic_walk(
                abs_root=abs_root,
                root=join(root, dir),
                deletable=deletable,
                empty=empty,
                existing=existing,
                file_type=file_type,
                stop_chance=probability_bound(stop_chance * DESCENT_FACTOR),
            )


class PathType(BaseType):
    def __init__(
        self,
        existing: Optional[bool] = None,
        filetype: Optional[FileType] = None,
        deletable: Optional[bool] = None,
        empty: Optional[bool] = None,
        root: str = "/",
    ) -> None:
        super().__init__()
        self.__root = root
        self._deletable = deletable if deletable is not None else False
        self._empty = empty if empty is not None else False
        self.opts = {
            "existing": BOOLEANS if existing is None else [existing],
            "filetype": (
                [FileType.FILE, FileType.DIRECTORY] if filetype is None else [filetype]
            ),
        }

    @property
    def root(self) -> str:
        return self.__root

    def generate(self) -> PathValue:
        opts = Fuzzer.fuzz_dict(self.opts)
        path = None
        for _ in range(0, 100):
            # try:
            path = stochastic_walk(
                root=self.root,
                abs_root=self.root,
                deletable=self._deletable,
                empty=self._empty,
                existing=opts["existing"],
                file_type=opts["filetype"],
                stop_chance=0.005,
            )
            break
        # except NoPathError:
        #     continue

        if path == None:
            raise NoPathError(
                opts["existing"], opts["filetype"], self._deletable, self._empty, 3
            )

        return PathValue(path)
