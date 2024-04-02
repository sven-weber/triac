import base64
import pickle
from os import getcwd
from os.path import commonprefix, dirname, join, relpath
from typing import Any

import docker

from triac.lib.encoding import encode, decode
from triac.lib.docker.types.base_images import BaseImages
from triac.lib.docker.types.container import Container

TRIAC_SRC_DIR = "/usr/lib/python3/dist-packages/triac"
TRIAC_WORKING_DIR = "/usr/app/triac"


class DockerClient:
    def __init__(self):
        self._client = docker.from_env()

    def get_client(self):
        return self._client

    # Returns the build image
    def build_base_image(self, img: BaseImages):
        print(f"Building base image {img}")
        docker_file_path = join(dirname(__file__), "images", img.value)
        repository_root = getcwd()
        image_identifier = f"triac:{img}"
        res = self.get_client().images.build(
            path=repository_root,
            dockerfile=docker_file_path,
            pull=True,
            tag=image_identifier,
        )
        print(f"Base image finished building")
        return image_identifier

    def get_triac_dir_in_repo(self):
        return join(getcwd(), "triac")

    def run_container_from_image(self, image_identifier: str) -> Container:
        print(f"Starting container for image {image_identifier}")
        ssh_image_port = "22/tcp"
        container = self.get_client().containers.run(
            image=image_identifier,
            privileged=True,
            detach=True,
            cgroupns="host",
            ports={ssh_image_port: 0},  # Bind random free port to 22 (ssh)
            volumes={
                # Working dir
                "triac-working-dir": {"bind": TRIAC_WORKING_DIR},
                # Needed for systemd
                "/sys/fs/cgroup": {"bind": "/sys/fs/cgroup"},
                # Needed to export state from the container
                self.get_triac_dir_in_repo(): {"bind": TRIAC_SRC_DIR, "mode": "ro"},
            },
        )
        container.reload()
        assert container.status == "running"
        ssh_host_port = container.ports[ssh_image_port][0]["HostPort"]
        print(f"Container running with ssh available at port {ssh_host_port}")
        return Container(container.id, ssh_host_port, container)

    def get_runner_path(self):
        relative_path_to_lib_docker = relpath(
            dirname(__file__),
            commonprefix([dirname(__file__), self.get_triac_dir_in_repo()]),
        )
        return join(
            TRIAC_SRC_DIR, relative_path_to_lib_docker, "runners", "run_in_container.py"
        )

    def execute_obj_method_in_container(
        self, obj: Any, method: str, container: Container
    ):
        # Dump the object
        encoded_obj = encode(obj)

        # Call the script in the container
        res = container.base_obj.exec_run(
            workdir=TRIAC_WORKING_DIR,
            cmd=f"python3 {self.get_runner_path()} {TRIAC_SRC_DIR} {encoded_obj} {method}",
        )
        assert res[0] == 0  # Check exit code

        # Unpickle the result
        res = decode(res[1])

        # Return
        return res

    def stop_container(self, container: Container):
        container.base_obj.stop()
        container.base_obj.wait()

    def commit_container_to_image(self, container: Container):
        self.stop_container(container)
        image_repository = "triac"
        image_tag = "intermediate-state"
        container.base_obj.commit(repository=image_repository, author="triac", tag=image_tag)
        return f"triac:intermediate-state"

    def remove_container(self, container: Container):
        print(f"Removing container with id {container.id}")
        self.stop_container(container)
        container.base_obj.remove(v=True)
        print(f"Container with id {container.id} removed")

    def remove_image(self, image: str):
        self.get_client().images.remove(image)
