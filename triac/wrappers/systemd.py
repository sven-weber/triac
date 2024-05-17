from copy import deepcopy
from grp import getgrgid
import importlib
from os import lstat, readlink
from os.path import isdir, islink
from pwd import getpwuid
from typing import List, cast

from triac.types.errors import UnsupportedTargetWrapperError
from triac.types.target import Target
from triac.types.wrapper import Definition, State, Wrapper
from triac.values.bool import BoolType, BoolValue
from triac.values.group import Group, GroupType, GroupValue
from triac.values.mode import ModeType, ModeValue, parse_mode
from triac.values.path import PathValue
from triac.values.path_state import PathState, PathStateType, PathStateValue
from triac.values.service_name import ServiceNameType, ServiceNameValue
from triac.values.service_state import ServiceState, ServiceStateType, ServiceStateValue
from triac.values.user import User, UserType, UserValue

ANSIBLE_TEMPLATE = """ansible.builtin.systemd_service:
  name: {name}
  enabled: {enabled}
  state: {state}
"""

PYINFRA_TEMPLATE = """systemd.service(,
    {name},
    enabled={enabled},
    {state}
)
"""

class Systemd(Wrapper):
    def __init__(self) -> None:
        super().__init__()

    @staticmethod
    def definition() -> Definition:
        return {
            "name": ServiceNameType(),
            "enabled": BoolType(),
            "state": ServiceStateType(),
        }

    @staticmethod
    def transform(target: Target, state: State) -> str:
        # Build the state dictionary
        s = {key: value.transform(target) for key, value in state.items()}
        if target == Target.ANSIBLE:
            return ANSIBLE_TEMPLATE.format(**s)
        elif target == Target.PYINFRA:
            return PYINFRA_TEMPLATE.format(**s)
        else:
            raise UnsupportedTargetWrapperError(target, Systemd.__name__)

    def supported_targets() -> List[Target]:
        return [Target.ANSIBLE, Target.PYINFRA]

    @staticmethod
    def verify(exp: State) -> State:
        state = {}
        try:
            # Dynamically load pystemd
            systemd = importlib.import_module("pystemd.systemd1")
            service = systemd.Unit(exp["name"].val, _autoload=True)

            # Enabled
            enabled_value = service.Unit.UnitFileState.decode("utf-8")
            is_enabled = enabled_value in ["enabled", "linked"] #"static"

            # Active state
            # Possible values: "active", "reloading", "inactive", "failed",
            # "activating", and "deactivating"
            active_value = service.Unit.ActiveState.decode("utf-8")
            match ServiceState[exp["state"].val.name]:
                case ServiceState.STARTED:
                    if active_value in ["active"]:
                        state_value = ServiceState.STARTED
                    else:
                        state_value = ServiceState.STOPPED
                case ServiceState.STOPPED:
                    if active_value in ["inactive"]:
                        state_value = ServiceState.STOPPED
                    else:
                        state_value = ServiceState.STARTED

            # Set the status
            state["name"] = ServiceNameValue(exp["name"].val)
            state["enabled"] = BoolValue(is_enabled)
            state["state"] = ServiceStateValue(state_value)
            #state["raw_state"] = active_value
            #state["raw_enabled"] = enabled_value
        except Exception as e:
            print(e)
            state["name"] = e
        
        return state


        
