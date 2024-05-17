import logging
import signal
import sys
import time
from asyncio import Event
from threading import Thread
from typing import Dict, List
from art import text2art

import click
from deepdiff import DeepDiff

from triac.lib.docker.client import DockerClient
from triac.lib.docker.const import get_base_image_identifiers
from triac.lib.docker.types.base_images import BaseImages
from triac.lib.errors import persist_error
from triac.lib.generator.ansible import Ansible
from triac.types.errors import StateMismatchError, WrappersExhaustedError
from triac.types.execution import Execution
from triac.types.target import Target
from triac.ui.cli_layout import CLILayout


def exec_fuzzing_round(
    execution: Execution, stop_event: Event, image_cache: Dict[BaseImages, str]
):
    # Start new round
    execution.start_new_round()
    logger = logging.getLogger(__name__)
    logger.info(
        f"***** Starting fuzzing round {execution.round} on image {execution.base_image.name} *****"
    )
    docker = DockerClient()

    # Build the base image or take from cache
    if execution.base_image not in image_cache:
        image = docker.build_base_image(execution.base_image)
        execution.add_image_to_used(image)
        image_cache[execution.base_image] = image

    image = image_cache[execution.base_image]

    if stop_event.is_set():
        return

    while execution.wrappers_left_in_round():
        if stop_event.is_set():
            return
        logger.info(f"---- Executing wrapper #{execution.num_wrappers_in_round + 1}")

        # TODO: Do this with multiple tools to enable differential testing
        container = docker.run_container_from_image(image)

        try:
            if stop_event.is_set():
                return

            # Randomly choose next wrapper and execute
            try:
                wrapper = execution.get_next_wrapper(container)
            except WrappersExhaustedError as e:
                logger.error("There are no wrappers that can run in the reached state")
                raise e

            # Instantiate target state
            target_state = execution.add_wrapper_to_round(wrapper, container)
            if stop_event.is_set():
                return

            # Execute IaC tool
            logger.info(f"Executing Ansible against target")
            is_state = Ansible(wrapper, target_state, container).run()
            if stop_event.is_set():
                return

            logger.debug(f"Got the following actual state:")
            logger.debug(is_state)

            # Check states for equality
            if len(DeepDiff(is_state, target_state).affected_root_keys) > 0:
                raise StateMismatchError(target_state, is_state)

            logger.info(f"Target state reached, wrapper finished")
            if stop_event.is_set():
                return

            # Commit container for next round then remove
            image = docker.commit_container_to_image(container)
            execution.add_image_to_used(image)
        except StateMismatchError as e:
            logger.error("Found mismatch between target and actual state")
            logger.error("Target state:")
            logger.error(e.target)
            logger.error("Actual state:")
            logger.error(e.actual)
            execution.set_error_for_round(e.target, e.actual)
            persist_error(execution, e)
            break
        finally:
            docker.remove_container(container)

def print_debug_header(logger: logging.Logger):
    logger.debug("\n\n\n\n")
    logger.debug(text2art("TRIaC"))
    logger.debug("\n\n\n\n")
    logger.debug("Starting new triac run")

def exec_fuzzing(execution: Execution, stop_event: Event):
    logger = logging.getLogger(__name__)

    # Log the beginning of a new session
    print_debug_header(logger)

    # Cache for build base images
    image_cache = {}

    # Execute all the rounds
    while execution.rounds_left() and stop_event.is_set() == False:
        try:
            exec_fuzzing_round(execution, stop_event, image_cache)
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
            logger.error("\n")
            if stop_event.is_set() == False:
                if execution.continue_on_error == False:
                    logger.error("Press any key to continue with the next round...")
                    input()
                else:
                    logger.error("Executing next round")

    if stop_event.is_set() == False:
        logger.info("All rounds executed")

    # Cleanup
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
    if stop_event.is_set():
        logger.info("***** Execution stopped *****")
    else:
        logger.info("***** Execution finished *****")

    time.sleep(1)

def get_differential_options() -> List[str]:
    results : List[str] = []
    targets = [val.name for val in Target]
    # Build all possible pairs
    for first in range(0, len(targets)):
        for second in range(first + 1, len(targets)):
            results.append(f"{targets[first]}:{targets[second]}")
    return results


@click.command()
@click.option(
    "--rounds",
    "-R",
    help="Number of rounds to perform",
    type=click.IntRange(1),
    default=2,
    show_default=True,
)
@click.option(
    "--wrappers-per-round",
    "-W",
    help="The maximum number of wrappers to try in each round before starting the next round",
    type=click.IntRange(1),
    default=10,
    show_default=True,
)
@click.option(
    "--log-level",
    help="The log level to use for the generated log file",
    default="DEBUG",
    show_default=True,
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
)
@click.option(
    "--ui-log-level",
    help="The log level to display in the TRIaC Ui",
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
    '-K',
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
@click.option(
    "--differential",
    '-D',
    help="Enables differential testing between two tools. The tools have to be specified using one of the provided format options.",
    type=click.Choice(get_differential_options()),
)
def fuzz(
    rounds,
    wrappers_per_round,
    log_level,
    ui_log_level,
    base_image,
    keep_base_images,
    continue_on_error,
    differential
):
    """Start a TRIaC fuzzing session"""

    # Generate execution
    state = Execution(
        base_image,
        keep_base_images,
        rounds,
        wrappers_per_round,
        log_level,
        ui_log_level,
        continue_on_error,
    )

    # TODO: Enable replay

    # Stop events
    ui_stop = Event()
    fuzz_stop = Event()

    # Capture STRG+C (interrupts)
    def interrupt_handler(*args):
        fuzz_stop.set()
        logger = logging.getLogger(__name__)
        logger.error("Execution cancellation requested, stopping current execution....")

    signal.signal(signal.SIGINT, interrupt_handler)

    # initialize the UI
    ui = CLILayout(state)

    # Load the wrappers
    state.load_list_of_wrapper_classes()

    # Start the threads to display the UI and computation
    fuzz_worker = Thread(target=exec_fuzzing, args=(state, fuzz_stop))
    ui_worker = Thread(
        target=ui.render_ui,
        args=(
            ui_stop,
            fuzz_stop,
        ),
    )

    fuzz_worker.start()
    ui_worker.start()

    fuzz_worker.join()
    ui_stop.set()  # Set event when the worker finished to close the UI

    ui_worker.join()


if __name__ == "__main__":
    fuzz()
    # TODO: Enable replay
    # TODO: Fix permissions issues (cannot delete folder owned by root)
    sys.exit(0)
