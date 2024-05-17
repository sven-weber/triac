from os import getcwd
from os.path import join
from typing import List

from triac.lib.docker.types.base_images import BaseImages

TRIAC_SRC_DIR = "/usr/lib/python3/dist-packages/triac"
TRIAC_WORKING_DIR = "/usr/app/triac"
TRIAC_DIR_IN_REPO = join(getcwd(), "triac")


def get_base_image_identifiers() -> List[str]:
    return [get_image_identifier(val) for val in BaseImages]


def get_image_identifier(img: BaseImages):
    return f"triac:{img.name}"
