from copy import deepcopy
from grp import getgrgid
from time import sleep
import importlib
from os import lstat, readlink
from os.path import isdir, islink
from pwd import getpwuid
from typing import List, cast

from triac.types.errors import UnsupportedTargetWrapperError
from triac.types.target import Target
from triac.types.wrapper import Definition, State, Wrapper
from triac.values.postgres_uri import PostgresURIType
from triac.values.postgres_db_state import PostgresDbStateType
from triac.values.postgres_db_name import PostgresDbNameType
from triac.values.postgres_uri import DEFAULT_CHECK_URI

ANSIBLE_TEMPLATE = """community.postgresql.postgresql_db:
  name: {name}
  {uri}
  state: {state}
"""


class PostgresDb(Wrapper):
    def __init__(self) -> None:
        super().__init__()

    @staticmethod
    def definition() -> Definition:
        return {
            "name": PostgresDbNameType(),
            "uri": PostgresURIType(),
            "state": PostgresDbStateType(),
        }

    @staticmethod
    def transform(target: Target, state: State) -> str:
        # Build the state dictionary
        s = {key: value.transform(target) for key, value in state.items()}
        if target == Target.ANSIBLE:
            return ANSIBLE_TEMPLATE.format(**s)
        else:
            raise UnsupportedTargetWrapperError(target, PostgresDB.__name__)

    @staticmethod
    def can_execute() -> bool:
        for i in range(10):
            try:
                sleep(0.1 * i**2)
                __import__("psycopg2").connect(DEFAULT_CHECK_URI)
                return True
            except:
                continue
        return False

    @staticmethod
    def supported_targets() -> List[Target]:
        return [Target.ANSIBLE]

    @staticmethod
    def enabled() -> bool:
        return True

    @staticmethod
    def verify(exp: State) -> State:
        state = {}

        return state
