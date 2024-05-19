from logging import Logger
from triac.types.base import BaseType, BaseValue
from triac.types.errors import UnsupportedTargetValueError
from triac.types.target import Target
from triac.values.postgres_db_state import PostgresDbState, PostgresDbStateValue, PostgresDbStateType
from triac.values.postgres_db_name import PostgresDbNameValue, PostgresDbNameType, find_databases

class PostgresDbValue(BaseValue):
    def __init__(self, state: PostgresDbStateValue, db: PostgresDbNameValue) -> None:
        super().__init__(db)
        self.state = state

    def __repr__(self):
        return f"[state] {self.state} [db] {self.val.__repr__()}"

    def transform(self, target: Target) -> str:
        if target == Target.ANSIBLE:
            return f"""name: {self.val.transform(target)}
  state: {self.state.transform(target)}"""
        else:
            raise UnsupportedTargetValueError(target, self)


class PostgresDbType(BaseType):
    def __init__(self) -> None:
        super().__init__()

    def generate(self) -> PostgresDbValue:
        can_delete = len(find_databases()) > 0
        state = PostgresDbStateType(can_delete=can_delete).generate()
        name = PostgresDbNameType(existing=state.val != PostgresDbState.PRESENT).generate()
        return PostgresDbValue(state, name)
