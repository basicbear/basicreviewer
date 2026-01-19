"""Sum command for crev CLI - summarizes repos and PRs."""

from typing import Optional

import click

from .sum_pr import sum_pr as execute_sum_pr
from .sum_repo import sum_repo as execute_sum_repo


@click.group(invoke_without_command=True)
@click.option(
    "--context-only",
    is_flag=True,
    help="Only collect and cache context without generating summaries",
)
@click.pass_context
def sum(ctx: click.Context, context_only: bool = False) -> None:
    """Summarize repositories and pull requests.

    If no subcommand is given, runs both 'repo' and 'pr' subcommands
    for all orgs/repos/prs.

    Use --context-only to collect context without generating summaries.
    """
    # Store context_only in the context for subcommands to access
    ctx.ensure_object(dict)
    ctx.obj["context_only"] = context_only

    # If no subcommand is provided, run both repo and pr for all
    if ctx.invoked_subcommand is None:
        click.echo("Running both 'repo' and 'pr' summarization for all orgs/repos/prs...")
        ctx.invoke(repo, org=None, repo_name=None, context_only=context_only)
        ctx.invoke(pr, org=None, repo_name=None, pr_number=None, context_only=context_only)


@sum.command()
@click.argument("org", required=False)
@click.argument("repo_name", required=False)
@click.option(
    "--context-only",
    is_flag=True,
    help="Only collect and cache repo context without generating summary",
)
@click.pass_context
def repo(
    ctx: click.Context,
    org: Optional[str] = None,
    repo_name: Optional[str] = None,
    context_only: bool = False,
) -> None:
    """Summarize repository business purpose, tech stack, and architecture.

    \b
    Arguments:
      ORG        Organization name (use "." for all orgs)
      REPO_NAME  Repository name (use "." for all repos in org)

    \b
    Examples:
      crev sum repo                    # All repos in all orgs
      crev sum repo myorg              # All repos in myorg
      crev sum repo myorg myrepo       # Specific repo
      crev sum repo . myrepo           # myrepo in all orgs
      crev sum repo myorg .            # All repos in myorg

    Skips repositories that already have summary files.

    Use --context-only to collect context without generating summaries.
    """
    # Inherit context_only from parent if not explicitly set
    if not context_only and ctx.obj:
        context_only = ctx.obj.get("context_only", False)

    execute_sum_repo(org, repo_name, context_only)


@sum.command()
@click.argument("org", required=False)
@click.argument("repo_name", required=False)
@click.argument("pr_number", required=False)
@click.option(
    "--context-only",
    is_flag=True,
    help="Only collect and cache PR context without generating summary",
)
@click.pass_context
def pr(
    ctx: click.Context,
    org: Optional[str] = None,
    repo_name: Optional[str] = None,
    pr_number: Optional[str] = None,
    context_only: bool = False,
) -> None:
    """Summarize pull request business purpose and architecture.

    \b
    Arguments:
      ORG        Organization name (use "." for all orgs)
      REPO_NAME  Repository name (use "." for all repos)
      PR_NUMBER  Pull request number (use "." for all PRs)

    \b
    Examples:
      crev sum pr                      # All PRs in all repos
      crev sum pr myorg                # All PRs in myorg
      crev sum pr myorg myrepo         # All PRs in myorg/myrepo
      crev sum pr myorg myrepo 123     # Specific PR
      crev sum pr . . .                # All PRs everywhere

    Skips PRs that already have summary files.

    Use --context-only to collect context without generating summaries.
    """
    # Inherit context_only from parent if not explicitly set
    if not context_only and ctx.obj:
        context_only = ctx.obj.get("context_only", False)

    # Convert pr_number to int if provided and not "."
    pr_num: Optional[int] = None
    if pr_number is not None and pr_number != ".":
        try:
            pr_num = int(pr_number)
        except ValueError:
            click.echo(f"Error: PR_NUMBER must be an integer or '.', got '{pr_number}'", err=True)
            raise SystemExit(1)

    execute_sum_pr(org, repo_name, pr_num if pr_number != "." else None, context_only)
