"""Utility functions for the sum command."""

import json
from pathlib import Path
from typing import Any, Optional

import click


def load_configs() -> dict:
    """Load configs.json from the current directory.

    Returns:
        Dictionary containing configuration data

    Raises:
        SystemExit: If configs.json is not found
    """
    configs_file = Path("configs.json")

    if not configs_file.exists():
        click.echo("Error: configs.json not found. Run 'crev init' first.", err=True)
        raise SystemExit(1)

    with open(configs_file) as f:
        return json.load(f)


def get_repos_from_config(
    config: dict,
    org: Optional[str] = None,
    repo_name: Optional[str] = None,
) -> list[dict]:
    """Get repos to process from config.

    Args:
        config: Configuration dictionary
        org: Optional org name to filter by. Use "." to match all orgs.
        repo_name: Optional specific repo name to filter by. Use "." to match all repos.

    Returns:
        List of repo dictionaries to process

    Raises:
        SystemExit: If specified repo is not found
    """
    all_repos = config.get("repos", [])

    # Handle "." as wildcard meaning "all"
    if org == ".":
        org = None
    if repo_name == ".":
        repo_name = None

    # Filter by org if specified
    if org:
        all_repos = [r for r in all_repos if r.get("org") == org]
        if not all_repos:
            click.echo(f"Error: Organization '{org}' not found in configs.json", err=True)
            raise SystemExit(1)

    # Filter by repo name if specified
    if repo_name:
        repos = [r for r in all_repos if r.get("name") == repo_name]
        if not repos:
            if org:
                click.echo(
                    f"Error: Repository '{repo_name}' not found in org '{org}' in configs.json",
                    err=True,
                )
            else:
                click.echo(
                    f"Error: Repository '{repo_name}' not found in configs.json", err=True
                )
            raise SystemExit(1)
        return repos
    else:
        return all_repos


def load_prompt_file(prompt_path: str) -> str:
    """Load a prompt from a file.

    Args:
        prompt_path: Path to the prompt file

    Returns:
        Contents of the prompt file

    Raises:
        SystemExit: If prompt file is not found
    """
    prompt_file = Path(prompt_path)

    if not prompt_file.exists():
        click.echo(f"Error: Prompt file '{prompt_path}' not found.", err=True)
        raise SystemExit(1)

    return prompt_file.read_text()


def ensure_directory_exists(directory: Path) -> None:
    """Ensure a directory exists, creating it if necessary.

    Args:
        directory: Path to the directory
    """
    directory.mkdir(parents=True, exist_ok=True)


def should_skip_existing(output_file: Path) -> bool:
    """Check if an output file exists and should be skipped.

    Args:
        output_file: Path to the output file

    Returns:
        True if file exists and should be skipped, False otherwise
    """
    if output_file.exists():
        click.echo(f"  Output file already exists, skipping: {output_file}")
        return True
    return False


def generate_summary_with_llm(
    llm: Any, prompt: str, output_file: Path
) -> None:
    """Generate a summary using an LLM and save it to a file.

    Args:
        llm: The LLM client instance
        prompt: The full prompt to send to the LLM
        output_file: Path where the summary should be saved

    Raises:
        Exception: If there's an error generating the summary
    """
    click.echo("  Generating summary with LLM...")

    try:
        response = llm.invoke(prompt)

        # Extract content from the response
        if hasattr(response, "content"):
            summary = response.content
        else:
            summary = str(response)

        # Save summary to file
        output_file.write_text(summary)
        click.echo(f"  Summary saved to: {output_file}")

    except Exception as e:
        click.echo(f"  Error generating summary: {e}", err=True)
        raise
