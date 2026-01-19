"""Summary endpoints for the MCP server."""

from typing import Any

from fastmcp import FastMCP

from .utils import (
    find_pr_summary,
    find_repo_summary,
    list_available_summaries,
    load_configs,
)


def register_summary_endpoints(mcp: FastMCP) -> None:
    """Register summary endpoints on the MCP server.

    Args:
        mcp: FastMCP server instance
    """

    @mcp.tool()
    def sum_repo(orgs: list[str]) -> dict[str, Any]:
        """Get repository summaries for the specified organizations.

        Args:
            orgs: List of organization names to get repo summaries for

        Returns:
            Dictionary mapping org/repo to summary content
        """
        try:
            config = load_configs()
        except FileNotFoundError as e:
            return {"error": str(e)}

        repos = config.get("repos", [])
        return {
            f"{org}/{repo_name}": find_repo_summary(org, repo_name)
            for repo in repos
            if (org := repo.get("org"))
            and (repo_name := repo.get("name"))
            and org in orgs
        }

    @mcp.tool()
    def sum_pr(repos: list[dict[str, Any]]) -> dict[str, Any]:
        """Get PR summaries for the specified repositories and PR numbers.

        Args:
            repos: List of objects with structure similar to configs.json repos field.
                   Each object should have: org, name, and pull_requests (list of PR numbers)

        Returns:
            Dictionary mapping org/repo/pr_number to summary content
        """
        return {
            f"{org}/{repo_name}/{pr_number}": find_pr_summary(org, repo_name, pr_number)
            for repo in repos
            if (org := repo.get("org")) and (repo_name := repo.get("name"))
            for pr_number in repo.get("pull_requests", [])
            if isinstance(pr_number, int)
        }

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

        try:
            config = load_configs()
            result["repos"] = config.get("repos", [])
        except FileNotFoundError:
            result["repos"] = []

        return result
