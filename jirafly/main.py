from dotenv import load_dotenv

from jirafly.cli import app


def main():
    """Main entry point for the jirafly CLI."""
    # Load .env file before running the CLI
    load_dotenv()
    app()


if __name__ == "__main__":
    main()
