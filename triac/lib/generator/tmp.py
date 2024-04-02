from shutil import rmtree
from tempfile import mkdtemp


class Tmp:
    def __init__(self) -> None:
        self.__path = mkdtemp()
        pass

    @property
    def tmp_path(self) -> str:
        return self.__path

    def destroy(self) -> None:
        rmtree(self.__path)
