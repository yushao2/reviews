import asyncio
from datetime import datetime
from time import sleep
from typing import List, Tuple

from rich.console import RenderGroup
from rich.live import Live
from rich.panel import Panel

from reviews import config
from reviews.controller import PullRequestController
from reviews.layout import (
    RenderLayoutManager,
    generate_layout,
    generate_log_table,
    generate_progress_tracker,
    generate_tree_layout,
)

logs: List[Tuple[str, str]] = []


def add_log_event(message: str) -> List[Tuple[str, str]]:
    """adds a log event to a list of logs and displays the top 20."""
    global logs

    logs = logs[-20:]
    logs.append(
        (str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), f"[white]{message}")
    )
    return logs


def _render_pull_requests(
    controller: PullRequestController, configuration: List[Tuple[str, str]]
) -> Panel:
    """Renders all pull requests for the provided configuration"""

    tables = [
        controller.retrieve_pull_requests(org=org, repository=repo)
        for (org, repo) in configuration
    ]

    # filter unrenderable `None` results
    return Panel(
        RenderGroup(*[t for t in tables if t]),
        title="Activity",
        border_style="blue",
    )


def single_render() -> None:
    """Renders the Terminal UI Dashboard once before closing the application"""

    configuration = config.get_configuration()
    controller = PullRequestController()

    layout_manager = RenderLayoutManager(layout=generate_layout(footer=False))
    layout_manager.render_layout(
        progress_table=None,
        body=_render_pull_requests(controller=controller, configuration=configuration),
        pull_request_component=generate_tree_layout(configuration=configuration),
        log_component=generate_log_table(logs=logs),
    )

    with Live(
        renderable=layout_manager.layout,
        refresh_per_second=5,
        transient=False,
        screen=False,
    ):
        add_log_event(message="updated")


def render() -> None:
    """Renders Terminal UI Dashboard"""
    (
        job_progress,
        overall_progress,
        overall_task,
        progress_table,
    ) = generate_progress_tracker()

    # initial load should be from database
    add_log_event(message="initializing...")

    configuration = config.get_configuration()
    controller = PullRequestController()

    layout_manager = RenderLayoutManager(layout=generate_layout())
    layout_manager.render_layout(
        progress_table=progress_table,
        body=Panel(
            RenderGroup(),
            title="Activity",
            border_style="blue",
        ),
        pull_request_component=generate_tree_layout(configuration=configuration),
        log_component=generate_log_table(logs=logs),
    )

    with Live(layout_manager.layout, refresh_per_second=5, screen=True):
        while True:
            if not overall_progress or overall_progress.finished:
                (
                    job_progress,
                    overall_progress,
                    overall_task,
                    progress_table,
                ) = generate_progress_tracker()

            add_log_event(message="waiting...")

            # update view (blocking operation)
            layout_manager.render_layout(
                progress_table=progress_table,
                body=_render_pull_requests(
                    controller=controller, configuration=configuration
                ),
                pull_request_component=generate_tree_layout(
                    configuration=configuration
                ),
                log_component=generate_log_table(logs=logs),
            )

            delay = config.DELAY_REFRESH * 0.01
            while not overall_progress.finished:
                sleep(delay)
                for job in job_progress.tasks:
                    if not job.finished:
                        job_progress.advance(job.id)

                completed = sum(task.completed for task in job_progress.tasks)
                overall_progress.update(overall_task, completed=completed)

            add_log_event(message="updated")


async def update() -> None:
    """Updates data in the background."""

    while True:
        print("working")
        await asyncio.sleep(1)
