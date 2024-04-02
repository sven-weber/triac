from tempfile import mkdtemp
from shutil import rmtree

class Tmp:
    def __init__(self) -> None:
        self.__path = mkdtemp()
        pass

    @property
    def tmp_path(self) -> str:
        return self.__path

    def destroy(self) -> None:
        rmtree(self.__path)
