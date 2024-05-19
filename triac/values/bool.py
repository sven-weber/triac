from random import choice

from triac.types.base import BaseType, BaseValue
from triac.types.errors import UnsupportedTargetValueError
from triac.types.target import Target


class BoolValue(BaseValue):
    def __init__(self, val: bool) -> None:
        super().__init__(val)

    def transform(self, target: Target) -> str:
        if target == Target.ANSIBLE:
            return "true" if self.val else "false"
        elif target == Target.PYINFRA:
            return "True" if self.val else "False"
        else:
            raise UnsupportedTargetValueError(target, self)

    def __repr__(self):
        return str(self.val)


class BoolType(BaseType):
    def __init__(self) -> None:
        super().__init__()

    def generate(self) -> BoolValue:
        return BoolValue(choice([True, False]))
