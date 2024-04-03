from asyncio import Event
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


def exec_fuzzing_round(execution: Execution):
    logger = logging.getLogger(__name__)
    docker = DockerClient()

    # Start new round
    execution.start_new_round()
    logger.info(f"Starting fuzzing round {execution.round} on image {execution.base_image.name}")

    # Build the base image
    image = docker.build_base_image(execution.base_image)

    while(execution.wrappers_left_in_round()):
        # TODO: Do this with multiple tools to enable differential testing
        container = docker.run_container_from_image(image)

        try:
            # Randomly choose next wrapper and execute
            # TODO: Randomly choose wrapper
            wrapper = File()
            
            # Instantiate target state
            target_state = execution.add_wrapper_to_round(wrapper, container)
            logger.info("target state:")
            logger.info(target_state)

            # Execute IaC tool
            is_state =  Ansible(wrapper, target_state, container).run()
            logger.info("obtained state:")
            logger.info(is_state)

            # TODO: state comparison and error finding

            # Commit container for next round then remove
            image = docker.commit_container_to_image(container)
            execution.add_image_to_used(image)
        finally:
            docker.remove_container(container)

def exec_fuzzing(execution: Execution, stop_event : Event):
    logger = logging.getLogger(__name__)

    # Execute all the rounds
    while(execution.rounds_left()):
        exec_fuzzing_round(execution)

    # TODO: Cleanup docker images
    logger.info("Cleaning up resources")

    logger.info("Execution finished")


@click.command()
@click.option(
    "--rounds",
    help="Number of rounds to perform",
    type=click.IntRange(1),
    default=2,
    show_default=True,
)
@click.option(
    "--wrappers-per-round",
    help="The maximum number of wrappers to try in each round before starting the next round",
    type=click.IntRange(1),
    default=10,
    show_default=True,
)
@click.option(
    "--log-level",
    default="INFO",
    show_default=True,
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
)
@click.option(
    "--base-image",
    help="The base image to use. If not specified, one is chosen randomly each round",
    type=click.Choice([val.name for val in BaseImages]),
)
def fuzz(rounds, wrappers_per_round, log_level, base_image):
    """Start a TRIaC fuzzing session"""

    # Generate execution
    state = Execution(base_image, rounds, wrappers_per_round, log_level)

    # Stop event
    event = Event()
    
    # initialize the UI
    ui = CLILayout(state)

    # Start the threads to display the UI and computation
    fuzz_worker = Thread(target=exec_fuzzing, args=(state, event))
    ui_worker = Thread(target=ui.render_ui, args=(event, ))

    fuzz_worker.start()
    ui_worker.start()

    fuzz_worker.join()
    event.set() #Set the when the worker finished to close the UI

    ui_worker.join()


if __name__ == "__main__":
    fuzz()
    sys.exit(0)
