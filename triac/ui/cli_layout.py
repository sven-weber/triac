import logging
import time
from asyncio import Event
from typing import Optional, Union

from art import text2art
from rich import box
from rich.align import Align
from rich.console import Console
from rich.containers import Lines
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.pretty import Pretty
from rich.table import Table
from rich.text import Text

from triac.types.execution import Execution, ExecutionMode
from triac.ui.log_filter import build_log_filter
from triac.ui.log_handler import UILoggingHandler


class VerticalOverflowText(Text):
    """
    Custom text element that shows the text tail when the text is overflowed
    """

    def wrap(
        self,
        console: "Console",
        width: int,
        *,
        justify: Optional["JustifyMethod"] = None,
        overflow: Optional["OverflowMethod"] = None,
        tab_size: int = 8,
        no_wrap: Optional[bool] = None,
    ) -> Lines:
        # Call sub wrapped
        # When we pass along the parameters this
        # Crashes sometimes. And it seems to be working
        # fine without passing them along so.
        wrapped = super().wrap(console, width)

        # If there are too many lines, show the tail
        if console.height < len(wrapped):
            return [Text("...")] + wrapped[len(wrapped) - console.height - 1 :]
        else:
            return wrapped


class CLILayout:

    def __init__(self, state: Execution):
        self.__state = state

        # Fixed UI elements
        self.__logo = Panel(Align.center(text2art("TRIaC"), vertical="middle"))
        self.__log_output = VerticalOverflowText()

        #Setup logging
        self.__configure_logging(state)
        

    def __configure_logging(self, state: Execution):
        # Enable log capturing
        log_filter = build_log_filter(False, [__name__.split(".")[0], "__main__"])

        # UI Logger
        ui_handler = UILoggingHandler(self.__log_output)
        ui_handler.setFormatter(
            logging.Formatter(
                fmt='%(message)s\n'
            )
        )
        ui_handler.setLevel(state.ui_log_level)
        ui_handler.addFilter(log_filter)

        # File Handler
        file_handler = logging.FileHandler("triac.log")
        file_handler.setLevel(state.log_level)
        file_handler.setFormatter(
            logging.Formatter(
                fmt='%(asctime)s - %(name)s :: %(levelname)-8s :: %(message)s',
                datefmt='[%Y-%m-%d %H:%M:%S]'
            )
        )
        file_handler.addFilter(log_filter)

        # Configure the two loggers
        logging.basicConfig(
            level=state.log_level,
            handlers=[ui_handler, file_handler],
        )

    def format_timedelta(self):
        hours, remainder = divmod(self.__state.elapsed_time.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return "{:02}h{:02}m{:02}s".format(hours, minutes, seconds)

    def generate_cli_layout(
        self, execution_finished: bool, execution_canceled: bool
    ) -> Layout:
        # Statistics

        # First table
        stats_table_1 = Table(show_header=False, show_lines=False, box=None)
        stats_table_1.add_column("name")
        stats_table_1.add_column("value")

        stats_table_1.add_row("Runtime", self.format_timedelta())
        stats_table_1.add_row(
            "Wrapper",
            f"{self.__state.num_wrappers_in_round}/{self.__state.wrappers_per_round}",
        )
        stats_table_1.add_row(
            "Round", f"{self.__state.round}/{self.__state.total_rounds}"
        )
        stats_table_1.add_row(
            "Mode", f"{self.__state.mode().name}"
        )

        stats_table_2 = Table(show_header=False, show_lines=False, box=None)
        stats_table_2.add_column("name")
        stats_table_2.add_column("value")
        stats_table_2.add_row(
            Text("Errors", style="bold red"),
            Text(str(self.__state.errors), style="bold red"),
        )
        stats_table_2.add_row("Log Level", str(self.__state.ui_log_level))
        stats_table_2.add_row(
            "Base Image",
            (
                ""
                if self.__state.base_image is None
                else str(self.__state.base_image.name)
            ),
        )
        stats_table_2.add_row(
            "Target",
            (
                self.__state.unit_target.name if self.__state.mode() == ExecutionMode.UNIT
                else self.__state.formatted_diff_target
            ),
        )
        # Second table
        statistics = Layout()
        statistics.split_row(
            Layout(Align.center(stats_table_1, vertical="middle")),
            Layout(Align.center(stats_table_2, vertical="middle")),
        )

        stats = Panel(statistics, title="Statistics")

        # Status
        if execution_canceled:
            status_text = Text("CANCELED", style="bold yellow")
        elif execution_finished:
            status_text = Text("FINISHED", style="bold dark_green")
        else:
            status_text = Text("RUNNING", style="bold dark_orange")

        status = Panel(
            Align.center(status_text, vertical="middle"),
            title="Status",
        )

        # Wrappers
        wrappers_table = Table(
            show_header=True, show_lines=True, expand=True, box=box.MINIMAL
        )
        wrappers_table.add_column(
            "#", width=2, max_width=2, min_width=2, justify="left", no_wrap=True
        )
        wrappers_table.add_column("Name", width=6, max_width=6, min_width=6)
        wrappers_table.add_column("Target state")

        states = self.__state.target_states
        for i, wrapper in enumerate(reversed(states)):
            wrappers_table.add_row(
                f"{len(states) - i}",
                Pretty(wrapper[0]),
                Pretty(wrapper[1], expand_all=True),
            )

        wrappers = Panel(wrappers_table)

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
            Layout(self.__logo, name="logo"),
            Layout(stats, name="stats"),
            Layout(status, name="status"),
            Layout(wrappers, name="wrappers"),
        )

        layout["logo"].size = 8
        layout["stats"].size = 6
        layout["status"].size = 3

        # Right
        # layout["right"].ratio = 2

        return layout

    def render_ui(self, stop_event: Event, canceled_event: Event):
        # Generate the fixed parts
        with Live(
            self.generate_cli_layout(stop_event.is_set(), canceled_event.is_set()),
            auto_refresh=False,
        ) as live:
            while True:
                # Refresh the UI layout
                live.update(
                    self.generate_cli_layout(
                        stop_event.is_set(), canceled_event.is_set()
                    ),
                    refresh=True,
                )

                # Stop if cancellation is requested
                if stop_event.is_set():
                    break

                time.sleep(0.5)
