from enum import Enum
from random import choice

from triac.types.base import BaseType, BaseValue
from triac.types.errors import UnsupportedTargetValueError
from triac.types.target import Target


class Permission(Enum):
    NONE = 0
    R = 1
    W = 2
    RW = 3
    X = 4
    XR = 5
    XW = 6
    XWR = 7


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
