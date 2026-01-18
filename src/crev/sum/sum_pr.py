"""PR summarization subcommand for the sum command."""

from pathlib import Path
from typing import Any, Optional

import click

from crev.utils import cache_file_check
from crev.utils.ai.llm import get_llm_client
from crev.utils.context.collector import pr as collect_pr_context

from .util import (
    ensure_directory_exists,
    get_repos_from_config,
    load_configs,
    load_prompt_file,
)


def _invoke_llm(llm: Any, prompt: str) -> str:
    """Invoke the LLM and extract the response content.

    Args:
        llm: The LLM client instance
        prompt: The prompt to send

    Returns:
        The response content as a string
    """
    response = llm.invoke(prompt)
    if hasattr(response, "content"):
        return response.content
    return str(response)


def summarize_pr(
    repo_name: str,
    pr_number: int,
    prompt_template: str,
    cache_files_config: dict,
    llm: Optional[Any] = None,
    context_only: bool = False,
) -> None:
    """Summarize a single pull request.

    Args:
        repo_name: Name of the repository
        pr_number: Pull request number
        prompt_template: The prompt template string
        cache_files_config: Cache file name configuration from configs.json
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

    # Get cache file names from config (with defaults)
    context_file_name = cache_files_config.get("context", "sum/sum.context.md")
    output_file_name = cache_files_config.get(
        "output", "summary.pr.{pr_number}.ai.md"
    ).format(pr_number=pr_number)

    # Define cache files in order of creation
    # Each element is passed to cache_file, sub-arrays to other_bypass_files
    cache_files: list[Path] = [
        pr_dir / context_file_name,  # Context file
        pr_dir / output_file_name,  # Final output file
    ]

    # Ensure parent directories exist for cache files
    for cache_file in cache_files:
        ensure_directory_exists(cache_file.parent)

    # Phase 1: Collect PR context
    def collect_context_task() -> str:
        click.echo("  Collecting PR context...")
        return collect_pr_context(pr_dir)

    pr_context = cache_file_check(
        cache_file=cache_files[0],
        task=collect_context_task,
        other_bypass_files=cache_files[1:],  # Skip if final output exists
    )

    # If context_only mode or skipped, we're done
    if context_only:
        click.echo("  Context collection complete (--context-only mode)")
        return

    if pr_context is None:
        # Skipped due to bypass file existing
        return

    # Phase 2: Generate summary with LLM
    if llm is None:
        click.echo("  Error: LLM client not provided", err=True)
        raise ValueError("LLM client is required when not in context_only mode")

    def generate_summary_task() -> str:
        click.echo("  Generating summary with LLM...")
        full_prompt = f"{prompt_template}\n\n{pr_context}"
        return _invoke_llm(llm, full_prompt)

    cache_file_check(
        cache_file=cache_files[1],
        task=generate_summary_task,
    )


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

    # Get cache files config
    cache_files_config = config.get("cache_files", {}).get("sum_pr", {})

    # Get LLM client once if not in context_only mode
    llm = None if context_only else get_llm_client()

    # Process each PR
    for pr in prs_to_process:
        if not isinstance(pr, int):
            click.echo(f"Skipping invalid PR number: {pr}", err=True)
            continue

        summarize_pr(
            repo_name, pr, prompt_template, cache_files_config, llm, context_only
        )

    click.echo("Done.")
