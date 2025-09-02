from dataclasses import dataclass, field

from termcolor import colored


@dataclass
class MemberPlan:
    wd: float  # work days
    vel: float  # velocity
    tasks: list["Task"] = field(default_factory=list)
    total_hle: float = 0


class Task:
    def __init__(
        self,
        issue,
        custom_field_hle: str,
        custom_field_wsjf: str,
        custom_field_tech_lead_first: str,
        custom_field_tech_lead_second: str,
        unassigned: str = "Unassigned",
    ):
        self.assignee: str = (
            issue.fields.assignee.displayName if issue.fields.assignee else unassigned
        )
        self.is_assigned: bool = bool(issue.fields.assignee)
        self._key: str = issue.key
        self._title: str = issue.fields.summary
        self.type: str = issue.fields.issuetype.name
        self._status: str = issue.fields.status
        self.hle: float = getattr(issue.fields, custom_field_hle, 0) or 0
        self.wsjf: float = int(getattr(issue.fields, custom_field_wsjf, 0) or 0)

        def _get_initials(field_name: str) -> str:
            tl = getattr(issue.fields, field_name, None)
            if not tl or not tl.displayName.strip():
                return ""
            return "".join(word[0].upper() for word in tl.displayName.split())

        first, second = (
            _get_initials(custom_field_tech_lead_first),
            _get_initials(custom_field_tech_lead_second),
        )

        if first or second:
            blank = "  "
            self.tl = f"{first or blank}/{second or blank}"
        else:
            self.tl = ""

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
        elif self.type == "Bug":
            self.ratio_type = "Bug"
        else:
            self.ratio_type = "Product"

        fix_versions = sorted(
            issue.fields.fixVersions, key=lambda x: x.name, reverse=True
        )
        self.fix_version: str | None = (
            fix_versions[0].name[:4] if fix_versions else None
        )

        self.time_spent: int = (
            issue.raw["fields"].get("timetracking", {}).get("timeSpentSeconds", 0)
        )

    @property
    def colored_title(self):
        color, title = None, f"{self._key}: {self._title[:80]}"
        if self.ratio_type == "Maintenance":
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
        if self._status.name in ("In Progress", "In Review", "Waiting"):
            return colored(self._status.name, color="yellow")
        elif self._status.name in ("In Testing", "Merged", "Done"):
            return colored(self._status.name, color="green")
        else:
            return self._status.name
