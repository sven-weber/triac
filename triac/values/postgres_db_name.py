from random import choice, randrange
from typing import List
from string import ascii_letters, digits
from re import match
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

IGNORE_DBS="^template.*$|^postgres$"

def find_databases() -> List[str]:
    pg = __import__("psycopg2")
    cur = pg.connect(DEFAULT_CHECK_URI).cursor()
    cur.execute("SELECT datname FROM pg_database")
    raw = [row[0] for row in cur.fetchall()]
    dbs = [db for db in raw if not match(IGNORE_DBS, db)]
    return dbs

def random_name(size: int, chars=ascii_letters + digits):
    return "".join(choice(chars) for _ in range(size))

class PostgresDbNameType(BaseType):
    def __init__(self, existing: bool = True) -> None:
        super().__init__()
        self.existing = existing

    def generate(self) -> PostgresDbNameValue:
        dbs = find_databases()
        if not self.existing:
            l = randrange(5, 15, 1)
            dbs += [random_name(l) for _ in range(len(dbs)+1)]
        return PostgresDbNameValue(choice(dbs))
