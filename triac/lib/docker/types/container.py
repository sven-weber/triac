import logging
from os.path import commonprefix, dirname, join, realpath, relpath
from typing import Any, List

from triac.lib.docker.const import TRIAC_DIR_IN_REPO, TRIAC_SRC_DIR, TRIAC_WORKING_DIR
from triac.lib.encoding import decode, encode


class Container:
    def __init__(self, id, ssh_port, base_obj):
        self.__id = id
        self.__ssh_port = ssh_port
        self.__base_obj = base_obj

    @property
    def id(self):
        return self.__id

    @property
    def ssh_port(self):
        return self.__ssh_port

    @property
    def base_obj(self):
        return self.__base_obj

    def __get_runner_path(self):
        file_dirname = realpath(join(dirname(__file__), ".."))
        relative_path_to_lib_docker = relpath(
            file_dirname,
            commonprefix([file_dirname, TRIAC_DIR_IN_REPO]),
        )
        return join(
            TRIAC_SRC_DIR, relative_path_to_lib_docker, "runners", "run_in_container.py"
        )

    def execute_method(self, obj: Any, method: str, arguments: List[Any] = []) -> Any:
        # Dump the object
        encoded_obj = encode(obj)
        encoded_args = " ".join([encode(arg) for arg in arguments])

        logger = logging.getLogger(__name__)
        logger.debug(f"Executing method {method} in container")

        # Call the script in the container
        res = self.base_obj.exec_run(
            workdir=TRIAC_WORKING_DIR,
            user="root",
            cmd=f"python3 {self.__get_runner_path()} {TRIAC_SRC_DIR} {encoded_obj} {method} {encoded_args}",
        )
        # Check exit code
        if res[0] != 0:
            print(res[1])
            raise AssertionError(
                f"Execution of method in container failed. Exit code {res[0]}"
            )

        logger.debug(f"Method {method} executed successfully")

        # Unpickle the result
        res = decode(res[1])

        # Log the std and stderr of the execution
        if res["std_out"] != "":
            logger.debug("Execution std out:")
            logger.debug(res["std_out"])
        if res["std_err"] != "":
            logger.debug("Execution std err:")
            logger.debug(res["std_err"])

        return res["method_result"]
