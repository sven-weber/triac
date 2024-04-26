from os import chmod, getcwd
from stat import S_IWUSR, S_IRUSR
from os.path import join


class Key:
    def __init__(self) -> None:
        self.__key_path = join(getcwd(), "ssh-keys", "id_rsa")
        chmod(self.__key_path, S_IWUSR | S_IRUSR)

    @property
    def key_path(self) -> str:
        return self.__key_path
