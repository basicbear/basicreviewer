"""Utility functions for the MCP server."""

import json
from pathlib import Path
from typing import Any


def load_configs() -> dict:
    """Load configs.json from current directory.

    Returns:
        Configuration dictionary

    Raises:
        FileNotFoundError: If configs.json doesn't exist
    """
    configs_file = Path("configs.json")
    if not configs_file.exists():
        raise FileNotFoundError(
            "configs.json not found. Run 'crev init' first to create a workspace."
        )
    with open(configs_file) as f:
        return json.load(f)


def get_data_dir() -> Path:
    """Get the data directory path.

    Returns:
        Path to the data directory
    """
    return Path("data")


def find_repo_summary(org: str, repo_name: str) -> str | None:
    """Find the repository summary file for a given org/repo.

    Args:
        org: Organization name
        repo_name: Repository name

    Returns:
        Content of the summary file, or None if not found
    """
    data_dir = get_data_dir()
    sum_dir = data_dir / org / repo_name / "sum"

    if not sum_dir.exists():
        return None

    # Look for sum.repo.*.ai.md files (the combined output), fallback to .json
    file = next(sum_dir.glob("sum.repo.*.ai.md"), None) or next(
        sum_dir.glob("sum.repo.*.ai.json"), None
    )
    return file.read_text() if file else None


def find_pr_summary(org: str, repo_name: str, pr_number: int) -> str | None:
    """Find the PR summary file for a given org/repo/pr.

    Args:
        org: Organization name
        repo_name: Repository name
        pr_number: Pull request number

    Returns:
        Content of the summary file, or None if not found
    """
    data_dir = get_data_dir()
    pr_dir = data_dir / org / repo_name / str(pr_number)

    if not pr_dir.exists():
        return None

    # Look for sum.pr.{pr_number}.ai.md files
    summary_file = pr_dir / f"sum.pr.{pr_number}.ai.md"
    if summary_file.exists():
        return summary_file.read_text()

    return None


def _try_parse_int(s: str) -> int | None:
    """Try to parse a string as an integer, return None if it fails."""
    try:
        return int(s)
    except ValueError:
        return None


def list_available_summaries() -> dict[str, Any]:
    """List all available summaries in the data directory.

    Returns:
        Dictionary with repo_summaries and pr_summaries lists
    """
    data_dir = get_data_dir()
    if not data_dir.exists():
        return {"repo_summaries": [], "pr_summaries": []}

    # Get all org/repo directory pairs
    repo_dirs = [
        (org_dir.name, repo_dir)
        for org_dir in data_dir.iterdir()
        if org_dir.is_dir()
        for repo_dir in org_dir.iterdir()
        if repo_dir.is_dir()
    ]

    # Find repo summaries (first matching file per repo)
    repo_summaries = [
        {"org": org, "repo": repo_dir.name, "file": file.name}
        for org, repo_dir in repo_dirs
        if (file := next((repo_dir / "sum").glob("sum.repo.*.ai.md"), None))
    ]

    # Find PR summaries (numeric directories with summary files)
    pr_summaries = [
        {
            "org": org,
            "repo": repo_dir.name,
            "pr_number": pr_number,
            "file": summary_file.name,
        }
        for org, repo_dir in repo_dirs
        for pr_dir in repo_dir.iterdir()
        if pr_dir.is_dir()
        and (pr_number := _try_parse_int(pr_dir.name)) is not None
        and (summary_file := pr_dir / f"sum.pr.{pr_number}.ai.md").exists()
    ]

    return {"repo_summaries": repo_summaries, "pr_summaries": pr_summaries}


def get_distinct_orgs() -> list[str]:
    """Get list of distinct organizations from configs.json.

    Returns:
        List of unique organization names
    """
    try:
        config = load_configs()
    except FileNotFoundError:
        return []

    repos = config.get("repos", [])
    return sorted({repo.get("org") for repo in repos if repo.get("org")})


def get_repos_for_org(org: str) -> list[dict]:
    """Get list of repos for a specific organization from configs.json.

    Args:
        org: Organization name

    Returns:
        List of repo configurations for the org
    """
    try:
        config = load_configs()
    except FileNotFoundError:
        return []

    repos = config.get("repos", [])
    return [repo for repo in repos if repo.get("org") == org]
