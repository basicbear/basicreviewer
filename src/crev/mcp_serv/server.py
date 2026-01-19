"""MCP server implementation using FastMCP."""

import json
from pathlib import Path
from typing import Any

from fastmcp import FastMCP


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

    # Look for sum.repo.*.ai.md files (the combined output)
    for file in sum_dir.glob("sum.repo.*.ai.md"):
        return file.read_text()

    # Also check for sum.repo.*.ai.json if md not found
    for file in sum_dir.glob("sum.repo.*.ai.json"):
        return file.read_text()

    return None


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


def list_available_summaries() -> dict[str, Any]:
    """List all available summaries in the data directory.

    Returns:
        Dictionary with repo_summaries and pr_summaries lists
    """
    data_dir = get_data_dir()
    result: dict[str, Any] = {"repo_summaries": [], "pr_summaries": []}

    if not data_dir.exists():
        return result

    # Iterate through org directories
    for org_dir in data_dir.iterdir():
        if not org_dir.is_dir():
            continue
        org = org_dir.name

        # Iterate through repo directories
        for repo_dir in org_dir.iterdir():
            if not repo_dir.is_dir():
                continue
            repo_name = repo_dir.name

            # Check for repo summary in sum/ subdirectory
            sum_dir = repo_dir / "sum"
            if sum_dir.exists():
                for file in sum_dir.glob("sum.repo.*.ai.md"):
                    result["repo_summaries"].append(
                        {"org": org, "repo": repo_name, "file": file.name}
                    )
                    break  # Only add one entry per repo

            # Check for PR summaries (directories that are numeric)
            for pr_dir in repo_dir.iterdir():
                if not pr_dir.is_dir():
                    continue
                try:
                    pr_number = int(pr_dir.name)
                    # Check if PR summary exists
                    summary_file = pr_dir / f"sum.pr.{pr_number}.ai.md"
                    if summary_file.exists():
                        result["pr_summaries"].append(
                            {
                                "org": org,
                                "repo": repo_name,
                                "pr_number": pr_number,
                                "file": summary_file.name,
                            }
                        )
                except ValueError:
                    # Not a PR directory (like "sum")
                    continue

    return result


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
    orgs = set()
    for repo in repos:
        org = repo.get("org")
        if org:
            orgs.add(org)

    return sorted(list(orgs))


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


def create_server() -> FastMCP:
    """Create and configure the FastMCP server.

    Returns:
        Configured FastMCP server instance
    """
    mcp = FastMCP("crev")

    # --- Summary Endpoints ---

    @mcp.tool()
    def sum_repo(orgs: list[str]) -> dict[str, Any]:
        """Get repository summaries for the specified organizations.

        Args:
            orgs: List of organization names to get repo summaries for

        Returns:
            Dictionary mapping org/repo to summary content
        """
        results: dict[str, Any] = {}

        try:
            config = load_configs()
        except FileNotFoundError as e:
            return {"error": str(e)}

        repos = config.get("repos", [])

        for repo in repos:
            org = repo.get("org")
            repo_name = repo.get("name")

            if not org or not repo_name:
                continue

            if org not in orgs:
                continue

            summary = find_repo_summary(org, repo_name)
            key = f"{org}/{repo_name}"

            if summary:
                results[key] = summary
            else:
                results[key] = None

        return results

    @mcp.tool()
    def sum_pr(repos: list[dict[str, Any]]) -> dict[str, Any]:
        """Get PR summaries for the specified repositories and PR numbers.

        Args:
            repos: List of objects with structure similar to configs.json repos field.
                   Each object should have: org, name, and pull_requests (list of PR numbers)

        Returns:
            Dictionary mapping org/repo/pr_number to summary content
        """
        results: dict[str, Any] = {}

        for repo in repos:
            org = repo.get("org")
            repo_name = repo.get("name")
            pull_requests = repo.get("pull_requests", [])

            if not org or not repo_name:
                continue

            for pr_number in pull_requests:
                if not isinstance(pr_number, int):
                    continue

                summary = find_pr_summary(org, repo_name, pr_number)
                key = f"{org}/{repo_name}/{pr_number}"

                if summary:
                    results[key] = summary
                else:
                    results[key] = None

        return results

    @mcp.tool()
    def sum_list() -> dict[str, Any]:
        """List available repository and PR summaries.

        Returns:
            Dictionary containing:
            - repo_summaries: List of available repo summaries with org, repo, file
            - pr_summaries: List of available PR summaries with org, repo, pr_number, file
            - repos: Repository configuration from configs.json (if available)
        """
        result = list_available_summaries()

        # Include repos from configs.json
        try:
            config = load_configs()
            result["repos"] = config.get("repos", [])
        except FileNotFoundError:
            result["repos"] = []

        return result

    # --- CV Endpoints ---

    @mcp.tool()
    def stack(org: str) -> dict[str, Any]:
        """Get tech stack data from repository summaries for a specific organization.

        This pulls in sum_repo data for all repositories belonging to the specified org.

        Args:
            org: Organization name

        Returns:
            Dictionary with repo summaries for the org
        """
        results: dict[str, Any] = {"org": org, "repos": {}}

        repos = get_repos_for_org(org)

        for repo in repos:
            repo_name = repo.get("name")
            if not repo_name:
                continue

            summary = find_repo_summary(org, repo_name)
            if summary:
                results["repos"][repo_name] = summary

        return results

    @mcp.tool()
    def accomplishments(org: str) -> dict[str, Any]:
        """Get accomplishment data from PR summaries for a specific organization.

        This pulls in sum_pr data for all PRs belonging to repos in the specified org.

        Args:
            org: Organization name

        Returns:
            Dictionary with PR summaries organized by repo
        """
        results: dict[str, Any] = {"org": org, "repos": {}}

        repos = get_repos_for_org(org)

        for repo in repos:
            repo_name = repo.get("name")
            pull_requests = repo.get("pull_requests", [])

            if not repo_name:
                continue

            results["repos"][repo_name] = {"pull_requests": {}}

            for pr_number in pull_requests:
                if not isinstance(pr_number, int):
                    continue

                summary = find_pr_summary(org, repo_name, pr_number)
                if summary:
                    results["repos"][repo_name]["pull_requests"][pr_number] = summary

        return results

    @mcp.tool()
    def org_list() -> list[str]:
        """Get list of distinct organizations from configs.json.

        Returns:
            List of unique organization names
        """
        return get_distinct_orgs()

    return mcp
