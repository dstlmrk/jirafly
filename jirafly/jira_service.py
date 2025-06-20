from jira import JIRA

from .models import Task

# Custom Fields
CUSTOM_FIELD_HLE = "customfield_11605"
CUSTOM_FIELD_WSJF = "customfield_11737"
CUSTOM_FIELD_TECH_LEAD_1ST = "customfield_11606"
CUSTOM_FIELD_TECH_LEAD_2ND = "customfield_11634"

# Constants
UNASSIGNED = "Unassigned"


class JiraClient:
    def __init__(self, jira_url: str, email: str, token: str):
        if not jira_url:
            raise ValueError("JIRA URL must be provided")
        print("Establishing Jira connection...")
        self.jira = JIRA(jira_url, basic_auth=(email, token))

    def fetch_tasks(self, filter_id: str, limit: int = 1000) -> list[Task]:
        print(f"Fetching (max {limit}) tasks...")
        issues = self.jira.search_issues(f"filter={filter_id}", maxResults=limit)
        tasks = []
        for issue in issues:
            if hasattr(issue, "fields") and issue.fields.issuetype.name != "Epic":
                tasks.append(
                    Task(
                        issue,
                        CUSTOM_FIELD_HLE,
                        CUSTOM_FIELD_WSJF,
                        CUSTOM_FIELD_TECH_LEAD_1ST,
                        CUSTOM_FIELD_TECH_LEAD_2ND,
                        UNASSIGNED,
                    )
                )
        return tasks
