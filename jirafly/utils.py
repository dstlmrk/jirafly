from prettytable import PrettyTable

from .jira_service import UNASSIGNED
from .models import MemberPlan, Task


def format_seconds(seconds):
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")

    return " ".join(parts)


def highlight_exceeding(task: Task) -> str | None:
    if task.time_spent > (task.hle * 8 * 3600) * 3:
        return "red"
    elif task.time_spent > (task.hle * 8 * 3600) * 2:
        return "yellow"
    else:
        return None


def print_general_info(tasks_by_assignee: dict[str, MemberPlan]):
    team_capacity = sum(
        (member.wd * member.vel) for member in tasks_by_assignee.values()
    )

    # Ratio
    hle: dict[str, float] = {"Maintenance": 0.0, "Product": 0.0, "Excluded": 0.0}
    for plan in tasks_by_assignee.values():
        for task in plan.tasks:
            hle[task.ratio_type] += task.hle
    total = hle["Maintenance"] + hle["Product"]

    # Sprint goal
    sprint_goal = 0.0
    for member, data in tasks_by_assignee.items():
        if member != UNASSIGNED:
            sprint_goal += sum(task.wsjf for task in data.tasks)

    table = PrettyTable(header=False, align="l")

    table.add_row(
        [
            "MAINTENANCE",
            f"{hle['Maintenance']:.2f} MD {hle['Maintenance'] / total * 100:5.2f} %",
        ]
    )
    table.add_row(
        ["PRODUCT", f"{hle['Product']:.2f} MD {hle['Product'] / total * 100:5.2f} %"],
        divider=True,
    )
    table.add_row(["TOTAL", f"{sum(hle.values()):.2f} MD"])
    table.add_row(["TEAM CAPACITY", f"{team_capacity:.2f} MD"], divider=True)
    table.add_row(["SPRINT GOAL", f"{sprint_goal} WSJF"])
    print()
    print(table)


def print_tasks_by_assignee(tasks_by_assignee: dict[str, MemberPlan], verbose: bool):
    sorted_tasks_by_assignee = {
        k: tasks_by_assignee[k]
        for k in sorted(tasks_by_assignee.keys())
        if k != UNASSIGNED
    }
    sorted_tasks_by_assignee[UNASSIGNED] = tasks_by_assignee[UNASSIGNED]

    def get_task_detail(task_: Task):
        return (
            f"{task_.hle:.2f}",
            (
                f"{task_.colored_title}\n{task_.colored_url}"
                if verbose
                else task_.colored_title
            ),
            f"{task_.wsjf or ''}",
            task_.status,
        )

    table = PrettyTable()
    table.field_names = ["Assignee", "Tot.", "Cap.", "HLE", "Task", "WSJF", "Status"]

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

    # Set alignment - default left, with specific columns right-aligned
    for field in table.field_names:
        if field in ["Tot.", "Cap.", "WSJF", "HLE"]:
            table.align[field] = "r"
        else:
            table.align[field] = "l"
    print(table)
