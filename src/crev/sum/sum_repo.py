"""Repo summarization subcommand for the sum command."""

import json
import subprocess
from pathlib import Path
from typing import Any, Optional

import click

from crev.utils import cache_file_check
from crev.utils.ai.llm import get_llm_client
from crev.utils.context.collector import file_category as collect_file_category
from crev.utils.context.collector.repo import repo as collect_repo_context
from crev.utils.context.collector.repo import structure as collect_structure_context

from .util import (
    ensure_directory_exists,
    get_repos_from_config,
    load_configs,
    load_prompt_file,
)


def _get_git_version_info(repo_path: Path) -> tuple[int, str]:
    """Get commit count and short hash from the repository.

    Args:
        repo_path: Path to the repository

    Returns:
        Tuple of (commit_count, short_hash)
    """
    try:
        # Get commit count
        result = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        commit_count = int(result.stdout.strip())

        # Get short hash (first 10 characters)
        result = subprocess.run(
            ["git", "rev-parse", "--short=10", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        short_hash = result.stdout.strip()

        return commit_count, short_hash
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError) as e:
        click.echo(f"  Warning: Could not get git version info: {e}", err=True)
        return 0, "unknown"


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


def _parse_file_categories(llm_response: str) -> dict[str, list[str]]:
    """Parse the LLM's file categorization response.

    Args:
        llm_response: The LLM's JSON response

    Returns:
        Dictionary mapping categories to file lists
    """
    # Try to extract JSON from the response
    try:
        # Look for JSON in the response
        start_idx = llm_response.find("{")
        end_idx = llm_response.rfind("}") + 1
        if start_idx != -1 and end_idx > start_idx:
            json_str = llm_response[start_idx:end_idx]
            return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    # If parsing fails, return empty categories
    click.echo("  Warning: Could not parse file categorization response", err=True)
    return {"app": [], "test": [], "infra": []}


def _phase1_collect_context(
    repo_path: Path,
    output_dir: Path,
    cache_files_config: dict,
    format_args: dict,
) -> Optional[str]:
    """Phase 1a: Collect file listing context for categorization.

    Args:
        repo_path: Path to the repository
        output_dir: Directory for cache files
        cache_files_config: Cache file configuration
        format_args: Format arguments for filename templates

    Returns:
        File listing context string, or None if skipped
    """
    click.echo("  Phase 1a: Collecting file listing context...")

    def collect_task() -> str:
        click.echo("  Collecting file listing...")
        return collect_file_category(repo_path)

    return cache_file_check(
        output_dir=output_dir,
        cache_files_config=cache_files_config,
        cache_key="categorization_context",
        task=collect_task,
        default_filename="sum_repo.categorization.context.md",
        bypass_keys=[
            "categorization_result",
            "structure_context",
            "structure_result",
            "app_context",
            "app_result",
            "test_context",
            "test_result",
            "infra_context",
            "infra_result",
            "output",
        ],
        format_args=format_args,
    )


def _phase1_categorize_files(
    file_listing_context: str,
    prompts_config: dict,
    llm: Any,
    output_dir: Path,
    cache_files_config: dict,
    format_args: dict,
) -> Optional[dict[str, list[str]]]:
    """Phase 1b: Categorize repository files into app/test/infra.

    Args:
        file_listing_context: The file listing context from phase 1a
        prompts_config: Prompts configuration dictionary
        llm: LLM client instance
        output_dir: Directory for cache files
        cache_files_config: Cache file configuration
        format_args: Format arguments for filename templates

    Returns:
        Dictionary mapping categories to file lists, or None if skipped
    """
    click.echo("  Phase 1b: Categorizing files...")

    def categorize_task() -> str:
        prompt_path = prompts_config.get(
            "sum_repo_file_category", "prompts/sum_repo_file_category.txt"
        )
        prompt_template = load_prompt_file(prompt_path)
        full_prompt = f"{prompt_template}\n\n{file_listing_context}"

        click.echo("  Requesting file categorization from LLM...")
        response = _invoke_llm(llm, full_prompt)
        file_categories = _parse_file_categories(response)
        return json.dumps(file_categories, indent=2)

    result = cache_file_check(
        output_dir=output_dir,
        cache_files_config=cache_files_config,
        cache_key="categorization_result",
        task=categorize_task,
        default_filename="sum_repo.categorization.json",
        bypass_keys=[
            "structure_context",
            "structure_result",
            "app_context",
            "app_result",
            "test_context",
            "test_result",
            "infra_context",
            "infra_result",
            "output",
        ],
        parser=json.loads,
        format_args=format_args,
    )

    if result is not None:
        # Log category counts
        for cat in ["app", "test", "infra"]:
            count = len(result.get(cat, []))
            click.echo(f"    {cat}: {count} files")

    return result


def _phase2_collect_structure_context(
    file_categories: dict[str, list[str]],
    output_dir: Path,
    cache_files_config: dict,
    format_args: dict,
) -> Optional[str]:
    """Phase 2a: Collect structure context.

    Args:
        file_categories: Dictionary mapping categories to file lists
        output_dir: Directory for cache files
        cache_files_config: Cache file configuration
        format_args: Format arguments for filename templates

    Returns:
        Structure context string, or None if skipped
    """
    click.echo("  Phase 2a: Collecting structure context...")

    def collect_task() -> str:
        click.echo("  Collecting structure information...")
        return collect_structure_context(file_categories)

    return cache_file_check(
        output_dir=output_dir,
        cache_files_config=cache_files_config,
        cache_key="structure_context",
        task=collect_task,
        default_filename="sum_repo.structure.context.md",
        bypass_keys=[
            "structure_result",
            "app_context",
            "app_result",
            "test_context",
            "test_result",
            "infra_context",
            "infra_result",
            "output",
        ],
        format_args=format_args,
    )


def _phase2_summarize_structure(
    structure_context: str,
    prompts_config: dict,
    llm: Any,
    output_dir: Path,
    cache_files_config: dict,
    format_args: dict,
) -> Optional[str]:
    """Phase 2b: Summarize repository structure.

    Args:
        structure_context: The structure context from phase 2a
        prompts_config: Prompts configuration dictionary
        llm: LLM client instance
        output_dir: Directory for cache files
        cache_files_config: Cache file configuration
        format_args: Format arguments for filename templates

    Returns:
        Structure summary string, or None if skipped
    """
    click.echo("  Phase 2b: Summarizing repository structure...")

    def summarize_task() -> str:
        prompt_path = prompts_config.get(
            "sum_repo_structure", "prompts/sum_repo_structure.txt"
        )
        prompt_template = load_prompt_file(prompt_path)
        full_prompt = f"{prompt_template}\n\n{structure_context}"

        click.echo("  Requesting structure summary from LLM...")
        return _invoke_llm(llm, full_prompt)

    return cache_file_check(
        output_dir=output_dir,
        cache_files_config=cache_files_config,
        cache_key="structure_result",
        task=summarize_task,
        default_filename="sum_repo.structure.md",
        bypass_keys=[
            "app_context",
            "app_result",
            "test_context",
            "test_result",
            "infra_context",
            "infra_result",
            "output",
        ],
        format_args=format_args,
    )


def _phase3_collect_category_context(
    repo_path: Path,
    file_categories: dict[str, list[str]],
    category: str,
    output_dir: Path,
    cache_files_config: dict,
    format_args: dict,
) -> Optional[str]:
    """Phase 3a: Collect context for a specific category.

    Args:
        repo_path: Path to the repository
        file_categories: Dictionary mapping categories to file lists
        category: The category to process (app, test, or infra)
        output_dir: Directory for cache files
        cache_files_config: Cache file configuration
        format_args: Format arguments for filename templates

    Returns:
        Category context string, or None if skipped
    """
    files = file_categories.get(category, [])
    if not files:
        click.echo(f"    Skipping {category} (no files)")
        return None

    click.echo(f"  Phase 3a: Collecting {category} context ({len(files)} files)...")

    # Build bypass keys for categories that come after this one
    all_categories = ["app", "test", "infra"]
    cat_idx = all_categories.index(category)
    bypass_keys = [f"{category}_result"]
    for later_cat in all_categories[cat_idx + 1 :]:
        bypass_keys.extend([f"{later_cat}_context", f"{later_cat}_result"])
    bypass_keys.append("output")

    def collect_task() -> str:
        click.echo(f"    Collecting {category} file contents...")
        return collect_repo_context(repo_path, files, category=category)

    return cache_file_check(
        output_dir=output_dir,
        cache_files_config=cache_files_config,
        cache_key=f"{category}_context",
        task=collect_task,
        default_filename=f"sum_repo.{category}.context.md",
        bypass_keys=bypass_keys,
        format_args=format_args,
    )


def _phase3_analyze_category(
    category_context: str,
    category: str,
    prompts_config: dict,
    llm: Any,
    output_dir: Path,
    cache_files_config: dict,
    format_args: dict,
) -> Optional[str]:
    """Phase 3b: Analyze a specific category.

    Args:
        category_context: The context from phase 3a
        category: The category to process (app, test, or infra)
        prompts_config: Prompts configuration dictionary
        llm: LLM client instance
        output_dir: Directory for cache files
        cache_files_config: Cache file configuration
        format_args: Format arguments for filename templates

    Returns:
        Category summary string, or None if skipped
    """
    click.echo(f"  Phase 3b: Analyzing {category} code...")

    # Build bypass keys for categories that come after this one
    all_categories = ["app", "test", "infra"]
    cat_idx = all_categories.index(category)
    bypass_keys = []
    for later_cat in all_categories[cat_idx + 1 :]:
        bypass_keys.extend([f"{later_cat}_context", f"{later_cat}_result"])
    bypass_keys.append("output")

    def analyze_task() -> str:
        prompt_path = prompts_config.get(
            f"sum_repo_{category}", f"prompts/sum_repo_{category}.txt"
        )
        prompt_template = load_prompt_file(prompt_path)
        full_prompt = f"{prompt_template}\n\n{category_context}"

        click.echo(f"    Requesting {category} analysis from LLM...")
        return _invoke_llm(llm, full_prompt)

    return cache_file_check(
        output_dir=output_dir,
        cache_files_config=cache_files_config,
        cache_key=f"{category}_result",
        task=analyze_task,
        default_filename=f"sum_repo.{category}.md",
        bypass_keys=bypass_keys,
        format_args=format_args,
    )


def _combine_output(
    repo_name: str,
    commit_count: int,
    short_hash: str,
    structure_summary: str,
    category_summaries: dict[str, str],
    output_dir: Path,
    cache_files_config: dict,
    format_args: dict,
) -> Optional[str]:
    """Combine all summaries into the final output file.

    Args:
        repo_name: Name of the repository
        commit_count: Number of commits in the repository
        short_hash: Short git hash of current commit
        structure_summary: Repository structure summary
        category_summaries: Dictionary mapping categories to summaries
        output_dir: Directory for cache files
        cache_files_config: Cache file configuration
        format_args: Format arguments for filename templates

    Returns:
        Final combined output string, or None if skipped
    """
    click.echo("  Combining summaries...")

    def combine_task() -> str:
        categories = ["app", "test", "infra"]

        # Build final output
        output_parts = [
            f"# Repository Summary: {repo_name}",
            f"\n*Generated from commit #{commit_count} ({short_hash})*\n",
            "---\n",
            "## Repository Structure\n",
            structure_summary,
            "\n---\n",
        ]

        for category in categories:
            if category in category_summaries:
                output_parts.append(f"## {category.title()} Analysis\n")
                output_parts.append(category_summaries[category])
                output_parts.append("\n---\n")

        return "\n".join(output_parts)

    return cache_file_check(
        output_dir=output_dir,
        cache_files_config=cache_files_config,
        cache_key="output",
        task=combine_task,
        default_filename="sum.repo.{commit_count}.{short_hash}.ai.md",
        format_args=format_args,
    )


def summarize_repo(
    repo_name: str,
    org: str,
    config: dict,
    cache_files_config: dict,
    llm: Optional[Any] = None,
    context_only: bool = False,
) -> None:
    """Summarize a single repository using multi-phase analysis.

    Phase 1: File categorization (test/app/infra)
    Phase 2: Structure summarization
    Phase 3: Category-specific analysis (app, test, infra)

    Args:
        repo_name: Name of the repository
        org: Organization name for the repository
        config: Configuration dictionary
        cache_files_config: Cache file name configuration from configs.json
        llm: Optional LLM client instance (required if not context_only)
        context_only: If True, only collect context and skip LLM generation
    """
    click.echo(f"Summarizing repository: {org}/{repo_name}")

    # Check if repos directory exists
    repos_dir = Path("repos")
    if not repos_dir.exists():
        click.echo(
            "  Error: repos directory not found. Run 'crev pull' first.", err=True
        )
        return

    repo_path = repos_dir / org / repo_name
    if not repo_path.exists():
        click.echo(
            f"  Error: Repository '{org}/{repo_name}' not found in repos directory.", err=True
        )
        return

    # Get git version info for output filename
    commit_count, short_hash = _get_git_version_info(repo_path)

    # Create output directory
    output_dir = Path("pullrequests") / org / repo_name / "sum"
    ensure_directory_exists(output_dir)

    # Format args for filename templates
    format_args = {"commit_count": commit_count, "short_hash": short_hash}

    # Load prompts config
    prompts_config = config.get("prompts", {})

    # Phase 1a: Collect file listing context
    file_listing_context = _phase1_collect_context(
        repo_path, output_dir, cache_files_config, format_args
    )

    if file_listing_context is None:
        # Skipped because later cache file exists
        return

    if context_only:
        click.echo("  Context collection complete (--context-only mode)")
        return

    # Phase 1b: Categorize files with LLM
    if llm is None:
        click.echo("  Error: LLM client not provided", err=True)
        raise ValueError("LLM client is required when not in context_only mode")

    file_categories = _phase1_categorize_files(
        file_listing_context,
        prompts_config,
        llm,
        output_dir,
        cache_files_config,
        format_args,
    )
    if file_categories is None:
        # Skipped because later cache file exists
        return

    # Phase 2a: Collect structure context
    structure_context = _phase2_collect_structure_context(
        file_categories, output_dir, cache_files_config, format_args
    )
    if structure_context is None:
        # Skipped because later cache file exists
        return

    # Phase 2b: Summarize structure with LLM
    structure_summary = _phase2_summarize_structure(
        structure_context,
        prompts_config,
        llm,
        output_dir,
        cache_files_config,
        format_args,
    )
    if structure_summary is None:
        # Skipped because later cache file exists
        return

    # Phase 3: Category-specific Analysis
    category_summaries: dict[str, str] = {}
    categories = ["app", "test", "infra"]

    for category in categories:
        # Phase 3a: Collect category context
        category_context = _phase3_collect_category_context(
            repo_path,
            file_categories,
            category,
            output_dir,
            cache_files_config,
            format_args,
        )
        if category_context is None:
            # Either no files or skipped because later cache exists
            continue

        # Phase 3b: Analyze category with LLM
        category_summary = _phase3_analyze_category(
            category_context,
            category,
            prompts_config,
            llm,
            output_dir,
            cache_files_config,
            format_args,
        )
        if category_summary is not None:
            category_summaries[category] = category_summary

    # Combine Output
    _combine_output(
        repo_name,
        commit_count,
        short_hash,
        structure_summary,
        category_summaries,
        output_dir,
        cache_files_config,
        format_args,
    )


def sum_repo(repo_name: Optional[str] = None, context_only: bool = False) -> None:
    """Execute repo summarization.

    Args:
        repo_name: Optional specific repo name. If None, processes all repos.
        context_only: If True, only collect context and skip LLM generation
    """
    # Load config
    config = load_configs()

    # Get cache files config for sum_repo
    cache_files_config = config.get("cache_files", {}).get("sum_repo", {})

    # Get repos to process
    repos = get_repos_from_config(config, repo_name)

    # Get LLM client once if not in context_only mode
    llm = None if context_only else get_llm_client()

    # Process each repo
    for repo in repos:
        name = repo.get("name")
        org = repo.get("org")
        if not name or not org:
            click.echo("Skipping invalid repo entry (missing name or org)", err=True)
            continue

        summarize_repo(name, org, config, cache_files_config, llm, context_only)

    click.echo("Done.")
