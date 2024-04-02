from typing import List, Tuple, cast

from triac.lib.docker.types.base_images import BaseImages
from triac.lib.docker.types.container import Container
from triac.lib.encoding import decode, encode
from triac.lib.random import Fuzzer
from triac.types.wrapper import State, Wrapper


class Identifier:
    def __init__(self, obj: Wrapper) -> None:
        cls = obj.__class__
        self.__cls = cls.__qualname__
        self.__mod = cls.__module__

    @property
    def mod(self) -> str:
        return self.__mod

    @property
    def cls(self) -> str:
        return self.__cls

class Wrappers:
    def __init__(self, base_image: BaseImages, data: List[Tuple[Identifier, State]]) -> None:
        self.base_image = base_image
        self.data = data
        pass

    def save(self, dest: str) -> None:
        file = open(dest, 'w')
        file.write(encode(self))
        file.close()
        pass

    def append(self, wrapper: Wrapper, container: Container) -> State:
        identifier = Identifier(wrapper)
        state = Fuzzer.fuzz_state(wrapper.definition(), container)
        self.data.append((identifier, state))
        return state

def load(path: str) -> Wrappers:
    with open(path, 'r') as file:
        return cast(Wrappers, decode(file.read()))
