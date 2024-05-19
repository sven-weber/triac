from triac.types.base import BaseType, BaseValue
from triac.types.errors import UnsupportedTargetValueError
from triac.types.target import Target
from random import choice


class PostgresConnectionParameters:
    def __init__(self, host: str, user: str, password: str) -> None:
        self.host = host
        self.user = user
        self.password = password

    @property
    def uri(self) -> str:
        return f"host={self.host} user={self.user} password={self.password}"

    def __repr__(self):
        return f"[host] {self.host} [user] {self.user} [password] {self.password}"


class PostgresURIValue(BaseValue):
    def __init__(self, val: PostgresConnectionParameters) -> None:
        super().__init__(val)

    def __repr__(self):
        return f"{self.val.__repr__()}"

    def transform(self, target: Target) -> str:
        if target == Target.ANSIBLE:
            return f"""login_host: '{self.val.host}'
  login_user: '{self.val.user}'
  login_password: '{self.val.password}'"""
        else:
            raise UnsupportedTargetValueError(target, self)


# DEFAULT_CHECK_URI = "dbname=postgres user=postgres password=postgres host=::1"
DEFAULT_CHECK_URI = "host=localhost user=postgres password=postgres"

POSTGRES_PARAMS = [
    PostgresConnectionParameters("localhost", "postgres", "postgres"),
    PostgresConnectionParameters("127.0.0.1", "postgres", "postgres"),
    PostgresConnectionParameters("::1", "postgres", "postgres"),
]


class PostgresURIType(BaseType):
    def __init__(self) -> None:
        super().__init__()

    def generate(self) -> PostgresURIValue:
        return PostgresURIValue(choice(POSTGRES_PARAMS))
