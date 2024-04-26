import stat
from enum import Enum
from random import choice

from triac.types.base import BaseType, BaseValue
from triac.types.errors import UnsupportedTargetValueError
from triac.types.target import Target


class Permission(Enum):
    NONE = 0
    R = 4
    W = 2
    RW = 6
    X = 1
    XR = 5
    XW = 3
    XWR = 7

    def __str__(self) -> str:
        match self:
            case Permission.NONE:
                return "---"
            case Permission.R:
                return "r--"
            case Permission.W:
                return "-w-"
            case Permission.RW:
                return "rw-"
            case Permission.X:
                return "--x"
            case Permission.XR:
                return "r-x"
            case Permission.XW:
                return "-wx"
            case Permission.XWR:
                return "rwx"


class Mode:
    def __init__(self, user: Permission, group: Permission, others: Permission) -> None:
        self.__user = user
        self.__group = group
        self.__others = others

    @property
    def user(self) -> Permission:
        return self.__user

    @property
    def group(self) -> Permission:
        return self.__group

    @property
    def others(self) -> Permission:
        return self.__others

    def __repr__(self):
        return f"u: {str(self.__user)} g: {str(self.__group)} o: {str(self.__others)}"


def parse_mode(mode: int) -> Mode:
    u = 0
    u += 4 if bool(mode & stat.S_IRUSR) else 0
    u += 2 if bool(mode & stat.S_IWUSR) else 0
    u += 1 if bool(mode & stat.S_IXUSR) else 0

    g = 0
    g += 4 if bool(mode & stat.S_IRGRP) else 0
    g += 2 if bool(mode & stat.S_IWGRP) else 0
    g += 1 if bool(mode & stat.S_IXGRP) else 0

    o = 0
    o += 4 if bool(mode & stat.S_IROTH) else 0
    o += 2 if bool(mode & stat.S_IWOTH) else 0
    o += 1 if bool(mode & stat.S_IXOTH) else 0

    return Mode(Permission(u), Permission(g), Permission(o))


class ModeValue(BaseValue):
    def __init__(self, val: Mode) -> None:
        super().__init__(val)

    def transform(self, target: Target) -> str:
        if target == Target.ANSIBLE:
            return f"'0{self.val.user.value}{self.val.group.value}{self.val.others.value}'"  # single quotes in ansible cannot be evaluated with variables
        elif target == Target.PYINFRA:
            return (
                f'"{self.val.user.value}{self.val.group.value}{self.val.others.value}"'
            )
        else:
            raise UnsupportedTargetValueError(target, self)


class ModeType(BaseType):
    def __init__(self) -> None:
        super().__init__()

    def generate(self) -> ModeValue:
        modes = []
        for u in Permission:
            for g in Permission:
                for o in Permission:
                    modes.append(Mode(u, g, o))

        return ModeValue(choice(modes))
