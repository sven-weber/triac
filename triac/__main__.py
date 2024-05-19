import logging
import signal
import sys
import time
from asyncio import Event
from threading import Thread
from typing import Container, Dict, List, Set

import click
from art import text2art
from deepdiff import DeepDiff

from triac.lib.docker.client import DockerClient
from triac.lib.docker.const import get_base_image_identifiers
from triac.lib.docker.types.base_images import BaseImages
from triac.lib.errors import persist_error
from triac.lib.generator.ansible import Ansible
from triac.lib.generator.pyinfra import PyInfra
from triac.types.errors import (
    ExecutionShouldStopRequestedError,
    StateMismatchError,
    TargetNotSupportedError,
    WrappersExhaustedError,
)
from triac.types.execution import Execution, ExecutionMode
from triac.types.target import Target
from triac.types.wrapper import State, Wrapper
from triac.types.wrappers import Wrappers, load
from triac.ui.cli_layout import CLILayout
from triac.wrappers.systemd import Systemd


def build_base_image(
    docker: DockerClient, execution: Execution, image_cache: Dict[BaseImages, str]
) -> BaseImages:
    # Build the base image or take from cache
    if execution.base_image not in image_cache:
        image = docker.build_base_image(execution.base_image)
        execution.add_image_to_used(image)
        image_cache[execution.base_image] = image

    return image_cache[execution.base_image]


def create_container_for_image(
    docker: DockerClient, image: BaseImages, containers: List[Container]
):
    container = docker.run_container_from_image(image)
    containers.append(container)
    return container


def get_next_wrapper(
    execution: Execution, container: Container, logger: logging.Logger
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
    logger: logging.Logger,
) -> State:
    match target:
        case Target.ANSIBLE:
            logger.info(f"Executing Ansible against target")
            is_state = Ansible(wrapper, target_state, container).run()
        case Target.PYINFRA:
            logger.info(f"Executing pyinfra against target")
            is_state = PyInfra(wrapper, target_state, container).run()
        case _:
            raise TargetNotSupportedError(target)

    logger.debug(f"Got the following actual state:")
    logger.debug(is_state)

    return is_state


def raise_error_when_states_not_equal(
    is_state: State, target_state: State, logger: logging.Logger
):
    if len(DeepDiff(is_state, target_state).affected_root_keys) > 0:
        raise StateMismatchError(target_state, is_state)


def exec_unit_test_with_wrapper(
    target: Target,
    target_state: State,
    container: Container,
    wrapper: Wrapper,
    logger: logging.Logger,
    stop_event: Event,
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
    containers: List[Container],
):
    # Execute first tool against target
    first_state = exec_unit_test_with_wrapper(
        execution.first_differential_target,
        target_state,
        container,
        wrapper,
        logger,
        stop_event,
    )

    # Create second container for second tool
    raise_when_stop_event_set(stop_event)
    second_container = create_container_for_image(docker, image, containers)
    raise_when_stop_event_set(stop_event)
    second_state = exec_unit_test_with_wrapper(
        execution.second_differential_target,
        target_state,
        second_container,
        wrapper,
        logger,
        stop_event,
    )

    # Check the states for equality
    raise_when_stop_event_set(stop_event)
    raise_error_when_states_not_equal(first_state, second_state, logger)


def check_slow_mode(execution: Execution, logger: logging.Logger):
    if execution.slow_mode:
        logger.info("Slow mode enabled. Press Enter to continue with next wrapper...")
        time.sleep(2)  # Hacky UI Update
        input()


