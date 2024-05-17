from enum import Enum
from random import choice
from triac.types.base import BaseType, BaseValue
from triac.types.errors import UnsupportedTargetValueError
from triac.types.target import Target


class ServiceState(Enum):
    STARTED = "started"
    STOPPED = "stopped"
    #RELOADED = "reloaded",
    #RESTARTED = "restarted",
    

class ServiceStateValue(BaseValue):
    def __init__(self, val: ServiceState) -> None:
        super().__init__(val)

    def transform(self, target: Target) -> str:
        if target == Target.ANSIBLE:
            return f"'{self.val.value}'"  # single quotes in ansible cannot be evaluated with variables
        elif target == Target.PYINFRA:
            match self.val:
                case ServiceState.RELOADED:
                    return "reloaded=True"
                case ServiceState.RESTARTED:
                    return "restarted=True"
                case ServiceState.STARTED:
                    return "running=True"
                case ServiceState.STOPPED:
                    return "running=False"
        else:
            raise UnsupportedTargetValueError(target, self)

    def __repr__(self):
        return self.val.name

class ServiceStateType(BaseType):
    def __init__(self):
        super().__init__()

    def generate(self) -> ServiceStateValue:
        state = choice([state for state in ServiceState])
        return ServiceStateValue(state)
