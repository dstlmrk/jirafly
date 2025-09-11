import requests
from jira import JIRA

from .models import Task


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
            issue_type = issue_data["fields"].get("issuetype", {}).get("name", "")
            if issue_type != "Epic":
                task = Task.from_raw_issue(issue_data)
                tasks.append(task)
        return tasks
