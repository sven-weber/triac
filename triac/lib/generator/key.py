from os import chmod, getcwd
from os.path import join
from stat import S_IRUSR, S_IWUSR


class Key:
    def __init__(self) -> None:
        self.__key_path = join(getcwd(), "ssh-keys", "id_rsa")
        chmod(self.__key_path, S_IWUSR | S_IRUSR)

    @property
    def key_path(self) -> str:
        return self.__key_path
