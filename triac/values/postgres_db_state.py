from enum import Enum
from random import choice
from triac.types.base import BaseType, BaseValue
from triac.types.errors import UnsupportedTargetValueError
from triac.types.target import Target


class PostgresDbState(Enum):
    PRESENT = "present"
    ABSENT = "absent"


class PostgresDbStateValue(BaseValue):
    def __init__(self, val: PostgresDbState) -> None:
        super().__init__(val)

    def __repr__(self):
        return f"{self.val.value.__repr__()}"

    def transform(self, target: Target) -> str:
        if target == Target.ANSIBLE:
            return f"'{self.val.value}'"  # single quotes in ansible cannot be evaluated with variables
        elif target == Target.PYINFRA:
            return f'"{self.val.value}"'
        else:
            raise UnsupportedTargetValueError(target, self)


class PostgresDbStateType(BaseType):
    def __init__(self, can_delete: bool) -> None:
        super().__init__()
        self.can_delete = can_delete

    def generate(self) -> PostgresDbStateValue:
        return PostgresDbStateValue(
            choice([PostgresDbState.PRESENT, PostgresDbState.ABSENT] if self.can_delete else [PostgresDbState.PRESENT])
        )
