
import docker
from os.path import join, dirname
from lib.docker.base_images import BaseImages

client = docker.from_env()

# Returns the build image
def build_base_image(img: BaseImages):
    images_path = join(dirname(__file__), "images")
    res = client.images.build(path=images_path, dockerfile=img.value, pull=True, tag=f"triac:{img}")
    return res[0]