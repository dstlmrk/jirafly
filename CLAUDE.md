# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Jirafly is a CLI tool for Jira analytics and team sprint planning. It calculates metrics that Jira doesn't provide natively, including team capacity planning, work ratio analysis (maintenance vs product development), and sprint statistics.

**Technology Stack:**
- Python 3.12
- Typer CLI framework
- Jira Python library + direct REST API calls
- uv for dependency management
- Pydantic for configuration validation
- PrettyTable for terminal output

## Development Commands

**Setup:**
```bash
# Install dependencies and sync
uv sync --dev

# Install pre-commit hooks
uv run pre-commit install
```

**Running the CLI:**
```bash
# Sprint planning (requires sprint identifier like "6.12")
uv run jirafly planning <sprint_id> configs/team.yaml

# Work ratio analysis
uv run jirafly ratio configs/team.yaml

# Override team member settings via CLI
uv run jirafly planning <sprint_id> configs/team.yaml --member peter=7.0,0.3 --member jane=5.0,0.5
```

**Code Quality:**
```bash
# Format and lint with ruff
uv run pre-commit run --all-files
```

**Adding Dependencies:**
```bash
# Runtime dependencies
uv add $PACKAGE_NAME

# Development dependencies
uv add --dev $PACKAGE_NAME
```

## Configuration

**Environment Variables (.env file required):**
- `JIRA_URL` - Jira server URL (e.g., https://yourcompany.atlassian.net)
- `JIRA_EMAIL` - Email for Jira authentication
- `JIRA_TOKEN` - Jira API token
- `PLANNING_FILTER_ID` - Jira filter ID for planning command
- `RATIO_FILTER_ID` - Jira filter ID for ratio analysis command

**Team Configuration (configs/team.yaml):**
```yaml
members:
  - name: "John Doe"      # Must match Jira assignee display name
    nickname: john        # Short identifier for CLI overrides
    wd: 5.0              # Working days per sprint (0-10)
    vel: 0.4             # Velocity factor (productivity multiplier)

working_days_per_sprint:
  "6.12":
    total: 25.0          # Total team working days for sprint 6.12
```

Team capacity is calculated as: `wd × vel` per member.

## Architecture

**Core Components:**

1. **jira_service.py** - Jira API client
   - Uses Jira Python library for authentication and filter retrieval
   - Uses direct REST API (`/rest/api/3/search/jql`) for pagination (fetches all issues with nextPageToken)
   - Excludes Epic issue types from task lists

2. **models.py** - Data models and formatting
   - `Task` class with `from_raw_issue()` factory method to parse Jira API responses
   - Custom field mappings (HLE, WSJF, Tech Leads, Sprint)
   - Task categorization: Product, Bug, Maintenance, Excluded (based on labels and issue type)
   - Version extraction logic: strips dates and normalizes to X.Y format (e.g., "6.12.0 (16. 9. - 29. 9)" → "6.12")

3. **team_config.py** - Team configuration management
   - Pydantic models for validation: `TeamConfig`, `TeamMember`, `SprintWorkingDays`
   - CLI override system using nicknames
   - Converts between dict formats for internal use

4. **cli.py** - Command implementations
   - `planning` command: Sprint capacity planning with task assignment analysis
   - `ratio` command: Maintenance vs Product work ratio analysis with time tracking
   - Both commands support team member overrides via `--member` flag

5. **utils.py** - Display utilities (PrettyTable formatting, color coding)

**Key Custom Fields (from models.py):**
- `customfield_11605` - HLE (estimate)
- `customfield_11737` - WSJF (priority score)
- `customfield_11606` - Tech Lead 1st
- `customfield_11634` - Tech Lead 2nd
- `customfield_10000` - Sprint

**Task Categorization Logic:**
- Excluded: Has "RatioExcluded" or "Bughunting" label
- Maintenance: Has "Maintenance" or "DevOps" label
- Bug: Issue type is "Bug"
- Product: Everything else

## Data Flow

**Planning Command:**
1. Load team config (YAML) and apply CLI overrides
2. Fetch tasks from Jira filter (via `PLANNING_FILTER_ID`)
3. Group tasks by assignee and calculate total HLE per member
4. Compare against team capacity (wd × vel)
5. Display capacity utilization with color-coded warnings for overallocation

**Ratio Command:**
1. Load team config for working days per sprint data
2. Fetch tasks from Jira filter (via `RATIO_FILTER_ID`)
3. Group by fix version and categorize (Maintenance/Bug/Product/Excluded)
4. Calculate HLE ratios and time spent percentages per sprint
5. Display efficiency metric: (total HLE + excluded) / working days
6. Show overall maintenance vs product ratio across all sprints

## Important Implementation Details

- **Version Normalization**: Both fix versions and sprints are normalized to X.Y format (first two dot-separated parts)
- **Sprint Highlighting**: Tasks from previous sprints are highlighted in red in planning output
- **Time Tracking**: Ratio command uses `timetracking.timeSpentSeconds` field
- **Pagination**: Jira fetch uses nextPageToken pagination (max 100 results per page)
- **Assignee Matching**: Team member names in config must exactly match Jira `assignee.displayName`
- **URL Formatting**: Task URLs are hardcoded to mallpay.atlassian.net domain (see models.py:131)

# Rules
- **ABSOLUTELY NEVER mention Claude, AI, or code generation in commit messages, MR descriptions, or comments**.
