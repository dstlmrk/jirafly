import requests
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
        self.jira_url = jira_url.rstrip("/")
        self.email = email
        self.token = token
        self.jira = JIRA(jira_url, basic_auth=(email, token))

    def fetch_tasks(self, filter_id: str) -> list[Task]:
        print("Fetching tasks...", end=" ")

        # Get the filter and its JQL query using the newer API
        filter_obj = self.jira.filter(filter_id)
        jql_query = filter_obj.jql

        # Use direct REST API call to the new search/jql endpoint with pagination
        url = f"{self.jira_url}/rest/api/3/search/jql"
        headers = {"Accept": "application/json"}

        all_issues = []
        next_page_token = None

        while True:
            params = {
                "jql": jql_query,
                "maxResults": 100,  # Maximum per request
                "fields": "*all",
                "nextPageToken": next_page_token,
            }

            response = requests.get(
                url, headers=headers, params=params, auth=(self.email, self.token)
            )

            if response.status_code != 200:
                raise Exception(
                    f"Failed to fetch issues: {response.status_code} - {response.text}"
                )

            data = response.json()
            issues = data.get("issues", [])
            all_issues.extend(issues)
            next_page_token = data.get("nextPageToken")

            if not next_page_token:
                break

        issues = all_issues
        print(f"total issues downloaded: {len(issues)}")

        tasks = []
        for issue_data in issues:
            # Convert raw JSON to JIRA issue-like object for compatibility
            issue = type("Issue", (), {})()
            issue.key = issue_data["key"]
            issue.raw = issue_data  # Add raw data for timetracking access
            issue.fields = type("Fields", (), {})()

            fields = issue_data["fields"]
            issue.fields.summary = fields.get("summary", "")
            issue.fields.issuetype = type(
                "IssueType", (), {"name": fields.get("issuetype", {}).get("name", "")}
            )()

            # Handle assignee properly
            assignee_data = fields.get("assignee")
            if assignee_data:
                issue.fields.assignee = type(
                    "Assignee",
                    (),
                    {
                        "displayName": assignee_data.get("displayName", ""),
                        "accountId": assignee_data.get("accountId", ""),
                        "emailAddress": assignee_data.get("emailAddress", ""),
                    },
                )()
            else:
                issue.fields.assignee = None

            issue.fields.status = type(
                "Status", (), {"name": fields.get("status", {}).get("name", "")}
            )()

            # Handle labels (convert list of strings to list that supports 'in' operator)
            labels_data = fields.get("labels", [])
            issue.fields.labels = labels_data

            # Handle fix versions
            fix_versions_data = fields.get("fixVersions", [])
            fix_versions = []
            for fv in fix_versions_data:
                fix_version = type("FixVersion", (), {"name": fv.get("name", "")})()
                fix_versions.append(fix_version)
            issue.fields.fixVersions = fix_versions

            issue.fields.worklog = fields.get("worklog", {})

            # Add custom fields - handle tech leads properly
            setattr(issue.fields, CUSTOM_FIELD_HLE, fields.get(CUSTOM_FIELD_HLE))
            setattr(issue.fields, CUSTOM_FIELD_WSJF, fields.get(CUSTOM_FIELD_WSJF))

            # Handle tech lead custom fields
            tl1_data = fields.get(CUSTOM_FIELD_TECH_LEAD_1ST)
            if tl1_data:
                tl1_obj = type(
                    "TechLead", (), {"displayName": tl1_data.get("displayName", "")}
                )()
                setattr(issue.fields, CUSTOM_FIELD_TECH_LEAD_1ST, tl1_obj)
            else:
                setattr(issue.fields, CUSTOM_FIELD_TECH_LEAD_1ST, None)

            tl2_data = fields.get(CUSTOM_FIELD_TECH_LEAD_2ND)
            if tl2_data:
                tl2_obj = type(
                    "TechLead", (), {"displayName": tl2_data.get("displayName", "")}
                )()
                setattr(issue.fields, CUSTOM_FIELD_TECH_LEAD_2ND, tl2_obj)
            else:
                setattr(issue.fields, CUSTOM_FIELD_TECH_LEAD_2ND, None)

            if issue.fields.issuetype.name != "Epic":
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
