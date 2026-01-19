"""Organizational endpoints for the MCP server."""

from typing import Any

from fastmcp import FastMCP

from .utils import find_pr_summary, find_repo_summary, get_distinct_orgs, get_repos_for_org


def register_organizational_endpoints(mcp: FastMCP) -> None:
    """Register organizational endpoints on the MCP server.

    Args:
        mcp: FastMCP server instance
    """

    @mcp.tool()
    def stack(org: str) -> dict[str, Any]:
        """Get tech stack data from repository summaries for a specific organization.

        This pulls in sum_repo data for all repositories belonging to the specified org.

        Args:
            org: Organization name

        Returns:
            Dictionary with repo summaries for the org
        """
        repos = get_repos_for_org(org)
        return {
            "org": org,
            "repos": {
                repo_name: summary
                for repo in repos
                if (repo_name := repo.get("name"))
                and (summary := find_repo_summary(org, repo_name))
            },
        }

    @mcp.tool()
    def accomplishments(org: str) -> dict[str, Any]:
        """Get accomplishment data from PR summaries for a specific organization.

        This pulls in sum_pr data for all PRs belonging to repos in the specified org.

        Args:
            org: Organization name

        Returns:
            Dictionary with PR summaries organized by repo
        """
        repos = get_repos_for_org(org)
        return {
            "org": org,
            "repos": {
                repo_name: {
                    "pull_requests": {
                        pr_number: summary
                        for pr_number in repo.get("pull_requests", [])
                        if isinstance(pr_number, int)
                        and (summary := find_pr_summary(org, repo_name, pr_number))
                    }
                }
                for repo in repos
                if (repo_name := repo.get("name"))
            },
        }

    @mcp.tool()
    def org_list() -> dict[str, Any]:
        """Get list of distinct organizations from configs.json.

        Returns:
            Dictionary with 'orgs' key containing list of unique organization names
        """
        return {"orgs": get_distinct_orgs()}
