from datetime import datetime
from typing import Any, List, Set, Tuple

from triac.lib.docker.types.base_images import BaseImages
from triac.lib.docker.types.container import Container
from triac.lib.random import Fuzzer
from triac.types.wrapper import State, Wrapper
from triac.types.wrappers import Identifier, Wrappers


class Execution:
    def __init__(
        self,
        user_preferred_base_image: Any,
        keep_base_images: bool,
        total_rounds: int,
        wrappers_per_round: int,
        log_level: str,
    ) -> None:
        self.__fuzzer = Fuzzer()
        self.__user_preferred_base_image = user_preferred_base_image
        self.__keep_base_images = keep_base_images
        self.__total_rounds = total_rounds
        self.__wrappers_per_round = wrappers_per_round
        self.__log_level = log_level
        self.__start_time = datetime.now()
        self.__used_docker_images = set()
        self.__round = 0
        self.__errors = 0
        self.__wrappers = Wrappers(None, [])

    def wrappers_left_in_round(self) -> bool:
        return self.__wrappers.count < self.__wrappers_per_round

    def add_wrapper_to_round(self, wrapper: Wrapper, container: Container) -> State:
        return self.__wrappers.append(wrapper, container)

    def rounds_left(self) -> bool:
        return self.round < self.total_rounds

    def start_new_round(self):
        assert self.rounds_left() == True

        new_base = self.get_next_base_image()
        self.__wrappers = Wrappers(new_base, [])
        self.__round += 1

    def get_next_base_image(self) -> BaseImages:
        # Choose user specification or new random image
        if self.__user_preferred_base_image != None:
            return BaseImages[self.__user_preferred_base_image]
        else:
            return self.__fuzzer.fuzz_base_image()

    def add_image_to_used(self, img: str) -> None:
        self.__used_docker_images.add(img)

    @property
    def base_image(self) -> str:
        return self.__wrappers.base_image

    @property
    def keep_base_images(self) -> bool:
        return self.__keep_base_images

    @property
    def target_states(self) -> List[Tuple[Identifier, State]]:
        return self.__wrappers.target_states

    @property
    def total_rounds(self) -> int:
        return self.__total_rounds

    @property
    def round(self) -> int:
        return self.__round

    @property
    def wrappers_per_round(self) -> int:
        return self.__wrappers_per_round

    @property
    def num_wrappers_in_round(self) -> int:
        return self.__wrappers.count

    @property
    def used_docker_images(self) -> Set[str]:
        return self.__used_docker_images

    @property
    def log_level(self) -> str:
        return self.__log_level

    @property
    def elapsed_time(self) -> any:
        current_time = datetime.now()
        return current_time - self.__start_time

    @property
    def errors(self) -> int:
        return self.__errors
