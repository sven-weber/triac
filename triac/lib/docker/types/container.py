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
