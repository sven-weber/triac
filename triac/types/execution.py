from enum import Enum
import glob
import logging
from datetime import datetime
from os import getcwd
from os.path import join
from typing import Any, List, Set, Tuple

from triac.lib.docker.types.base_images import BaseImages
from triac.lib.docker.types.container import Container
from triac.lib.random import Fuzzer
from triac.types.errors import WrappersExhaustedError
from triac.types.target import Target
from triac.types.wrapper import State, Wrapper
from triac.types.wrappers import Identifier, Wrappers

class ExecutionMode(Enum):
    UNIT = "unit"
    DIFFERENTIAL = "differential"

class Execution:
    def __init__(
        self,
        user_preferred_base_image: Any,
        keep_base_images: bool,
        total_rounds: int,
        wrappers_per_round: int,
        log_level: str,
        ui_log_level: str,
        continue_on_error: bool,
        unit: Target,
        differential: str
    ) -> None:
        self.__fuzzer = Fuzzer()
        self.__user_preferred_base_image = user_preferred_base_image
        self.__keep_base_images = keep_base_images
        self.__total_rounds = total_rounds
        self.__wrappers_per_round = wrappers_per_round
        self.__log_level = log_level
        self.__ui_log_level = ui_log_level
        self.__continue_on_error = continue_on_error
        self.__unit = Target[unit] if unit != None else None
        diff_target = self.__parse_differential(differential)
        self.__first_differential = diff_target[0]
        self.__second_differential = diff_target[1]
        self.__start_time = datetime.now()
        self.__used_docker_images = set()
        self.__round = 0
        self.__errors = 0
        self.__wrappers = Wrappers(None, [])

    def __parse_differential(self, differential) -> tuple[Target, Target]:
        if (differential == None):
            return (None, None)
        
        # Parse
        split = differential.split(":")
        return (Target[split[0]], Target[split[1]])


    def load_list_of_wrapper_classes(self) -> List[type[Wrapper]]:
        logger = logging.getLogger(__name__)
        logger.info(f"Loading available wrappers for fuzzing")

        self.__available_wrappers : List[Wrapper] = []
        repository_root = getcwd() + "/"
        modules = glob.glob(join(repository_root, "triac", "wrappers", "*.py"))
        modules = list(map(lambda f: f.replace(repository_root, ""), modules))

        # Import the modules
        for module in modules:
            import_path = module.replace("/", ".").replace(".py", "")
            mod = __import__(import_path, fromlist=[None])
            class_name = import_path.split(".")[-1].capitalize()
            try:
                loaded_class = getattr(mod, class_name)
                self.__available_wrappers.append(loaded_class)
                logger.debug(f"Loaded triac module {class_name} from {import_path}")
            except:
                logger.error(
                    f"Could not load wrapper module from {import_path}, assuming class name {class_name}"
                )

        logger.info(f"Loaded {len(self.__available_wrappers )} wrappers for fuzzing")
        return self.__available_wrappers

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

    def get_next_wrapper(self, container: Container) -> Wrapper:
        last = self.__wrappers.get_last_wrapper()
        available = self.__available_wrappers

        # Filter available wrappers according to mode
        if self.mode() == ExecutionMode.UNIT:
            available = [elem for elem in filter(lambda w: self.unit_target in w.supported_targets(), available)]
        else:
            first = self.first_differential_target
            second = self.second_differential_target
            available = [
                elem for elem in filter(
                    lambda w: first in w.supported_targets() and second in w.supported_targets(),
                    available
                )
            ]

        logger = logging.getLogger(__name__)
        logger.debug(f"Fuzzing next wrapper")

        while True:
            if len(available) == 0:
                raise WrappersExhaustedError()

            # Search for wrapper that is capable
            wrapper = self.__fuzzer.fuzz_wrapper(last, available)

            logger.debug(f"Checking if {wrapper} can execute")

            # See if wrapper can be executed in the environment
            capable = container.execute_method(wrapper, "can_execute")

            if capable == True:
                logger.debug(f"Found {wrapper} which can run in the environment")
                return wrapper
            else:
                logger.debug(f"{wrapper} cannot run. Trying next")
                available.remove(wrapper)
                if wrapper == last:
                    last = None

    def add_image_to_used(self, img: str) -> None:
        self.__used_docker_images.add(img)

    def set_error_for_round(self, target: State, actual: State):
        self.__errors += 1
        self.__wrappers.set_error_state(target, actual)

    def encode_wrappers_for_round(self) -> str:
        return self.__wrappers.encode()

    def mode(self) -> ExecutionMode:
        if self.__unit != None:
            return ExecutionMode.UNIT
        return ExecutionMode.DIFFERENTIAL

    @property
    def unit_target(self) -> Target:
        return self.__unit
    
    @property
    def first_differential_target(self) -> Target:
        return self.__first_differential
    
    @property
    def second_differential_target(self) -> Target:
        return self.__second_differential

    @property
    def continue_on_error(self) -> bool:
        return self.__continue_on_error

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
    def ui_log_level(self) -> str:
        return self.__ui_log_level

    @property
    def elapsed_time(self) -> any:
        current_time = datetime.now()
        return current_time - self.__start_time

    @property
    def errors(self) -> int:
        return self.__errors
