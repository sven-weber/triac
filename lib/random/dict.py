from random import choice
from typing import Dict, List, Any


def random_dict_choice(d: Dict[str, List[Any]]) -> Dict[str, Any]:
    res = {}
    for key, vals in d.items(): 
        res[key] = choice(vals)
    return res
