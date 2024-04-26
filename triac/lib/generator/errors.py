from typing import Any


class AnsibleError(Exception):
    def __init__(self, error: str, event: Any):
        # TODO: make this message meaningful
        self.__error = error
        self.__event = event
        super().__init__(
            f"Ansible threw error: {self.__error}"
        )

    def event(self) -> Any:
        return self.__event
