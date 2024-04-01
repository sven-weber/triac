from pwd import getpwall, struct_passwd
from random import choice

from triac.types.base import BaseType, BaseValue
from triac.types.errors import UnsupportedTargetValueError
from triac.types.target import Target


class User:
    def __init__(self, data: struct_passwd) -> None:
        self.__name = data.pw_name
        self.__uid = data.pw_uid
        self.__gid = data.pw_gid
        self.__home = data.pw_dir
        self.__shell = data.pw_shell
        pass

    @property
    def name(self) -> str:
        return self.__name

    @property
    def uid(self) -> int:
        return self.__uid

    @property
    def gid(self) -> int:
        return self.__gid

    @property
    def home(self) -> str:
        return self.__home

    @property
    def shell(self) -> str:
        return self.__shell


class UserValue(BaseValue):
    def __init__(self, val: User) -> None:
        super().__init__(val)

    def transform(self, target: Target) -> str:
        if target == Target.ANSIBLE:
            return f"'{self.val.name}'"  # single quotes in ansible cannot be evaluated with variables
        elif target == Target.PYINFRA:
            return f'"{self.val.name}"'
        else:
            raise UnsupportedTargetValueError(target, self)


class UserType(BaseType):
    def __init__(self) -> None:
        super().__init__()

    def generate(self) -> UserValue:
        users = getpwall()
        user = choice(users)
        return UserValue(User(user))
