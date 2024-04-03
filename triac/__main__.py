import logging
import random
import sys
import time
from threading import Thread

import click

from triac.lib.docker.client import DockerClient
from triac.lib.docker.types.base_images import BaseImages
from triac.lib.generator.ansible import Ansible
from triac.lib.random import Fuzzer
from triac.types.execution import Execution
from triac.types.target import Target
from triac.types.wrappers import Wrappers
from triac.ui.cli_layout import CLILayout
from triac.ui.log_handler import UILoggingHandler
from triac.values.user import UserType
from triac.wrappers.file import File


def exec_fuzzing(state: Execution):
    logger = logging.getLogger(__name__)
    user = UserType()

    docker = DockerClient()
    base_image = BaseImages.DEBIAN12
    image = docker.build_base_image(base_image)
    wrappers = Wrappers(base_image, [])

    wrapper = File()
    container = docker.run_container_from_image(image)

    state = wrappers.append(wrapper, container)
    logger.info("wanted")
    logger.info(state)
    ansible = Ansible(wrapper, state, container)
    logger.info("obtained")
    logger.info(ansible.run())

    image = docker.commit_container_to_image(container)
    docker.remove_container(container)

    docker.remove_image(image)


def generate_execution(rounds, base_image, log_level):
    # Get the base image
    if base_image != None:
        BaseImages[base_image]
    else:
        base_image = Fuzzer().fuzz_base_image()

    # Create new execution
    return Execution(base_image, rounds, log_level)


@click.command()
@click.option(
    "--rounds", default=2, help="Number of rounds to perform", show_default=True
)
@click.option(
    "--log-level",
    default="INFO",
    show_default=True,
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
)
@click.option(
    "--base-image",
    help="The base image to use. If not specified, one is chosen randomly",
    type=click.Choice([val.name for val in BaseImages]),
)
def fuzz(rounds, log_level, base_image):
    """Start a TRIaC fuzzing session"""

    # Generate execution
    state = generate_execution(rounds, base_image, log_level)

    # initialize the UI
    ui = CLILayout(state)

    # Start the threads to display the UI and computation
    fuzz_worker = Thread(target=exec_fuzzing, args=(state,))
    ui_worker = Thread(target=ui.render_ui)

    fuzz_worker.start()
    ui_worker.start()

    fuzz_worker.join()
    ui_worker.join()


if __name__ == "__main__":
    fuzz()
    sys.exit(0)
