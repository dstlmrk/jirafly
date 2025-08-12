from collections import defaultdict
from pathlib import Path
from typing import Any

import typer
from prettytable import PrettyTable
from termcolor import colored

from .jira_service import JiraClient
from .models import MemberPlan
from .team_config import load_team_config
from .utils import (
    format_seconds,
    highlight_exceeding,
    print_general_info,
    print_tasks_by_assignee,
)

app = typer.Typer()


def parse_member_option(values: list[str]) -> dict[str, tuple[float, float]]:
    """Parse member option values from nickname=wd,vel format."""
    result = {}
    for value in values:
        try:
            nickname, rest = value.split("=", 1)
            wd_str, vel_str = rest.split(",", 1)
            wd = float(wd_str)
            vel = float(vel_str)
            result[nickname.strip()] = (wd, vel)
        except ValueError as e:
            raise typer.BadParameter(
                f"Invalid member format '{value}'. Expected: nickname=wd,vel (e.g., peter=7.0,0.3)"
            ) from e
    return result


@app.command()
def planning(
    team: Path = typer.Argument(
        Path("configs/team.yaml"), help="Path to team config YAML file", exists=True
    ),
    jira_url: str = typer.Option(
        ...,
        envvar="JIRA_URL",
        help="JIRA server URL (e.g., https://yourcompany.atlassian.net).",
    ),
    jira_email: str = typer.Option(
        ...,
        envvar="JIRA_EMAIL",
        help="JIRA email address for authentication.",
    ),
    jira_token: str = typer.Option(
        ...,
        envvar="JIRA_TOKEN",
        help="JIRA API token for authentication.",
    ),
    filter_id: str = typer.Option(
        "",
        envvar="PLANNING_FILTER_ID",
        help="JIRA filter ID for planning. Uses PLANNING_FILTER_ID env var if not provided.",
    ),
    member: list[str] = typer.Option(
        None,
        "--member",
        help="Override team member settings. Format: --member nickname=wd,vel (e.g., --member peter=7.0,0.3)",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """Plan sprint with team capacity from YAML configuration."""

    if not filter_id:
        print(
            "Error: filter_id must be provided either as parameter or PLANNING_FILTER_ID environment variable"
        )
        raise typer.Exit(1)

    # Load team configuration and apply overrides
    try:
        team_config = load_team_config(team)

        # Parse member overrides from command line
        parsed_overrides = parse_member_option(member or [])

        # Apply overrides to team configuration
        team_members = team_config.apply_overrides(parsed_overrides)

        print(f"📋 Loaded team from {team}")
        print(f"👥 Team members: {', '.join(team_members.keys())}")

        # Show override summary if any were applied
        override_summary = team_config.get_override_summary(parsed_overrides)
        if override_summary:
            print(override_summary)

    except Exception as e:
        print(f"Error loading team config: {e}")
        raise typer.Exit(1) from e

    # Planning logic
    client = JiraClient(jira_url, jira_email, jira_token)
    tasks = client.fetch_tasks(filter_id)

    tasks_by_assignee = defaultdict(
        lambda: MemberPlan(0, 0),
        {name: MemberPlan(*config) for name, config in team_members.items()},
    )

    for task in tasks:
        tasks_by_assignee[task.assignee].total_hle += task.hle
        tasks_by_assignee[task.assignee].tasks.append(task)

    print_general_info(tasks_by_assignee)
    print_tasks_by_assignee(tasks_by_assignee, verbose)


@app.command()
def ratio(
    jira_url: str = typer.Option(
        ...,
        envvar="JIRA_URL",
        help="JIRA server URL (e.g., https://yourcompany.atlassian.net).",
    ),
    jira_email: str = typer.Option(
        ...,
        envvar="JIRA_EMAIL",
        help="JIRA email address for authentication.",
    ),
    jira_token: str = typer.Option(
        ...,
        envvar="JIRA_TOKEN",
        help="JIRA API token for authentication.",
    ),
    filter_id: str = typer.Option(
        "",
        envvar="RATIO_FILTER_ID",
        help="JIRA filter ID for ratio analysis. Uses RATIO_FILTER_ID env var if not provided.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    if not filter_id:
        print(
            "❌ Error: filter_id must be provided either as parameter or RATIO_FILTER_ID environment variable"
        )
        raise typer.Exit(1)

    tasks: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "ratio": {"Maintenance": 0, "Product": 0, "Excluded": 0},
            "time": {"Maintenance": 0, "Product": 0, "Excluded": 0},
            "tasks": [],
        }
    )

    client = JiraClient(jira_url, jira_email, jira_token)
    for task in client.fetch_tasks(filter_id):
        fix_version = task.fix_version or "No Fix Version"
        tasks[fix_version]["tasks"].append(task)
        tasks[fix_version]["ratio"][task.ratio_type] += task.hle
        tasks[fix_version]["time"][task.ratio_type] += task.time_spent

    sorted_tasks = dict(sorted(tasks.items()))

    table = PrettyTable(align="l")
    table.field_names = [
        "Fix version",
        "Assignee",
        "Task",
        "HLE",
        "Time spent",
        "Status",
    ]

    total_maintenance = total_product = total_excluded = 0
    time_total_maintenance = time_total_product = 0

    for _, (fix_version, data) in enumerate(sorted_tasks.items()):
        maintenance = data["ratio"]["Maintenance"]
        product = data["ratio"]["Product"]
        excluded = data["ratio"]["Excluded"]

        total_maintenance += maintenance
        total_product += product
        total_excluded += excluded

        time_maintenance = data["time"]["Maintenance"]
        time_product = data["time"]["Product"]

        time_total_maintenance += time_maintenance
        time_total_product += time_product
        time_total_spent = 0

        sorted_tasks = sorted(data["tasks"], key=lambda x: x.assignee)
        for j, task in enumerate(sorted_tasks, start=1):
            previous_assignee = sorted_tasks[j - 2].assignee if j > 1 else None

            table.add_row(
                [
                    colored(
                        f" {fix_version} ",
                        color="black",
                        on_color="on_white",
                        attrs=["bold"],
                    )
                    if j == 1
                    else "",
                    task.assignee if task.assignee != previous_assignee else "",
                    (
                        f"{task.colored_title}\n{task.colored_url}"
                        if verbose
                        else task.colored_title
                    ),
                    f"{task.hle:.2f}",
                    colored(format_seconds(task.time_spent), highlight_exceeding(task)),
                    task.status,
                ],
            )
            time_total_spent += task.time_spent

        table.add_divider()

        total = maintenance + product
        time_total = time_maintenance + time_product
        maintenance_str = (
            f"MAINTENANCE: {maintenance:5.2f}"
            f" / {maintenance / total * 100:4.1f} %"
            f" / ⏱ {time_maintenance / time_total * 100:4.1f} %"
        )
        product_str = (
            f"PRODUCT: {product:5.2f}"
            f" / {product / total * 100:4.1f} %"
            f" / ⏱ {time_product / time_total * 100:4.1f} %"
        )

        table.add_row(
            [
                "",
                "",
                colored(f"{maintenance_str}  |  {product_str}", attrs=["bold"]),
                colored(f"{total + excluded:.2f}", attrs=["bold"]),
                format_seconds(time_total_spent),
                "",
            ],
            divider=True,
        )

    _total = total_maintenance + total_product
    _time_total = time_total_maintenance + time_total_product
    maintenance_str = (
        f"MAINTENANCE: {total_maintenance:5.2f}"
        f" / {total_maintenance / _total * 100:4.1f} %"
        f" / ⏱ {time_total_maintenance / _time_total * 100:4.1f} %"
    )
    product_str = (
        f"PRODUCT: {total_product:5.2f}"
        f" / {total_product / _total * 100:4.1f} %"
        f" / ⏱ {time_total_product / _time_total * 100:4.1f} %"
    )

    table.add_row(
        [
            "",
            colored("Total", attrs=["bold"]),
            colored(f"{maintenance_str}  |  {product_str}", attrs=["bold"]),
            f"{_total + total_excluded:.2f}",
            "",
            "",
        ]
    )

    table.align["HLE"] = "r"
    print(table)
