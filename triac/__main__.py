import logging
import random
import sys
import time
from asyncio import Event
from threading import Thread

import click

from triac.lib.docker.client import DockerClient
from triac.lib.docker.const import get_base_image_identifiers
from triac.lib.docker.types.base_images import BaseImages
from triac.lib.errors import persist_error
from triac.lib.generator.ansible import Ansible
from triac.lib.random import Fuzzer
from triac.types.errors import StateMismatchError
from triac.types.execution import Execution
from triac.types.target import Target
from triac.types.wrappers import Wrappers
from triac.ui.cli_layout import CLILayout
from triac.ui.log_handler import UILoggingHandler
from triac.values.user import UserType
from triac.wrappers.file import File


def exec_fuzzing_round(execution: Execution):
    # Start new round
    execution.start_new_round()
    logger = logging.getLogger(__name__)
    logger.info(
        f"***** Starting fuzzing round {execution.round} on image {execution.base_image.name} *****"
    )
    docker = DockerClient()

    # Build the base image
    image = docker.build_base_image(execution.base_image)
    execution.add_image_to_used(image)

    while execution.wrappers_left_in_round():
        logger.info(f"---- Executing wrapper #{execution.num_wrappers_in_round}")

        # TODO: Do this with multiple tools to enable differential testing
        container = docker.run_container_from_image(image)

        try:
            # Randomly choose next wrapper and execute
            # TODO: Randomly choose wrapper
            wrapper = File()

            # Instantiate target state
            target_state = execution.add_wrapper_to_round(wrapper, container)

            # Execute IaC tool
            logger.info(f"Executing Ansible against target")
            is_state = Ansible(wrapper, target_state, container).run()

            logger.debug(f"Got the following actual state:")
            logger.debug(is_state)

            # Check states for equality
            if is_state != target_state:
                raise StateMismatchError(target_state, is_state)

            logger.info(f"Target state reached, wrapper finished")

            # Commit container for next round then remove
            image = docker.commit_container_to_image(container)
            execution.add_image_to_used(image)
        finally:
            docker.remove_container(container)


def exec_fuzzing(execution: Execution, stop_event: Event):
    logger = logging.getLogger(__name__)

    # Execute all the rounds
    while execution.rounds_left():
        try:
            exec_fuzzing_round(execution)
        except StateMismatchError as e:
            logger.error("Found mismatch between target and actual state")
            logger.error("Target state:")
            logger.error(e.target)
            logger.error("Actual state:")
            logger.error(e.actual)
            execution.set_error_for_round(e.target, e.actual)
            persist_error(execution, e)
        except Exception as e:
            logger.error("Encountered unexpected error during execution of round:")
            logger.error(e)
            if execution.continue_on_error == False:
                logger.error("Press any key to continue with the next round...")
                input()
            else:
                logger.error("Executing next round")

    logger.info("All rounds executed")

    # Cleanup
    # TODO: Also delete base images (e.g. debian:12?
    logger.info("Cleaning up resources")
    logger.debug("The following images where used during execution:")
    logger.debug(execution.used_docker_images)
    to_remove = filter(
        lambda elem: elem not in get_base_image_identifiers()
        or not execution.keep_base_images,
        execution.used_docker_images,
    )
    for image in to_remove:
        logger.debug(f"Removing image {image}")
        docker = DockerClient()
        docker.remove_image(image)

    # Done!
    logger.info("Execution finished")

    time.sleep(1)


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
@click.option(
    "--keep-base-images",
    help="Whether the base images that where build during the execution should be kept. This will increase the speed of future executions.",
    is_flag=True,
    default=False,
    show_default=True,
)
@click.option(
    "--continue-on-error",
    help="Whether triac should automatically continue with the execution of the next round whenever a unexpected error is encountered.",
    is_flag=True,
    default=False,
    show_default=True,
)
def fuzz(
    rounds,
    wrappers_per_round,
    log_level,
    base_image,
    keep_base_images,
    continue_on_error,
):
    """Start a TRIaC fuzzing session"""

    # Generate execution
    state = Execution(
        base_image,
        keep_base_images,
        rounds,
        wrappers_per_round,
        log_level,
        continue_on_error,
    )

    # Todo: Enable replay

    # Stop event
    # TODO: Handle interruption
    event = Event()

    # initialize the UI
    ui = CLILayout(state)

    # Start the threads to display the UI and computation
    fuzz_worker = Thread(target=exec_fuzzing, args=(state, event))
    ui_worker = Thread(target=ui.render_ui, args=(event,))

    fuzz_worker.start()
    ui_worker.start()

    fuzz_worker.join()
    event.set()  # Set event when the worker finished to close the UI

    ui_worker.join()


if __name__ == "__main__":
    fuzz()
    sys.exit(0)
