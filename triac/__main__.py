import logging
import signal
import sys
import time
from asyncio import Event
from threading import Thread
from typing import Container, Dict, List
from art import text2art

import click
from deepdiff import DeepDiff

from triac.lib.docker.client import DockerClient
from triac.lib.docker.const import get_base_image_identifiers
from triac.lib.docker.types.base_images import BaseImages
from triac.lib.errors import persist_error
from triac.lib.generator.ansible import Ansible
from triac.types.errors import ExecutionShouldStopRequestedError, StateMismatchError, TargetNotSupportedError, WrappersExhaustedError
from triac.types.execution import Execution, ExecutionMode
from triac.types.target import Target
from triac.types.wrapper import State, Wrapper
from triac.ui.cli_layout import CLILayout


def build_base_image(
        docker: DockerClient,
        execution: Execution, 
        image_cache: Dict[BaseImages, str]
) -> BaseImages:
    # Build the base image or take from cache
    if execution.base_image not in image_cache:
        image = docker.build_base_image(execution.base_image)
        execution.add_image_to_used(image)
        image_cache[execution.base_image] = image

    return image_cache[execution.base_image]

def create_container_for_image(
        docker: DockerClient, image: BaseImages,
        containers: List[Container]
):
    container = docker.run_container_from_image(image)
    containers.append(container)
    return container

def get_next_wrapper(
        execution: Execution,
        container: Container,
        logger: logging.Logger
):
    try:
        return execution.get_next_wrapper(container)
    except WrappersExhaustedError as e:
        logger.error("There are no wrappers that can run in the reached state")
        raise e

def raise_when_stop_event_set(stop_event: Event):
    if stop_event.is_set():
        raise ExecutionShouldStopRequestedError()

def execute_against_target(
    target: Target,
    target_state: State,
    container: Container,
    wrapper: Wrapper,
    logger: logging.Logger
) -> State:
    match target:
        case Target.ANSIBLE:
            logger.info(f"Executing Ansible against target")
            is_state = Ansible(wrapper, target_state, container).run()
        case Target.PYINFRA:
            #TODO: Change to actual pyinfra
            logger.info(f"Executing pyinfra against target")
            is_state = Ansible(wrapper, target_state, container).run()
        case _:
            raise TargetNotSupportedError(target)
        
    logger.debug(f"Got the following actual state:")
    logger.debug(is_state)

    return is_state

def raise_error_when_states_not_equal(is_state: State, target_state: State, logger: logging.Logger):
    if len(DeepDiff(is_state, target_state).affected_root_keys) > 0:
        raise StateMismatchError(target_state, is_state)

def exec_unit_test_with_wrapper(
    target: Target,
    target_state: State,
    container: Container,
    wrapper: Wrapper,
    logger: logging.Logger,
    stop_event: Event
) -> State:
    # Execute against the target
    is_state = execute_against_target(target, target_state, container, wrapper, logger)
    raise_when_stop_event_set(stop_event)

    # Check states for equality
    raise_error_when_states_not_equal(is_state, target_state, logger)
    raise_when_stop_event_set(stop_event)

    return is_state

def exec_differential_test_with_wrapper(
    execution: Execution,
    target_state: State,
    container: Container,
    wrapper: Wrapper,
    logger: logging.Logger,
    stop_event: Event,
    docker: DockerClient,
    image: BaseImages,
    containers: List[Container]
):
    # Execute first tool against target
    first_state = exec_unit_test_with_wrapper(
        execution.first_differential_target, target_state, container,
        wrapper, logger, stop_event
    )
    
    # Create second container for second tool
    raise_when_stop_event_set(stop_event)
    second_container = create_container_for_image(docker, image, containers)
    raise_when_stop_event_set(stop_event)
    second_state = exec_unit_test_with_wrapper(
        execution.second_differential_target, target_state, second_container,
        wrapper, logger, stop_event
    )

    # Check the states for equality
    raise_when_stop_event_set(stop_event)
    raise_error_when_states_not_equal(first_state, second_state, logger)


