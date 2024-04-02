from triac.lib.docker.client import DockerClient
from triac.lib.docker.types.base_images import BaseImages
from triac.types.target import Target
from triac.values.user import UserType

if __name__ == "__main__":
    user = UserType()

    docker = DockerClient()
    image = docker.build_base_image(BaseImages.UBUNTU22)
    for i in range(0, 1):
        container = docker.run_container_from_image(image)
        obj = docker.execute_obj_method_in_container(user, "generate", container)
        print(obj.transform(Target.ANSIBLE))
        image = docker.commit_container_to_image(container)
        docker.remove_container(container)
    
    docker.remove_image(image)


