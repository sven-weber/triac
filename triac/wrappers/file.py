from grp import getgrgid
from os import lstat, readlink
from copy import deepcopy
from os.path import isdir, isfile, islink
from pwd import getpwuid
from typing import cast

from triac.types.errors import UnsupportedTargetWrapperError
from triac.types.target import Target
from triac.types.wrapper import Definition, State, Wrapper
from triac.values.bool import BoolType, BoolValue
from triac.values.group import Group, GroupType, GroupValue
from triac.values.mode import ModeType, ModeValue, parse_mode
from triac.values.path import PathValue
from triac.values.path_state import PathState, PathStateType, PathStateValue
from triac.values.user import User, UserType, UserValue

ANSIBLE_TEMPLATE_NORMAL = """ansible.builtin.file:
  path: {path}
  state: {state}
  owner: {owner}
  group: {group}
  mode: {mode}
"""

ANSIBLE_TEMPLATE_LINK = """ansible.builtin.file:
  dest: {path}
  src: {path}
  state: {state}
  owner: {owner}
  group: {group}
  mode: {mode}
"""

PYINFRA_TEMPLATE = """files.file(,
    path={path},
    present={present},
    user={user},
    group={group},
    mode={mode},
)
"""


class File(Wrapper):
    def __init__(self) -> None:
        super().__init__()

    @staticmethod
    def definition() -> Definition:
        return {
            "path": PathStateType(),
            "owner": UserType(),
            "group": GroupType(),
            "mode": ModeType(),
        }

    @staticmethod
    def transform(target: Target, state: State) -> str:
        s = {key: value.transform(target) for key, value in state.items()}
        ps = cast(PathStateValue, state["path"]).state
        s["state"] = ps.transform(target)

        if target == Target.ANSIBLE:
            if ps.value == PathState.SYMLINK:
                return ANSIBLE_TEMPLATE_LINK.format(**s)
            else:
                return ANSIBLE_TEMPLATE_NORMAL.format(**s)
        elif target == Target.PYINFRA:
            s["present"] = BoolValue(ps != PathState.ABSENT).transform(Target.PYINFRA)
            return PYINFRA_TEMPLATE.format(**s)
        else:
            raise UnsupportedTargetWrapperError(target, File.__name__)

    @staticmethod
    def verify(exp: State) -> State:
        path_val = cast(PathStateValue, exp["path"])
        path = path_val.val.val
        state = {}
        try:
            ps = PathState.FILE
            opt = None
            if isdir(path):
                ps = PathState.DIRECTORY
            elif islink(path):
                ps = PathState.SYMLINK
                opt = readlink(path)
            st = lstat(path)

            state["path"] = PathStateValue(PathValue(path), ps, opt)
            state["owner"] = UserValue(User(getpwuid(st.st_uid)))
            state["group"] = GroupValue(Group(getgrgid(st.st_gid)))
            state["mode"] = ModeValue(parse_mode(st.st_mode))
        except Exception as e:
            print(e)
            state = deepcopy(exp)
            state["path"] = PathStateValue(PathValue(path), PathState.ABSENT, None)

        return state
