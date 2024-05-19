import json
import logging
import subprocess
from copy import deepcopy
from grp import getgrgid
from os import lstat, readlink
from os.path import isdir, islink
from pwd import getpwuid
from typing import List, cast

from triac.lib.service import ServiceStatus, ServiceStatusFetcher
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
        logger = logging.getLogger(__name__)
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
    def enabled() -> bool:
        return True

    @staticmethod
    def determine_enabled(reached_status: ServiceStatus) -> bool:
        return reached_status.enabled in ["enabled", "linked"]

    @staticmethod
    def determine_state(
        service: ServiceNameValue,
        target_state: ServiceStateValue,
        reached_status: ServiceStatus,
    ) -> ServiceState:
        if target_state.val == ServiceState.STARTED:
            # If the service should have been started
            if reached_status.active in ["active"]:
                # The service is still running -> it was started
                return ServiceState.STARTED
            elif service.status.active_entered_tst < reached_status.active_entered_tst:
                # The service might not be running anymore but it has run since the last check
                # -> It was started
                return ServiceState.STARTED
            elif service.status.condition_tst < (
                reached_status.condition_tst and reached_status.condition_res == False
            ):
                # We tried to start the service, but it is not running because a condition
                # failed. However, the condition timestamp was updated, meaning that
                # IaC successfully tried to start the service
                return ServiceState.STARTED
            elif (
                service.status.condition_res == False
                and reached_status.condition_res == False
            ):
                # There is the weird behavior that systemd reports that it checked a condition
                # But is does not update the timer. So in these cases where the condition
                # Was false before and it still is we just says the service was tried to be started
                # since we have no other way of determining if the service was started or not
                return ServiceState.STARTED
            # Otherwise, return stopped
            return ServiceState.STOPPED
        elif target_state.val == ServiceState.STOPPED:
            # If the service should be stopped
            if reached_status.active in ["inactive"]:
                # It has been stopped, great!
                return ServiceState.STOPPED

            # Otherwise return stopped
            return ServiceState.STARTED

        # Fallback TODO: implement
        return ServiceState.STARTED

    @staticmethod
    def is_enable_edge_case(service_name: str):
        """
        There is an edge case that was discovered before.
        See: https://github.com/ansible/ansible/issues/75464
        Basically, systemd reports a zero exit when trying
        to enable a service, although the service is in fact not
        enabled afterward.
        """
        # We check here if a service applies to this edge case
        # by trying to enable it (AFTER! the state has been read)
        # and checking of the corresponding error message is return
        # If this is the case, we will treat the service as enabled,
        # Although it is in fact not
        result = subprocess.run(
            ["systemctl", "enable", service_name], capture_output=True, text=True
        )
        if result.stderr.startswith("The unit files have no installation config"):
            return True
        else:
            return False

    @staticmethod
    def print_raw_status_info(state: ServiceStatus):
        print(f"raw active: {state.active}")
        print(f"raw enabled: {state.enabled}")
        print(f"active_entered_tst: {state.active_entered_tst}")
        print(f"condition_tst: {state.condition_tst}")
        print(f"condition_res: {state.condition_res}")
        print(f"enabled_preset: {state.enabled_preset}")

    @staticmethod
    def verify(exp: State) -> State:
        state = {}

        # Get targets
        service_name: ServiceNameValue = exp["name"]
        target_state: ServiceStateValue = exp["state"]

        # Fetch new service status
        reached_status = ServiceStatusFetcher.fetch(service_name.val)

        # Determine new properties
        enabled = Systemd.determine_enabled(reached_status)
        reached_state = Systemd.determine_state(
            service_name, target_state, reached_status
        )

        if (
            enabled == False
            and exp["enabled"].val == True
            and Systemd.is_enable_edge_case(service_name.val)
        ):
            # Consider the service enabled anyways
            # -> Edge case, see description in method
            print("Applied fix for edge case")
            enabled = True

        # Set the state properties
        state["name"] = service_name
        state["enabled"] = BoolValue(enabled)
        state["state"] = ServiceStateValue(reached_state)

        # Log the found state to the debug log
        print("Raw status information before changes:")
        Systemd.print_raw_status_info(service_name.status)
        print("Raw status information after changes:")
        Systemd.print_raw_status_info(reached_status)

        return state
