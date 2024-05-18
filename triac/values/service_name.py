import importlib
from posixpath import basename
from random import choice
from typing import List
from triac.lib.service import ServiceStatus, ServiceStatusFetcher
from triac.types.base import BaseType, BaseValue
from triac.types.errors import UnsupportedTargetValueError
from triac.types.target import Target

# Services to ignore.
# SSH -> Would crash our fuzzing
# systemd-networkd-wait-online -> Waits potentially forever
ignore_list = ["ssh.service", "sshd.service", "systemd-networkd-wait-online.service"]

# Possible values: "enabled", "enabled-runtime", "linked", "linked-runtime", "masked", "masked-runtime", "static",
# "disabled", and "invalid"
# -> We ignore masked and static services since there is nothing sensible that
# can be done with those services
valid_status = ["enabled", "enabled-runtime", "linked", "linked-runtime", "disabled"]

class ServiceNameValue(BaseValue[str]):
    def __init__(self, val: str, status: ServiceStatus = None) -> None:
        super().__init__(val)
        self.__status = status

    @property
    def status(self) -> ServiceStatus:
        return self.__status
    
    def transform(self, target: Target) -> str:
        if target == Target.ANSIBLE:
            return f"'{self.val}'"  # single quotes in ansible cannot be evaluated with variables
        elif target == Target.PYINFRA:
            return f'"{self.val}"'
        else:
            raise UnsupportedTargetValueError(target, self)
        
    def __repr__(self):
        return super().__repr__()

class ServiceNameType(BaseType):
    def __init__(self):
        super().__init__()

    def __get_units_with_status(self, systemd) -> List[tuple[str, str]]:
        # Fetch all units managed by systemd
        manager = systemd.Manager()
        manager.load()
        all = [
            (basename(elem[0].decode("utf-8")), elem[1].decode("utf-8"))
            for elem in manager.Manager.ListUnitFiles()
        ]
        # Filter out those that should be ignored
        return [elem for elem in filter(
            lambda x: x[0] not in ignore_list,
            all
        )]

    def generate(self) -> ServiceNameValue:
        # Dynamically load pystemd
        systemd = importlib.import_module("pystemd.systemd1")
        units = self.__get_units_with_status(systemd)

        # Filter the units to only contain services
        # without parameters (those without @, otherwise it is unclear
        # how those services should be addressed)
        services = [elem for elem in filter(
            lambda x: x[0].endswith(".service") and "@" not in x[0],
            units
        )]

        # Filter the services to only include those with
        # a valid status
        to_choose = [elem for elem in filter(
            lambda x: x[1] in valid_status,
            services
        )]

        # Choose a name and fetch the current status
        service_name = choice(to_choose)[0]
        status = ServiceStatusFetcher.fetch(service_name)
        return ServiceNameValue(service_name, status)