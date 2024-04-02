import random
import sys
import time

import click
from art import text2art
from rich.live import Live
from rich.table import Table
from rich.layout import Layout
from rich.panel import Panel
from rich.align import Align
from rich.progress import Progress
from rich.text import Text

from triac.lib.docker.client import DockerClient
from triac.lib.docker.types.base_images import BaseImages
from triac.lib.random import Fuzzer
from triac.types.execution import Execution
from triac.types.target import Target
from triac.values.user import UserType
from threading import Thread

def format_timedelta(td):
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return "{:02}h{:02}m{:02}s".format(hours, minutes, seconds)

def generate_cli_layout(state: Execution) -> Layout:
    # Elements
    logo = Panel(Align.center(text2art("TRIaC"), vertical="middle"))

    # Statistics
    stats_table =  Table(show_header=False, show_lines=False, box=None)
    stats_table.add_column("name")
    stats_table.add_column("value")

    stats_table.add_row("Base Image", str(state.base_image.name))
    stats_table.add_row("Runtime", format_timedelta(state.elapsed_time))
    stats_table.add_row("Rounds", f"{state.round}/{state.total_rounds}")
    stats_table.add_row(Text("Errors", style="bold red"), Text(str(state.errors), style="bold red"))
    statistics = Layout(
       stats_table
    )

    stats = Panel(statistics, title="Statistics")

    # Execution log
    exec_log = Panel("", title="Execution log")

    # Global layout
    layout = Layout()
    layout.split_row(
        Layout(name="left"),
        Layout(exec_log, name="right"),
    )

    # Left
    layout["left"].split_column(Layout(logo, name="logo"), Layout(stats, name="stats"))
    layout["logo"].size = 8

    return layout

def exec_fuzzing(state: Execution):
    while(True):
        state.round += 1
        time.sleep(5)

def update_ui(state: Execution):
    with Live(generate_cli_layout(state), auto_refresh=False) as live:
        while(True):
            live.update(generate_cli_layout(state), refresh=True)
            time.sleep(0.1)

@click.command()
@click.option("--rounds", default=2, help="Number of rounds to perform")
@click.option(
    "--base-image",
    help="The base image to use",
    type=click.Choice([val.name for val in BaseImages]),
)
def fuzz(rounds, base_image):
    """Start a TRIaC fuzzing session"""
    
    # Get the base image
    if (base_image != None):
        print(base_image)
        BaseImages[base_image]
    else:
        base_image = Fuzzer().fuzz_base_image()
    
    # Create new execution
    state = Execution(base_image, rounds)

    # Start the threads to display the UI and computation
    worker = Thread(target=exec_fuzzing, args=(state, ))
    ui = Thread(target=update_ui, args=(state, ))

    worker.start()
    ui.start()

    worker.join()
    ui.join()

if __name__ == "__main__":
    fuzz()
    sys.exit(0)
