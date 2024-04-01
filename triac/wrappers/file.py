from triac.types.errors import UnsupportedTargetWrapperError
from triac.types.target import Target
from triac.types.wrapper import Definition, State, Wrapper
from triac.values.bool import BoolType
from triac.values.group import GroupType
from triac.values.mode import ModeType
from triac.values.path import PathType
from triac.values.user import UserType

ANSIBLE_TEMPLATE = """
ansible.builtin.file:
  path: {path}
  owner: {owner}
  group: {group}
  mode: {mode}
"""

PYINFRA_TEMPLATE = """
files.file(,
    path={path},
    present={present},
    user={user},
    group={group},
    mode={mode},
    force={force},
)
"""


class File(Wrapper):
    def __init__(self) -> None:
        super().__init__()

    @staticmethod
    def definition() -> Definition:
        return {
            "path": PathType(),
            "present": BoolType(),
            "owner": UserType(),
            "group": GroupType(),
            "mode": ModeType(),
            "force": BoolType(),
        }

    @staticmethod
    def transform(target: Target, state: State) -> str:
        if target == Target.ANSIBLE:
            return ANSIBLE_TEMPLATE.format(**state)
        elif target == Target.PYINFRA:
            return PYINFRA_TEMPLATE.format(**state)
        else:
            raise UnsupportedTargetWrapperError(target, File.__name__)

    @staticmethod
    def verify() -> State:
        return {}
