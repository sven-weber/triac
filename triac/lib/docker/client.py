import io
import logging
from os import getcwd
import os
from os.path import dirname, join
import tarfile

import docker

from triac.lib.docker.const import TRIAC_DIR_IN_REPO, TRIAC_SRC_DIR, TRIAC_WORKING_DIR
from triac.lib.docker.types.base_images import BaseImages
from triac.lib.docker.types.container import Container


class DockerClient:
    def __init__(self):
        self._client = docker.from_env()
        self.__logger = logging.getLogger(__name__)

    def get_client(self):
        return self._client

    def get_image_identifier(self, img: BaseImages):
        return f"triac:{img}"

    # Returns the build image
    def build_base_image(self, img: BaseImages):
        self.__logger.info(f"Building base image {img.name}")
        docker_file_path = join(dirname(__file__), "images", img.value)
        repository_root = getcwd()
        image_identifier = self.get_image_identifier(img)
        self.get_client().images.build(
            path=repository_root,
            dockerfile=docker_file_path,
            pull=True,
            rm=True,
            tag=image_identifier,
        )
        self.__logger.info(f"Base image finished building")
        return image_identifier

    def __ensure_working_dir_exists(self, container):
        try:
            # If this succeeds, the path exists
            container.get_archive(TRIAC_WORKING_DIR)
            return True
        except:
            # Ensure the path exists
            mem_stream = io.BytesIO()
            with tarfile.open(fileobj=mem_stream, mode="w") as tar:
                directory = tarfile.TarInfo(name=TRIAC_WORKING_DIR)
                directory.type = tarfile.DIRTYPE
                tar.addfile(directory)
            mem_stream.seek(0) # Back to beginning of the stream
            container.put_archive("/", mem_stream)
            return True

    def run_container_from_image(self, image_identifier: str) -> Container:
        self.__logger.debug(f"Starting container for image {image_identifier}")
        ssh_image_port = "22/tcp"
        container = self.get_client().containers.run(
            image=image_identifier,
            privileged=True,
            detach=True,
            cgroupns="host",
            ports={ssh_image_port: 0},  # Bind random free port to 22 (ssh)
            volumes={
                # Needed for systemd
                "/sys/fs/cgroup": {"bind": "/sys/fs/cgroup"},
                # Needed to export state from the container
                TRIAC_DIR_IN_REPO: {"bind": TRIAC_SRC_DIR, "mode": "ro"},
            },
        )
        container.reload()
        assert container.status == "running"
        ssh_host_port = container.ports[ssh_image_port][0]["HostPort"]
        self.__ensure_working_dir_exists(container)
        self.__logger.debug(
            f"Container running with ssh available at port {ssh_host_port}"
        )
        return Container(container.id, ssh_host_port, container)

    def commit_container_to_image(self, container: Container):
        image_repository = "triac"
        image_tag = "intermediate-state"
        container.base_obj.commit(
            repository=image_repository, author="triac", tag=image_tag
        )
        return f"{image_repository}:{image_tag}"

    def remove_container(self, container: Container):
        self.__logger.debug(f"Removing container with id {container.id}")
        container.base_obj.remove(v=True, force=True)
        self.__logger.debug(f"Container with id {container.id} removed")

    def remove_image(self, image: str):
        self.get_client().images.remove(image)
