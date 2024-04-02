from os import getcwd
from os.path import join


class Key:
    def __init__(self) -> None:
        self.__key_path = join(getcwd(), "ssh-keys", "is_rsa")

    @property
    def key_path(self) -> str:
        return self.__key_path
