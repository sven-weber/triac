import importlib
from posixpath import basename
from random import choice
from triac.types.base import BaseType, BaseValue
from triac.types.errors import UnsupportedTargetValueError
from triac.types.target import Target

ignore_list = ["systemd-volatile-root.service", "ssh.service", "sshd.service"]

class ServiceNameValue(BaseValue):
    def __init__(self, val: str) -> None:
        super().__init__(val)

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

    def generate(self) -> ServiceNameValue:
        # Dynamically load pystemd
        systemd = importlib.import_module("pystemd.systemd1")
        # Fetch all units managed by systemd
        manager = systemd.Manager()
        manager.load()
        all = [basename(elem[0].decode("utf-8")) for elem in manager.Manager.ListUnitFiles()]
        all = [elem for elem in filter(
            lambda x: x not in ignore_list,
            all
        )]

        # Filter out the services and return once of them
        services = [elem for elem in filter(
            lambda x: x.endswith(".service") and "@" not in x,
            all
        )]
        return ServiceNameValue(choice(services))