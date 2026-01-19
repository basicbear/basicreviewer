"""PR summarization subcommand for the sum command."""

from pathlib import Path
from typing import Any, Optional

import click

from crev.utils import cache_file_check
from crev.utils.ai.llm import get_llm_client
from crev.utils.context.collector import pr as collect_pr_context

from .util import (
    get_repos_from_config,
    load_configs,
    load_prompt_file,
)

# Default cache filenames for sum_pr (used if not specified in configs.json)
DEFAULT_CONTEXT_FILENAME = "sum.pr.{pr_number}.context.md"
DEFAULT_OUTPUT_FILENAME = "sum.pr.{pr_number}.ai.md"


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
    org: str,
    pr_number: int,
    prompt_template: str,
    cache_files_config: dict,
    llm: Optional[Any] = None,
    context_only: bool = False,
) -> None:
    """Summarize a single pull request.

    Args:
        repo_name: Name of the repository
        org: Organization name for the repository
        pr_number: Pull request number
        prompt_template: The prompt template string
        cache_files_config: Cache file name configuration from configs.json
        llm: Optional LLM client instance (required if not context_only)
        context_only: If True, only collect context and skip LLM generation
    """
    click.echo(f"Summarizing PR #{pr_number} for {org}/{repo_name}")

    # Check if PR directory exists
    pr_dir = Path("pullrequests") / org / repo_name / str(pr_number)
    output_dir = Path("data") / org / repo_name / str(pr_number)
    if not pr_dir.exists():
        click.echo(f"  Error: PR directory not found: {pr_dir}", err=True)
        click.echo("  Run 'crev extract' first to extract PR data.", err=True)
        return

    # Format args for filename templates
    format_args = {"pr_number": pr_number}

    # Phase 1: Collect PR context
    def collect_context_task() -> str:
        click.echo("  Collecting PR context...")
        return collect_pr_context(pr_dir)

    # Get filenames from config and format with pr_number
    context_filename = cache_files_config.get("context").format(pr_number=pr_number)
    output_filename = cache_files_config.get("result").format(pr_number=pr_number)

    pr_context = cache_file_check(
        output_dir=output_dir,
        cache_files_config=cache_files_config,
        cache_key="context",
        task=collect_context_task,
        default_filename=context_filename,
        bypass_keys=["output"],
        format_args=format_args,
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
        output_dir=output_dir,
        cache_files_config=cache_files_config,
        cache_key="output",
        task=generate_summary_task,
        default_filename=output_filename,
        format_args=format_args,
    )


def sum_pr(
    org: Optional[str] = None,
    repo_name: Optional[str] = None,
    pr_number: Optional[int] = None,
    context_only: bool = False,
) -> None:
    """Execute PR summarization.

    Args:
        org: Optional org name. Use "." to match all orgs. If None, processes all orgs.
        repo_name: Optional repo name. Use "." to match all repos. If None, processes all repos.
        pr_number: Optional specific PR number. If None, processes all PRs for the repo(s).
        context_only: If True, only collect context and skip LLM generation
    """
    # Load config
    config = load_configs()

    # Get repos to process (with org filtering)
    repos = get_repos_from_config(config, org, repo_name)
    if not repos:
        return

    # Load prompt once before processing PRs
    prompt_path = config.get("prompts", {}).get("sum_pr", "prompts/sum.pr.txt")
    prompt_template = load_prompt_file(prompt_path)

    # Get cache files config
    cache_files_config = config.get("cache_files", {}).get("sum_pr", {})

    # Get LLM client once if not in context_only mode
    llm = None if context_only else get_llm_client()

    # Process each repo
    for repo in repos:
        current_repo_name = repo.get("name")
        current_org = repo.get("org")
        if not current_repo_name or not current_org:
            click.echo("Skipping invalid repo entry (missing name or org)", err=True)
            continue

        pull_requests = repo.get("pull_requests", [])

        # Filter to specific PR if provided
        if pr_number is not None:
            if pr_number not in pull_requests:
                click.echo(
                    f"Error: PR #{pr_number} not found in configs.json for repo '{current_org}/{current_repo_name}'",
                    err=True,
                )
                continue
            prs_to_process = [pr_number]
        else:
            prs_to_process = pull_requests

        # Process each PR for this repo
        for pr in prs_to_process:
            if not isinstance(pr, int):
                click.echo(f"Skipping invalid PR number: {pr}", err=True)
                continue

            summarize_pr(
                current_repo_name,
                current_org,
                pr,
                prompt_template,
                cache_files_config,
                llm,
                context_only,
            )

    click.echo("Done.")
