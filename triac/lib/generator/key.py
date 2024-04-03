from os import getcwd
from os.path import join


class Key:
    def __init__(self) -> None:
        # TODO: Ensure correct permissions?
        self.__key_path = join(getcwd(), "ssh-keys", "id_rsa")

    @property
    def key_path(self) -> str:
        return self.__key_path
