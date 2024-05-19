import logging
import subprocess
from os.path import join
from typing import Container, List

from triac.lib.generator.errors import PyInfraError
from triac.lib.generator.key import Key
from triac.lib.generator.tmp import Tmp
from triac.types.target import Target
from triac.types.wrapper import State, Wrapper


class PyInfra(Tmp, Key):
    def __init__(self, wrapper: Wrapper, state: State, container: Container) -> None:
        Tmp.__init__(self)
        Key.__init__(self)

        self.__wrapper = wrapper
        self.__state = state
        self.__container = container
        self.__logger = logging.getLogger(__name__)

        self.__operations_path = join(super().tmp_path, "deploy.py")
        self.__inventory_path = join(super().tmp_path, "inventory.py")

        self.__generate()

    def __deploy_script(self):
        return self.__wrapper.transform(Target.PYINFRA, self.__state)

    def __host_inventory(self):
        return f"""
targets = [
    ("localhost", {{
        "ssh_hostname": "localhost",
        "ssh_port": {self.__container.ssh_port},
        "ssh_key": "{self.key_path}",
        "ssh_user": "root",
        "ssh_allow_agent": False,
        "ssh_known_hosts_file" : "/dev/null",
        "ssh_strict_host_key_checking" : "no"
    }})
]
        """

    def __generate(self):
        # Inventory
        with open(self.__inventory_path, "w+") as inventory:
            inventory.write(self.__host_inventory())

        # Deploy script
        with open(self.__operations_path, "w+") as deploy_script:
            script = self.__deploy_script()
            self.__logger.debug(
                "Generated the following deployment script for pyinfra:"
            )
            self.__logger.debug(f"\n{script}")
            deploy_script.write(script)

    def __get_pyinfra_invocation(self) -> List[str]:
        return ["pyinfra", self.__inventory_path, self.__operations_path, "--no-wait"]

    def run(self) -> State:
        pyinfra = subprocess.run(
            self.__get_pyinfra_invocation(), capture_output=True, text=True
        )

        # Cleanup the temp files
        self.destroy()

        if pyinfra.stdout != "":
            self.__logger.debug("Got the following stdout during pyinfra execution:")
            self.__logger.debug(pyinfra.stdout)

        if pyinfra.stderr != "":
            self.__logger.debug("Got the following stderr during pyinfra execution:")
            self.__logger.debug(pyinfra.stderr)

        if pyinfra.returncode != 0:
            raise PyInfraError(pyinfra.returncode)

        # Fetch the reached state and return that
        return self.__container.execute_method(self.__wrapper, "verify", [self.__state])
