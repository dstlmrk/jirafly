# Jirafly 🪰

Jirafly helps you calculate key statistics that Jira itself cannot provide, offering essential insights for effective team management.

## How to develop

This package uses [uv](https://github.com/astral/uv) for dependency management. To install Jirafly and its dependencies:

1. Install uv (if not installed):
```bash
$ curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Create a virtual environment and sync dependencies:
```bash
$ uv venv
$ uv sync --dev
```

3. Install pre-commit hooks:
```bash
$ uv run pre-commit install
```

## Running

You can run the CLI app from the activated virtual environment:

```bash
$ uv run jirafly planning --help
$ uv run jirafly ratio --help
```

### Available Commands

**Planning Command:**
```bash
$ uv run jirafly planning configs/team.yaml
```

**Ratio Analysis:**
```bash
$ uv run jirafly ratio
```

## Setup

### 1. Team Configuration

Copy and edit the team configuration file:
```bash
$ cp configs/example.yaml configs/team.yaml
```

Edit `configs/team.yaml` with your team details:
```yaml
members:
  - name: "Your Name"
    wd: 10.0   # Work days per sprint (0-10)
    vel: 0.3   # Velocity/productivity factor

  - name: "Teammate Name"
    wd: 4.0    # Part-time member
    vel: 0.6   # Higher productivity
```

**Team Configuration Parameters:**
- **name**: Full name of the team member (must match JIRA assignee names)
- **wd**: Working days in the sprint (0-10, decimals allowed for part-time)
- **vel**: Velocity factor

Team capacity is calculated as: `wd × vel` for each member.

### 2. Environment Variables

Create a `.env` file in the project root:
```bash
$ cat > .env << EOF
JIRA_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your.email@company.com
JIRA_TOKEN=your_jira_api_token
PLANNING_FILTER_ID=12345
RATIO_FILTER_ID=67890
EOF
```

### Code Quality

Format and check your code:
```bash
uv run pre-commit run --all-files
```

### Adding dependencies

To add runtime dependencies:

```bash
uv add $PACKAGE_NAME
```

To add development dependencies:

```bash
uv add --dev $PACKAGE_NAME
```

### Configuration

Used environment variables:
- `JIRA_URL` - JIRA server URL (e.g., https://yourcompany.atlassian.net)
- `JIRA_EMAIL` - Email for JIRA authentication
- `JIRA_TOKEN` - JIRA API token for authentication
- `PLANNING_FILTER_ID` - JIRA filter ID for planning command
- `RATIO_FILTER_ID` - JIRA filter ID for ratio analysis
