import logging
import time

from art import text2art
from rich.align import Align
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from triac.types.execution import Execution
from triac.ui.log_handler import UILoggingHandler


class CLILayout:

    def __init__(self, state: Execution):
        self.__state = state

        # Fixed UI elements
        self.__logo = Panel(Align.center(text2art("TRIaC"), vertical="middle"))
        self.__log_output = Text()

        # Enable log capturing
        logging.basicConfig(
            level=state.log_level,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[UILoggingHandler(self.__log_output, False)],
        )

    def format_timedelta(self):
        hours, remainder = divmod(self.__state.elapsed_time.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return "{:02}h{:02}m{:02}s".format(hours, minutes, seconds)

    def generate_cli_layout(self) -> Layout:
        # Statistics
        stats_table = Table(show_header=False, show_lines=False, box=None)
        stats_table.add_column("name")
        stats_table.add_column("value")

        stats_table.add_row("Base Image", str(self.__state.base_image.name))
        stats_table.add_row("Runtime", self.format_timedelta())
        stats_table.add_row(
            "Rounds", f"{self.__state.round}/{self.__state.total_rounds}"
        )
        stats_table.add_row(
            Text("Errors", style="bold red"),
            Text(str(self.__state.errors), style="bold red"),
        )
        stats_table.add_row(
            Text("Log Level"),
            Text(str(self.__state.log_level))
        )
        statistics = Layout(stats_table)

        stats = Panel(statistics, title="Statistics")

        # Execution log
        exec_log = Panel(self.__log_output, title="Execution log")

        # Global layout
        layout = Layout()
        layout.split_row(
            Layout(name="left"),
            Layout(exec_log, name="right"),
        )

        # Left
        layout["left"].split_column(
            Layout(self.__logo, name="logo"), Layout(stats, name="stats")
        )
        layout["logo"].size = 8

        return layout

    def render_ui(self):
        # Generate the fixed parts
        with Live(self.generate_cli_layout(), auto_refresh=False) as live:
            while True:
                # Refresh the UI layout
                live.update(self.generate_cli_layout(), refresh=True)
                time.sleep(0.1)
