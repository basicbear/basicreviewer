"""MCP server command for crev CLI - exposes summary data via MCP protocol."""

import click

from .server import create_server


@click.command(name="mcp-serv")
def mcp_serv() -> None:
    """Start the MCP server to expose crev data.

    This starts an MCP (Model Context Protocol) server that exposes
    crev summary data through standardized endpoints.

    \b
    Endpoints:
      Summary Endpoints:
        - sum_repo: Get repository summaries by org(s)
        - sum_pr: Get PR summaries by org/repo/pr_number
        - sum_list: List available summaries

      CV Endpoints:
        - stack: Get tech stack data from repo summaries
        - accomplishments: Get accomplishment data from PR summaries
        - org_list: List available organizations
    """
    server = create_server()
    server.run()
