from random import choice
from typing import List
from triac.types.base import BaseType, BaseValue
from triac.types.errors import UnsupportedTargetValueError
from triac.types.target import Target
from triac.values.postgres_uri import DEFAULT_CHECK_URI


class PostgresDbNameValue(BaseValue):
    def __init__(self, val: str) -> None:
        super().__init__(val)

    def __repr__(self):
        return f"{self.val.__repr__()}"

    def transform(self, target: Target) -> str:
        if target == Target.ANSIBLE:
            return f"'{self.val}'"  # single quotes in ansible cannot be evaluated with variables
        elif target == Target.PYINFRA:
            return f'"{self.val}"'
        else:
            raise UnsupportedTargetValueError(target, self)


def find_databases() -> List[str]:
    pg = __import__("psycopg2")
    conn = pg.connect(DEFAULT_CHECK_URI)
    cur = conn.cursor()
    cur.execute("SELECT datname FROM pg_database")
    return list([row[0] for row in cur.fetchall()])


class PostgresDbNameType(BaseType):
    def __init__(self) -> None:
        super().__init__()

    def generate(self) -> PostgresDbNameValue:
        return PostgresDbNameValue(choice(find_databases()))
