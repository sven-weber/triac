import logging
from os.path import join

from ansible_runner import run_async as ansible_run
from ansible_runner.interface import InventoryConfig

from triac.lib.docker.types.container import Container
from triac.lib.generator.key import Key
from triac.lib.generator.tmp import Tmp
from triac.types.target import Target
from triac.types.wrapper import State, Wrapper


class Ansible(Tmp, Key):
    def __init__(self, wrapper: Wrapper, state: State, container: Container) -> None:
        Tmp.__init__(self)
        Key.__init__(self)

        self.__wrapper = wrapper
        self.__state = state
        self.__container = container
        self.__logger = logging.getLogger(__name__)

        self.__inventory_path = join(super().tmp_path, "inventory.yaml")
        self.__playbook_path = join(super().tmp_path, "playbook.yaml")

        self.__generate()

    def __inventory(self) -> str:
        return f"""
all:
  hosts:
    target:
      ansible_host: localhost
      ansible_port: {self.__container.ssh_port}
      ansible_user: root
      ansible_ssh_private_key_file: {self.key_path}
      ansible_ssh_common_args: "-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o IdentitiesOnly=yes"
        """

    def __playbook(self) -> str:
        raw_task = self.__wrapper.transform(Target.ANSIBLE, self.__state)
        task = ""
        for i, line in enumerate(raw_task.split("\n")):
            if i != 0:
                task += "      " + line
            else:
                task += line
            task += "\n"

        return f"""
- name: {type(self.__wrapper).__name__}
  hosts: target
  tasks:
    - {task}"""

    def __generate(self) -> None:
        inventory_file = open(self.__inventory_path, "w+")
        inventory_file.write(self.__inventory())
        inventory_file.close()

        playbook_file = open(self.__playbook_path, "w+")
        playbook_file.write(self.__playbook())
        playbook_file.close()
        pass

    def run(self) -> State:
        _, runner = ansible_run(
            inventory=self.__inventory_path, playbook=self.__playbook_path, quiet=True
        )
        # TODO: use these
        # Check for failed and unreachable
        # runner_on_failed
        for event in runner.events:
            if "event" in event:
                self.__logger.debug(f'Ansible execution event: {event["event"]}')
                self.__logger.debug(event)
        state = self.__container.execute_method(
            self.__wrapper, "verify", [self.__state]
        )
        return state