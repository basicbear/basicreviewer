"""Sum command for crev CLI - summarizes repos and PRs."""

from typing import Optional

import click

from .sum_pr import sum_pr as execute_sum_pr
from .sum_repo import sum_repo as execute_sum_repo


@click.group(invoke_without_command=True)
@click.pass_context
def sum(ctx: click.Context) -> None:
    """Summarize repositories and pull requests.

    If no subcommand is given, runs both 'repo' and 'pr' subcommands.
    """
    # If no subcommand is provided, run both repo and pr
    if ctx.invoked_subcommand is None:
        click.echo("Running both 'repo' and 'pr' summarization...")
        ctx.invoke(repo)
        ctx.invoke(pr)


@sum.command()
@click.argument("repo_name", required=False)
@click.option(
    "--context-only",
    is_flag=True,
    help="Only collect and cache repo context without generating summary",
)
def repo(repo_name: Optional[str] = None, context_only: bool = False) -> None:
    """Summarize repository business purpose, tech stack, and architecture.

    If REPO_NAME is provided, only that repository will be summarized.
    If no REPO_NAME is given, all repositories will be summarized.

    Skips repositories that already have summary files.

    Use --context-only to collect context without generating summaries.
    """
    execute_sum_repo(repo_name, context_only)


@sum.command()
@click.argument("repo_name")
@click.argument("pr_number", type=int, required=False)
@click.option(
    "--context-only",
    is_flag=True,
    help="Only collect and cache PR context without generating summary",
)
def pr(
    repo_name: str, pr_number: Optional[int] = None, context_only: bool = False
) -> None:
    """Summarize pull request business purpose and architecture.

    Requires REPO_NAME to be specified.

    If PR_NUMBER is provided, only that PR will be summarized.
    If no PR_NUMBER is given, all PRs for the repository will be summarized.

    Skips PRs that already have summary files.

    Use --context-only to collect context without generating summaries.
    """
    execute_sum_pr(repo_name, pr_number, context_only)
