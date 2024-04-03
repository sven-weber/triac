import json
from datetime import datetime
from difflib import ndiff
from os import getcwd
from os.path import join
from pathlib import Path

from deepdiff import DeepDiff
from rich.console import Console

from triac.types.errors import StateMismatchError
from triac.types.execution import Execution
from triac.types.wrapper import State

ERROR_LOCATION = "errors"


def get_path_to_errors() -> str:
    return join(getcwd(), ERROR_LOCATION)


def pretty_print_state(state: State) -> str:
    console = Console(record=True)
    console.print(state)
    return console.export_text(clear=True)

def persist_error(execution: Execution, e: StateMismatchError) -> None:
    folder = get_path_to_errors()
    file_name = datetime.today().strftime("%Y-%m-%d-%H:%M:%S")

    # Ensure the folder exists
    Path(folder).mkdir(parents=True, exist_ok=True)

    # Write encoded wrappers
    encoded_target = join(folder, f"{file_name}.triac")
    with open(encoded_target, "w") as file:
        file.write(execution.encode_wrappers_for_round())

    # Write diff between states in human readable format

    # Pretty print both states
    target_pretty = pretty_print_state(e.target)
    actual_pretty = pretty_print_state(e.actual)

    #Create diff and dump it into the file
    
    human_readable = join(folder, f"{file_name}.json")
    with open(human_readable, "w") as file:
        json.dump(
            {
                "target": target_pretty,
                "actual": actual_pretty,
                "diff": DeepDiff(e.target, e.actual),
            },
            file,
            indent=4,
        )
