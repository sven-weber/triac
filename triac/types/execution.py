from datetime import datetime

from triac.lib.docker.types.base_images import BaseImages
from triac.types.wrappers import Wrappers


class Execution:
    def __init__(self, base_image: BaseImages, num_rounds: int) -> None:
        self.__wrappers = Wrappers(base_image, [])
        self.__rounds = num_rounds
        self.__start_time = datetime.now()
        self.__round = 0
        self.__errors = 0
        pass

    @property
    def base_image(self) -> str:
        return self.__wrappers.base_image

    @property
    def total_rounds(self) -> int:
        return self.__rounds

    @property
    def elapsed_time(self) -> any:
        current_time = datetime.now()
        return current_time - self.__start_time

    @property
    def round(self) -> int:
        return self.__round

    @round.setter
    def round(self, round: int):
        self.__round = round

    @property
    def errors(self) -> int:
        return self.__errors
