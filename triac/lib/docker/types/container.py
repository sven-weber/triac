class Container:
    def __init__(self, id, ssh_port, base_obj):
        self._id = id
        self._ssh_port = ssh_port
        self._base_obj = base_obj

    @property
    def id(self):
        return self._id

    @property
    def ssh_port(self):
        return self._ssh_port

    @property
    def base_obj(self):
        return self._base_obj
