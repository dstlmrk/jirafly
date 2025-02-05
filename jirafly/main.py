import os
from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Annotated

import typer
from dotenv import load_dotenv
from jira import JIRA
from prettytable import PrettyTable
from termcolor import colored

app = typer.Typer()
load_dotenv()

JIRA_URL = os.getenv("JIRA_URL")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_TOKEN = os.getenv("JIRA_TOKEN")
RATIO_FILTER_ID = os.getenv("RATIO_FILTER_ID")
PLANNING_FILTER_ID = os.getenv("PLANNING_FILTER_ID")
CUSTOM_FIELD_HLE = "customfield_11605"
CUSTOM_FIELD_WSJF = "customfield_11737"
UNASSIGNED = "Unassigned"


class Task:
    def __init__(self, issue):
        self.assignee: str = (
            issue.fields.assignee.displayName.split()[0]
            if issue.fields.assignee
            else UNASSIGNED
        )
        self._key: str = issue.key
        self._title: str = issue.fields.summary
        self.type: str = issue.fields.issuetype.name
        self._status: str = issue.fields.status
        self.hle: float = getattr(issue.fields, CUSTOM_FIELD_HLE, 0) or 0
        self.wsjf: float = int(getattr(issue.fields, CUSTOM_FIELD_WSJF, 0) or 0)

        if any(
            (
                "RatioExcluded" in issue.fields.labels,
                "Bughunting" in issue.fields.labels,
            )
        ):
            self.ratio_type = "Excluded"
        elif any(
            (
                "Maintenance" in issue.fields.labels,
                "DevOps" in issue.fields.labels,
            )
        ):
            self.ratio_type = "Maintenance"
        else:
            self.ratio_type = "Product"

        self.fix_version = sorted(
            issue.fields.fixVersions, key=lambda x: x.name, reverse=True
        )[0].name[:4]

    @property
    def colored_title(self):
        color, title = None, f"{self._key}: {self._title[:80]}"
        if self.ratio_type == "Product":
            color = "green"
        elif self.ratio_type == "Excluded":
            color = "light_magenta"
        return f"{self.colored_type} {colored(title, color)}"

    @property
    def colored_url(self):
        url = f"https://mallpay.atlassian.net/browse/{self._key}"
        return colored(url, "dark_grey")

    @property
    def colored_type(self):
        color = on_color = None
        if self.type == "Bug":
            on_color = "on_red"
        elif self.type == "Analysis":
            color, on_color = "black", "on_light_grey"
        return colored(f"[{self.type[:1]}]", color, on_color, attrs=["bold"])

    @property
    def status(self):
        status = "TA review" if self._status.id == "10902" else self._status
        if self._status.id != "1":
            status = colored(status, "yellow")
        return status


@dataclass
class MemberPlan:
    wd: float  # work days
    vel: float  # velocity
    tasks: list[Task] = field(default_factory=list)
    total_hle: float = 0


class JiraClient:
    def __init__(self, email, token):
        print("Establishing Jira connection...")
        self.jira = JIRA(JIRA_URL, basic_auth=(email, token))

    def fetch_tasks(self, filter_id: str, limit: int = 1000) -> list[Task]:
        print(f"Fetching (max {limit}) tasks...")
        issues = self.jira.search_issues(f"filter={filter_id}", maxResults=limit)
        tasks = []
        for issue in issues:
            if issue.fields.issuetype.name != "Epic":
                tasks.append(Task(issue))
        return tasks


def _print_general_info(tasks_by_assignee):
    team_capacity = sum(
        (member.wd * member.vel) for member in tasks_by_assignee.values()
    )

    # Ratio
    hle = Counter()
    for plan in tasks_by_assignee.values():
        for task in plan.tasks:
            hle[task.ratio_type] += task.hle
    total = hle["Maintenance"] + hle["Product"]

    # Sprint goal
    sprint_goal = 0
    for member, data in tasks_by_assignee.items():
        if member != UNASSIGNED:
            sprint_goal += sum(task.wsjf for task in data.tasks)

    table = PrettyTable(header=False, align="l")

    table.add_row(
        [
            "MAINTENANCE",
            f"{hle['Maintenance']:.2f} MD {hle['Maintenance'] / total * 100:.2f} %",
        ]
    )
    table.add_row(
        ["PRODUCT", f"{hle['Product']:.2f} MD {hle['Product'] / total * 100:.2f} %"],
        divider=True,
    )
    table.add_row(["TOTAL", f"{sum(hle.values()):.2f} MD"])
    table.add_row(["TEAM CAPACITY", f"{team_capacity:.2f} MD"], divider=True)
    table.add_row(["SPRINT GOAL", f"{sprint_goal} WSJF"])
    print()
    print(table)


