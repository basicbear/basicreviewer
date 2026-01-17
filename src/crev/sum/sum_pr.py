"""PR summarization subcommand for the sum command."""

from pathlib import Path
from typing import Any, Optional

import click

from crev.utils.ai.llm import get_llm_client
from crev.utils.context.collector import pr as collect_pr_context

from .util import (
    ensure_directory_exists,
    generate_summary_with_llm,
    get_repos_from_config,
    load_configs,
    load_prompt_file,
    should_skip_existing,
)


def summarize_pr(
    repo_name: str,
    pr_number: int,
    prompt_template: str,
    llm: Optional[Any] = None,
    context_only: bool = False,
) -> None:
    """Summarize a single pull request.

    Args:
        repo_name: Name of the repository
        pr_number: Pull request number
        prompt_template: The prompt template string
        llm: Optional LLM client instance (required if not context_only)
        context_only: If True, only collect context and skip LLM generation
    """
    click.echo(f"Summarizing PR #{pr_number} for {repo_name}")

    # Check if PR directory exists
    pr_dir = Path("pullrequests") / repo_name / str(pr_number)
    if not pr_dir.exists():
        click.echo(f"  Error: PR directory not found: {pr_dir}", err=True)
        click.echo("  Run 'crev extract' first to extract PR data.", err=True)
        return

    # Check if output file exists (skip if not context_only mode)
    if not context_only:
        output_file = pr_dir / f"summary.pr.{pr_number}.ai.txt"
        if should_skip_existing(output_file):
            return

    # Ensure sum directory exists
    sum_dir = pr_dir / "sum"
    ensure_directory_exists(sum_dir)

    # Check for cached context or collect new context
    context_file = sum_dir / "sum.context.md"
    if context_file.exists():
        click.echo("  Loading cached PR context...")
        pr_context = context_file.read_text()
    else:
        click.echo("  Collecting PR context...")
        pr_context = collect_pr_context(pr_dir)
        # Save context to cache file
        context_file.write_text(pr_context)
        click.echo(f"  Context saved to: {context_file}")

    # If context_only mode, we're done
    if context_only:
        click.echo("  Context collection complete (--context-only mode)")
        return

    # Combine prompt and context
    full_prompt = f"{prompt_template}\n\n{pr_context}"

    # Generate summary using the injected LLM client
    if llm is None:
        click.echo("  Error: LLM client not provided", err=True)
        raise ValueError("LLM client is required when not in context_only mode")

    generate_summary_with_llm(llm, full_prompt, output_file)


def sum_pr(
    repo_name: str, pr_number: Optional[int] = None, context_only: bool = False
) -> None:
    """Execute PR summarization.

    Args:
        repo_name: Repository name (required)
        pr_number: Optional specific PR number. If None, processes all PRs for the repo.
        context_only: If True, only collect context and skip LLM generation
    """
    # Load config
    config = load_configs()

    # Get the specific repo from config to get PR list
    repos = get_repos_from_config(config, repo_name)
    if not repos:
        return

    repo = repos[0]
    pull_requests = repo.get("pull_requests", [])

    # Filter to specific PR if provided
    if pr_number is not None:
        if pr_number not in pull_requests:
            click.echo(
                f"Error: PR #{pr_number} not found in configs.json for repo '{repo_name}'",
                err=True,
            )
            raise SystemExit(1)
        prs_to_process = [pr_number]
    else:
        prs_to_process = pull_requests

    # Load prompt once before processing PRs
    prompt_path = config.get("prompts", {}).get("sum_pr", "prompts/sum.pr.txt")
    prompt_template = load_prompt_file(prompt_path)

    # Get LLM client once if not in context_only mode
    llm = None if context_only else get_llm_client()

    # Process each PR
    for pr in prs_to_process:
        if not isinstance(pr, int):
            click.echo(f"Skipping invalid PR number: {pr}", err=True)
            continue

        summarize_pr(repo_name, pr, prompt_template, llm, context_only)

    click.echo("Done.")
