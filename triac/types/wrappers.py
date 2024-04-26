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

    def __repr__(self):
        return f"{self.__cls}"

    @property
    def cls(self) -> str:
        return self.__cls


class Wrappers:
    def __init__(
        self, base_image: BaseImages, data: List[Tuple[Identifier, State]]
    ) -> None:
        self.__base_image = base_image
        self.__data = data
        self.__last_wrapper = None
        self.__has_error = False
        self.__error_target = {}
        self.__error_actual = {}
        pass

    def encode(self) -> str:
        return encode(self)

    @property
    def count(self) -> int:
        return len(self.__data)

    @property
    def target_states(self) -> List[Tuple[Identifier, State]]:
        return self.__data

    def get_last_wrapper(self) -> Wrapper:
        return self.__last_wrapper

    def set_error_state(self, target: State, actual: State) -> None:
        self.__has_error = True
        self.__error_target = target
        self.__error_actual = actual

    def append(self, wrapper: Wrapper, container: Container) -> State:
        identifier = Identifier(wrapper)
        state = Fuzzer.fuzz_state(wrapper.definition(), container)
        self.__data.append((identifier, state))
        self.__last_wrapper = wrapper
        return state

    @property
    def base_image(self) -> str:
        return self.__base_image


def load(path: str) -> Wrappers:
    with open(path, "r") as file:
        return cast(Wrappers, decode(file.read()))
