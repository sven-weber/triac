from os import getcwd
from os.path import  dirname, join
from signal import SIGILL

import docker

from triac.lib.docker.const import TRIAC_DIR_IN_REPO
from triac.lib.docker.types.base_images import BaseImages
from triac.lib.docker.types.container import Container
from triac.lib.docker.const import TRIAC_SRC_DIR, TRIAC_WORKING_DIR


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
        self.get_client().images.build(
            path=repository_root,
            dockerfile=docker_file_path,
            pull=True,
            tag=image_identifier,
        )
        print(f"Base image finished building")
        return image_identifier


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
                TRIAC_DIR_IN_REPO: {"bind": TRIAC_SRC_DIR, "mode": "ro"},
            },
        )
        container.reload()
        assert container.status == "running"
        ssh_host_port = container.ports[ssh_image_port][0]["HostPort"]
        print(f"Container running with ssh available at port {ssh_host_port}")
        return Container(container.id, ssh_host_port, container)



    def commit_container_to_image(self, container: Container):
        image_repository = "triac"
        image_tag = "intermediate-state"
        container.base_obj.commit(
            repository=image_repository, author="triac", tag=image_tag
        )
        return f"triac:intermediate-state"

    def remove_container(self, container: Container):
        print(f"Removing container with id {container.id}")
        container.base_obj.remove(v=True, force=True)
        print(f"Container with id {container.id} removed")

    def remove_image(self, image: str):
        self.get_client().images.remove(image)
