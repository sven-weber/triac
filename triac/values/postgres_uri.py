from triac.types.base import BaseType, BaseValue
from triac.types.errors import UnsupportedTargetValueError
from triac.types.target import Target


class PostgresURIValue(BaseValue):
    def __init__(self, val: str) -> None:
        super().__init__(val)

    def __repr__(self):
        return f"{self.val.__repr__()}"

    def transform(self, target: Target) -> str:
        if target == Target.ANSIBLE:
            return f"'{self.val.name}'"  # single quotes in ansible cannot be evaluated with variables
        elif target == Target.PYINFRA:
            return f'"{self.val.name}"'
        else:
            raise UnsupportedTargetValueError(target, self)


POSTGRES_URIS = ["psql://root:root@localhost" "psql://localhost"]


class PostgresURIType(BaseType):
    def __init__(self) -> None:
        super().__init__()

    def generate(self) -> PostgresURIValue:
        return UserValue(User(user))