def exec_fuzzing_round(
    docker: DockerClient, execution: Execution,
    stop_event: Event, image_cache: Dict[BaseImages, str],
    containers: List[Container]
):
    # Start new round
    execution.start_new_round()
    logger = logging.getLogger(__name__)
    logger.info(
        f"***** Starting fuzzing round {execution.round} on image {execution.base_image.name} *****"
    )

    # Build base image
    image = build_base_image(docker, execution, image_cache)
    raise_when_stop_event_set(stop_event)

    # Main execution loop
    while execution.wrappers_left_in_round():
        raise_when_stop_event_set(stop_event)
        logger.info(f"---- Executing wrapper #{execution.num_wrappers_in_round + 1}")

        container = create_container_for_image(docker, image, containers)
        raise_when_stop_event_set(stop_event)

        # Randomly choose next wrapper and get target state
        wrapper = get_next_wrapper(execution, container, logger)
        target_state = execution.add_wrapper_to_round(wrapper, container)
        raise_when_stop_event_set(stop_event)

        if execution.mode == ExecutionMode.UNIT:
            # Unit test
            exec_unit_test_with_wrapper(
                execution.unit_target, target_state, container,
                wrapper, logger, stop_event
            )
            logger.info(f"Target state reached, wrapper finished")
        else:
            # Differential test
            exec_differential_test_with_wrapper(
                execution, target_state, container,
                wrapper, logger, stop_event,
                docker, image, containers
            )
            logger.info("Target state reached by all targets, wrapper finished")

        # Commit container for next round
        image = docker.commit_container_to_image(container)
        execution.add_image_to_used(image)

def print_debug_header(logger: logging.Logger):
    logger.debug("\n\n\n\n")
    logger.debug(text2art("TRIaC"))
    logger.debug("\n\n\n\n")
    logger.debug("Starting new triac run")

def perform_cleanup(
        execution: Execution,
        logger: logging.Logger,
        docker: DockerClient
):
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
        docker.remove_image(image)

def exec_fuzzing(execution: Execution, stop_event: Event):
    logger = logging.getLogger(__name__)
    image_cache = {}
    print_debug_header(logger)

    # Initialize docker client
    try:
        docker = DockerClient()
    except Exception as e:
        logger.error("Could not initialize docker client:")
        logger.exception(e)
        return

    # Execute all the rounds
    while execution.rounds_left() and stop_event.is_set() == False:
        containers = [] # Container to cleanup
        try:
            exec_fuzzing_round(docker, execution, stop_event, image_cache, containers)
        except StateMismatchError as e:
            logger.error("Found mismatch between target and actual state")
            logger.error("Target state:")
            logger.error(e.target)
            logger.error("Actual state:")
            logger.error(e.actual)
            execution.set_error_for_round(e.target, e.actual)
            persist_error(execution, e)
        except ExecutionShouldStopRequestedError as e:
            # Do nothing, the method failed because the execution should stop
            pass
        except Exception as e:
            logger.error("Encountered unexpected error during execution of round:")
            logger.exception(e)
            logger.error("\n")
            if stop_event.is_set() == False:
                if execution.continue_on_error == False:
                    logger.error("Press any key to continue with the next round...")
                    input()
                else:
                    logger.error("Executing next round")
        finally:
            for container in containers:
                docker.remove_container(container)

    if stop_event.is_set() == False:
        logger.info("All rounds executed")

    # Cleanup
    perform_cleanup(execution, logger, docker)

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

def validate_options(unit: Target, differential: str):
    if unit != None and differential != None:
        print("Error: You cannot enable differential and unit testing at the same time", file=sys.stderr)
        sys.exit(1)
    elif unit == None and differential == None:
        print("Error: You have to enable either unit or differential testing", file=sys.stderr)
        sys.exit(1)

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
    "--unit",
    "-U",
    help="Enables unit testing a specific tool. By default, Ansible wll be tested. This option cannot be supplied while performing differential testing.",
    type=click.Choice([val.name for val in Target])
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
    unit,
    differential
):
    """Start a TRIaC fuzzing session"""
    validate_options(unit, differential)

    # Generate execution
    state = Execution(
        base_image,
        keep_base_images,
        rounds,
        wrappers_per_round,
        log_level,
        ui_log_level,
        continue_on_error,
        unit,
        differential
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
    sys.exit(0)
