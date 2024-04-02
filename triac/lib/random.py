from random import choice
from typing import Any, Dict, List

from triac.types.wrapper import Definition, State

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
    def fuzz_state(d: Definition) -> State:
        res = {}
        for key, typ in d.items():
            res[key] = typ.generate()
        return res
