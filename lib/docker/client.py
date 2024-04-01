import docker
import os
from lib.docker.base_images import BaseImages

client = docker.from_env()

def build_base_image(img: BaseImages):
    images_path = os.path.join(os.getcwd(), "images")
    print(images_path)
    image = client.images.build(path=images_path, dockerfile=img.value, pull=True)
    print(image[1])