def _print_tasks_by_assignee(tasks_by_assignee, verbose):
    sorted_tasks_by_assignee = {
        k: tasks_by_assignee[k]
        for k in sorted(tasks_by_assignee.keys())
        if k != UNASSIGNED
    }
    sorted_tasks_by_assignee[UNASSIGNED] = tasks_by_assignee[UNASSIGNED]

    def get_task_detail(task_):
        return (
            f"{task_.hle:.2f}",
            f"{task_.colored_title}\n{task_.colored_url}"
            if verbose
            else task_.colored_title,
            f"{task_.wsjf or ''}",
            task_.status,
        )

    table = PrettyTable()
    table.field_names = ["Asg.", "Total", "Cap.", "HLE", "Task", "WSJF", "Status"]

    for user, data in sorted_tasks_by_assignee.items():
        capacity = data.wd * data.vel

        if data.tasks:
            table.add_row(
                [
                    user,
                    f"{data.total_hle:.2f}",
                    f"{capacity:.2f}",
                    *get_task_detail(data.tasks[0]),
                ],
                divider=len(data.tasks) == 1,
            )
            # Single tasks
            for idx, task in enumerate(data.tasks[1:]):
                is_last_task = idx == len(data.tasks) - 2
                table.add_row(
                    ["", "", "", *get_task_detail(task)], divider=is_last_task
                )

    table.align = "l"
    table.align["Tol. HLE"] = "r"
    table.align["Cap."] = "r"
    table.align["WSJF"] = "r"
    table.align["HLE"] = "r"
    print(table)


@app.command()
def planning(
    marek: Annotated[tuple[float, float], typer.Option("--marek")],
    ondra: Annotated[tuple[float, float], typer.Option("--ondra")],
    pavel: Annotated[tuple[float, float], typer.Option("--pavel")],
    filter_id: str = PLANNING_FILTER_ID,
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
):
    client = JiraClient(JIRA_EMAIL, JIRA_TOKEN)
    tasks = client.fetch_tasks(filter_id)

    members = {
        "Marek": MemberPlan(*marek),
        "Pavel": MemberPlan(*pavel),
        "Ondřej": MemberPlan(*ondra),
    }
    tasks_by_assignee = {**members, UNASSIGNED: MemberPlan(0, 0)}

    for task in tasks:
        tasks_by_assignee[task.assignee].total_hle += task.hle
        tasks_by_assignee[task.assignee].tasks.append(task)

    _print_general_info(tasks_by_assignee)
    _print_tasks_by_assignee(tasks_by_assignee, verbose)


@app.command()
def ratio(
    filter_id: str = RATIO_FILTER_ID,
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
):
    tasks = defaultdict(
        lambda: deepcopy(
            {
                "ratio": {"Maintenance": 0, "Product": 0, "Excluded": 0},
                "tasks": [],
            }
        )
    )

    client = JiraClient(JIRA_EMAIL, JIRA_TOKEN)
    for task in client.fetch_tasks(filter_id):
        tasks[task.fix_version]["tasks"].append(task)
        tasks[task.fix_version]["ratio"][task.ratio_type] += task.hle

    sorted_tasks = dict(sorted(tasks.items()))

    table = PrettyTable(align="l")
    table.field_names = ["Fix version", "Task", "HLE"]

    total_maintenance = 0
    total_product = 0
    total_excluded = 0

    for idx, (fix_version, data) in enumerate(sorted_tasks.items()):
        total_maintenance += (maintenance := data["ratio"]["Maintenance"])
        total_product += (product := data["ratio"]["Product"])
        total_excluded += (excluded := data["ratio"]["Excluded"])

        tasks_count = len(data["tasks"])
        for j, task in enumerate(data["tasks"], start=1):
            table.add_row(
                [
                    colored(fix_version, attrs=["bold"]) if j == 1 else "",
                    f"{task.colored_title}\n{task.colored_url}"
                    if verbose
                    else task.colored_title,
                    f"{task.hle:.2f}",
                ],
                divider=True if j == tasks_count else False,
            )

        total = maintenance + product
        maintenance_str = (
            f"MAINTENANCE: {maintenance:5.2f} / {maintenance / total * 100:4.1f} %"
        )
        product_str = f"PRODUCT: {product:5.2f} / {product / total * 100:4.1f} %"

        table.add_row(
            [
                "",
                colored(f"{maintenance_str}  |  {product_str}", attrs=["bold"]),
                colored(f"{total + excluded:.2f}", attrs=["bold"]),
            ],
            divider=True,
        )

    _total = total_maintenance + total_product
    maintenance_str = f"MAINTENANCE: {total_maintenance:5.2f} / {total_maintenance / _total * 100:4.1f} %"
    product_str = (
        f"PRODUCT: {total_product:5.2f} / {total_product / _total * 100:4.1f} %"
    )

    table.add_row(
        [
            colored("Total", attrs=["bold"]),
            colored(f"{maintenance_str}  |  {product_str}", attrs=["bold"]),
            f"{_total + total_excluded:.2f}",
        ]
    )

    table.align["HLE"] = "r"
    print(table)


if __name__ == "__main__":
    app()
