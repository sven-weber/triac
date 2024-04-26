import random
from random import choice
from typing import Any, Dict, List


from triac.lib.docker.types.base_images import BaseImages
from triac.lib.docker.types.container import Container
from triac.types.wrapper import Definition, State, Wrapper

BOOLEANS = [True, False]


def probability_bound(prob: float) -> float:
    return min(max(prob, 0), 100)


class Fuzzer:
    def __init__(self) -> None:
        pass

    @staticmethod
    def fuzz_dict(d: Dict[str, List[Any]]) -> Dict[str, Any]:
        res = {}
        for key, vals in d.items():
            res[key] = choice(vals)
        return res

    @staticmethod
    def fuzz_state(d: Definition, container: Container) -> State:
        res = {}
        for key, typ in d.items():
            res[key] = container.execute_method(typ, "generate", [])
        return res

    @staticmethod
    def fuzz_base_image() -> BaseImages:
        return choice([val for val in BaseImages])

    @staticmethod
    @staticmethod
    def fuzz_wrapper(current: Wrapper, options: List[type[Wrapper]]) -> Wrapper:
        """
        Randomly chooses the next wrapper to be executed.
        """
        to_choose = options[:]
        # Choose the same twice as likely as a new one
        if current != None:
            to_choose.append(current)

        return choice(to_choose)