def exec_fuzzing_round(
    docker: DockerClient,
    execution: Execution,
    stop_event: Event,
    image_cache: Dict[BaseImages, str],
    containers: List[Container],
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

        execute_wrapper(
            execution,
            docker,
            target_state,
            container,
            containers,
            wrapper,
            logger,
            stop_event,
        )

        # Check slow mode
        check_slow_mode(execution, logger)

        # Remove containers
        remove_containers(docker, containers)


def print_debug_header(logger: logging.Logger):
    logger.debug(f"\n{text2art('TRIaC')}")
    logger.debug("Starting new triac run")


def remove_containers(docker: DockerClient, containers: List[Container]):
    for container in containers:
        docker.remove_container(container)
    containers.clear()


def cleanup_images(docker: DockerClient, logger: logging.Logger, images: List[str]):
    for image in images:
        logger.debug(f"Removing image {image}")
        docker.remove_image(image)


def perform_cleanup(execution: Execution, logger: logging.Logger, docker: DockerClient):
    logger.info("Cleaning up resources")
    logger.debug("The following images where used during execution:")
    logger.debug(execution.used_docker_images)
    to_remove = filter(
        lambda elem: elem not in get_base_image_identifiers()
        or not execution.keep_base_images,
        execution.used_docker_images,
    )
    cleanup_images(docker, logger, to_remove)


def get_execution_for_replay(
    replay_file: str,
    keep_base_images: bool,
    log_level: str,
    ui_log_level: str,
) -> Execution:
    # Parse replay file
    try:
        to_replay = load(replay_file)
    except Exception as e:
        print(
            "Error: Could not parse the provided replay file",
            file=sys.stderr,
        )
        sys.exit(1)

    return Execution(
        to_replay.base_image.name,
        keep_base_images,
        1,
        to_replay.count,
        log_level,
        ui_log_level,
        False,
        False,
        to_replay.unit,
        to_replay.differential,
        replay_wrappers=to_replay,
    )


def execute_wrapper(
    execution: Execution,
    docker: DockerClient,
    target_state: State,
    container: Container,
    containers: List[Container],
    wrapper: Wrapper,
    logger: logging.Logger,
    stop_event=Event,
):
    if execution.mode == ExecutionMode.UNIT:
        # Unit test
        exec_unit_test_with_wrapper(
            execution.unit_target,
            target_state,
            container,
            wrapper,
            logger,
            stop_event,
        )
        logger.info(f"Target state reached, wrapper finished")
    else:
        # Differential test
        exec_differential_test_with_wrapper(
            execution,
            target_state,
            container,
            wrapper,
            logger,
            stop_event,
            docker,
            image,
            containers,
        )
        logger.info("Target state reached by all targets, wrapper finished")

    # Commit container for next round
    image = docker.commit_container_to_image(container)
    execution.add_intermediate_image_to_used(image)


def exec_replay(execution: Execution, stop_event: Event):
    logger = logging.getLogger(__name__)
    image_cache = {}
    containers: List[Container] = []
    print_debug_header(logger)

    execution.start_new_round()
    logger.info(f"***** Starting replay on image {execution.base_image.name} *****")

    try:
        # Initialize docker client
        docker = DockerClient()

        # Build base image
        image = build_base_image(docker, execution, image_cache)
        raise_when_stop_event_set(stop_event)

        # Replace the wrappers wrappers
        for identifier, target_state in execution.replay_wrappers.target_states:
            raise_when_stop_event_set(stop_event)
            logger.info(
                f"---- Executing wrapper #{execution.num_wrappers_in_round + 1}"
            )

            container = create_container_for_image(docker, image, containers)
            raise_when_stop_event_set(stop_event)

            # Instantiate wrapper
            wrapper = execution.get_wrapper_by_name(identifier.name)
            if wrapper == None:
                raise Exception(
                    f"No wrapper with the name {identifier.name} could be found for replay"
                )
            execution.add_wrapper_and_state_to_round(wrapper, target_state)
            raise_when_stop_event_set(stop_event)

            execute_wrapper(
                execution,
                docker,
                target_state,
                container,
                containers,
                wrapper,
                logger,
                stop_event,
            )

            logger.info("Press Enter to continue with next wrapper...")
            time.sleep(2)  # Hacky UI Update
            input()

            # Remove containers
            remove_containers(docker, containers)
    except ExecutionShouldStopRequestedError as e:
        # Do nothing, the method failed because the execution should stop
        pass
    except StateMismatchError as e:
        logger.error("Found mismatch between target and actual state")
        logger.error("Target state:")
        logger.error(e.target)
        logger.error("Actual state:")
        logger.error(e.actual)
        execution.set_error_for_round(e.target, e.actual)

        logger.info("Press Enter to finish execution")
        time.sleep(2)  # Hacky UI Update
        input()
    except Exception as e:
        logger.error("Encountered unexpected error during replay:")
        logger.exception(e)
        return
    finally:
        # Remove containers
        remove_containers(docker, containers)
        # Cleanup all intermediate images
        cleanup_images(docker, logger, execution.used_intermediate_images)
        execution.reset_intermediate_images()
        # Cleanup the base images
        perform_cleanup(execution, logger, docker)


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
        containers = []  # Container to cleanup
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
            check_slow_mode(execution, logger)
        except ExecutionShouldStopRequestedError as e:
            # Do nothing, the method failed because the execution should stop
            pass
        except Exception as e:
            logger.error("Encountered unexpected error during execution of round:")
            logger.exception(e)
            logger.error("\n")
            if stop_event.is_set() == False:
                if execution.continue_on_error == False:
                    logger.error("Press Enter to continue with the next round...")
                    input()
                else:
                    logger.error("Executing next round")
        finally:
            # Remove container that have not been removed
            remove_containers(docker, containers)
            # Cleanup all intermediate images
            cleanup_images(docker, logger, execution.used_intermediate_images)
            execution.reset_intermediate_images()

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
    results: List[str] = []
    targets = [val.name for val in Target]
    # Build all possible pairs
    for first in range(0, len(targets)):
        for second in range(first + 1, len(targets)):
            results.append(f"{targets[first]}:{targets[second]}")
    return results


def validate_options(unit: Target, differential: str, replay: str):
    if unit != None and differential != None:
        print(
            "Error: You cannot enable differential and unit testing at the same time",
            file=sys.stderr,
        )
        sys.exit(1)
    elif unit == None and differential == None and replay == None:
        print(
            "Error: You have to enable either unit or differential testing or a replay session",
            file=sys.stderr,
        )
        sys.exit(1)
    elif replay != None and replay.endswith(".triac") == False:
        print(
            "Error: If you want to replay an error, please supply a '.triac' file",
            file=sys.stderr,
        )
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
    "-B",
    help="The base image to use. If not specified, one is chosen randomly each round",
    type=click.Choice([val.name for val in BaseImages]),
)
@click.option(
    "--keep-base-images",
    "-K",
    help="Whether the base images that where build during the execution should be kept. This will increase the speed of future executions.",
    is_flag=True,
    default=False,
    show_default=True,
)
@click.option(
    "--continue-on-error",
    "-C",
    help="Whether triac should automatically continue with the execution of the next round whenever a unexpected error is encountered.",
    is_flag=True,
    default=False,
    show_default=True,
)
@click.option(
    "--slow-mode",
    "-S",
    help="Enables a slow mode. This means that triac pauses after each wrapper execution and waits for user input to continue. This can be very helpful for debugging or demos",
    is_flag=True,
    default=False,
    show_default=True,
)
@click.option(
    "--unit",
    "-U",
    help="Enables unit testing a specific tool. By default, Ansible wll be tested. This option cannot be supplied while performing differential testing.",
    type=click.Choice([val.name for val in Target]),
)
@click.option(
    "--differential",
    "-D",
    help="Enables differential testing between two tools. The tools have to be specified using one of the provided format options.",
    type=click.Choice(get_differential_options()),
)
@click.option(
    "--replay",
    help="This enables a replay. In this mode, TRIaC DOES NOT FUZZ but replays a previously found error from the /errors folder. When this option is supplied, only the log levels will be taken into account.",
    type=click.Path(
        exists=True, dir_okay=False, file_okay=True, readable=True, resolve_path=True
    ),
)
def fuzz(
    rounds,
    wrappers_per_round,
    log_level,
    ui_log_level,
    base_image,
    keep_base_images,
    continue_on_error,
    slow_mode,
    unit,
    differential,
    replay,
):
    """Start a TRIaC fuzzing or replay session"""
    validate_options(unit, differential, replay)

    if replay != None:
        state = get_execution_for_replay(
            replay, keep_base_images, log_level, ui_log_level
        )
        thread_target = exec_replay
    else:
        # Generate execution
        state = Execution(
            base_image,
            keep_base_images,
            rounds,
            wrappers_per_round,
            log_level,
            ui_log_level,
            continue_on_error,
            slow_mode,
            unit,
            differential,
        )
        thread_target = exec_fuzzing

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
    fuzz_worker = Thread(target=thread_target, args=(state, fuzz_stop))
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
    sys.exit(0)
