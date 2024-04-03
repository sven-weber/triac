from grp import getgrall, struct_group
from random import choice

from triac.types.base import BaseType, BaseValue
from triac.types.errors import UnsupportedTargetValueError
from triac.types.target import Target


class Group:
    def __init__(self, data: struct_group) -> None:
        self.__name = data.gr_name
        self.__gid = data.gr_gid
        pass

    @property
    def name(self) -> str:
        return self.__name

    @property
    def gid(self) -> int:
        return self.__gid

    def __repr__(self):
        return f"[name]: {self.__name}, [id]: {self.__gid}"


class GroupValue(BaseValue):
    def __init__(self, val: Group) -> None:
        super().__init__(val)

    def transform(self, target: Target) -> str:
        if target == Target.ANSIBLE:
            return f"'{self.val.name}'"  # single quotes in ansible cannot be evaluated with variables
        elif target == Target.PYINFRA:
            return f'"{self.val.name}"'
        else:
            raise UnsupportedTargetValueError(target, self)


class GroupType(BaseType):
    def __init__(self) -> None:
        super().__init__()

    def generate(self) -> GroupValue:
        groups = getgrall()
        group = choice(groups)
        return GroupValue(Group(group))
