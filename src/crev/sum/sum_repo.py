"""Repo summarization subcommand for the sum command."""

import json
import subprocess
from pathlib import Path
from typing import Any, Optional

import click

from crev.utils.ai.llm import get_llm_client
from crev.utils.context.collector import file_category as collect_file_category
from crev.utils.context.collector.repo import repo as collect_repo_context
from crev.utils.context.collector.repo import structure as collect_structure_context

from .util import (
    ensure_directory_exists,
    get_repos_from_config,
    load_configs,
    load_prompt_file,
    should_skip_existing,
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


def _save_context_file(context: str, output_path: Path) -> None:
    """Save context to a file.

    Args:
        context: The context content
        output_path: Path to save the context
    """
    output_path.write_text(context)
    click.echo(f"  Context saved to: {output_path}")


def _phase1_categorize_files(
    repo_path: Path,
    output_dir: Path,
    prompts_config: dict,
    llm: Optional[Any],
    context_only: bool,
) -> Optional[dict[str, list[str]]]:
    """Phase 1: Categorize repository files into app/test/infra.

    Args:
        repo_path: Path to the repository
        output_dir: Directory for output files
        prompts_config: Prompts configuration dictionary
        llm: LLM client instance (None if context_only)
        context_only: If True, only collect context

    Returns:
        Dictionary mapping categories to file lists, or None if aborted
    """
    click.echo("  Phase 1: Categorizing files...")

    categorization_context_file = output_dir / "sum_repo.categorization.context.md"
    categorization_result_file = output_dir / "sum_repo.categorization.json"

    # Check for cached categorization
    if categorization_result_file.exists():
        click.echo("  Loading cached file categorization...")
        file_categories = json.loads(categorization_result_file.read_text())
    elif context_only:
        # In context-only mode, we need the categorization to proceed
        click.echo(
            "  Error: No categorization file found. "
            "Run without --context-only first to generate file categorization.",
            err=True,
        )
        return None
    else:
        # Collect file listing context
        file_listing_context = collect_file_category(repo_path)
        _save_context_file(file_listing_context, categorization_context_file)

        # Get categorization from LLM
        prompt_path = prompts_config.get(
            "sum_repo_file_category", "prompts/sum_repo_file_category.txt"
        )
        prompt_template = load_prompt_file(prompt_path)
        full_prompt = f"{prompt_template}\n\n{file_listing_context}"

        click.echo("  Requesting file categorization from LLM...")
        response = _invoke_llm(llm, full_prompt)
        file_categories = _parse_file_categories(response)

        # Save categorization result
        categorization_result_file.write_text(json.dumps(file_categories, indent=2))
        click.echo(f"  Categorization saved to: {categorization_result_file}")

    # Log category counts
    for cat in ["app", "test", "infra"]:
        count = len(file_categories.get(cat, []))
        click.echo(f"    {cat}: {count} files")

    return file_categories


def _phase2_summarize_structure(
    file_categories: dict[str, list[str]],
    output_dir: Path,
    prompts_config: dict,
    llm: Optional[Any],
    context_only: bool,
) -> str:
    """Phase 2: Summarize repository structure.

    Args:
        file_categories: Dictionary mapping categories to file lists
        output_dir: Directory for output files
        prompts_config: Prompts configuration dictionary
        llm: LLM client instance (None if context_only)
        context_only: If True, only collect context

    Returns:
        Structure summary string (empty if context_only)
    """
    click.echo("  Phase 2: Summarizing repository structure...")

    structure_context_file = output_dir / "sum_repo.structure.context.md"
    structure_result_file = output_dir / "sum_repo.structure.md"

    # Check for cached context or collect new context
    if structure_context_file.exists():
        click.echo("  Loading cached structure context...")
        structure_context = structure_context_file.read_text()
    else:
        structure_context = collect_structure_context(file_categories)
        _save_context_file(structure_context, structure_context_file)

    if context_only:
        return ""

    if structure_result_file.exists():
        click.echo("  Loading cached structure summary...")
        return structure_result_file.read_text()

    prompt_path = prompts_config.get(
        "sum_repo_structure", "prompts/sum_repo_structure.txt"
    )
    prompt_template = load_prompt_file(prompt_path)
    full_prompt = f"{prompt_template}\n\n{structure_context}"

    click.echo("  Requesting structure summary from LLM...")
    structure_summary = _invoke_llm(llm, full_prompt)
    structure_result_file.write_text(structure_summary)
    click.echo(f"  Structure summary saved to: {structure_result_file}")

    return structure_summary


def _phase3_analyze_categories(
    repo_path: Path,
    file_categories: dict[str, list[str]],
    output_dir: Path,
    prompts_config: dict,
    llm: Optional[Any],
    context_only: bool,
) -> dict[str, str]:
    """Phase 3: Analyze code by category (app/test/infra).

    Args:
        repo_path: Path to the repository
        file_categories: Dictionary mapping categories to file lists
        output_dir: Directory for output files
        prompts_config: Prompts configuration dictionary
        llm: LLM client instance (None if context_only)
        context_only: If True, only collect context

    Returns:
        Dictionary mapping categories to their summaries (empty if context_only)
    """
    click.echo("  Phase 3: Analyzing code by category...")

    category_summaries = {}
    categories = ["app", "test", "infra"]

    for category in categories:
        files = file_categories.get(category, [])
        if not files:
            click.echo(f"    Skipping {category} (no files)")
            continue

        click.echo(f"    Processing {category} files ({len(files)} files)...")

        context_file = output_dir / f"sum_repo.{category}.context.md"
        result_file = output_dir / f"sum_repo.{category}.md"

        # Check for cached context or collect new context
        if context_file.exists():
            click.echo(f"    Loading cached {category} context...")
            category_context = context_file.read_text()
        else:
            category_context = collect_repo_context(repo_path, files, category=category)
            _save_context_file(category_context, context_file)

        if context_only:
            continue

        if result_file.exists():
            click.echo(f"    Loading cached {category} summary...")
            category_summaries[category] = result_file.read_text()
        else:
            prompt_path = prompts_config.get(
                f"sum_repo_{category}", f"prompts/sum_repo_{category}.txt"
            )
            prompt_template = load_prompt_file(prompt_path)
            full_prompt = f"{prompt_template}\n\n{category_context}"

            click.echo(f"    Requesting {category} analysis from LLM...")
            summary = _invoke_llm(llm, full_prompt)
            result_file.write_text(summary)
            category_summaries[category] = summary
            click.echo(f"    {category.title()} summary saved to: {result_file}")

    return category_summaries


def _combine_output(
    repo_name: str,
    commit_count: int,
    short_hash: str,
    structure_summary: str,
    category_summaries: dict[str, str],
    output_file: Path,
) -> None:
    """Combine all summaries into the final output file.

    Args:
        repo_name: Name of the repository
        commit_count: Number of commits in the repository
        short_hash: Short git hash of current commit
        structure_summary: Repository structure summary
        category_summaries: Dictionary mapping categories to summaries
        output_file: Path to the final output file
    """
    click.echo("  Combining summaries...")

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

    final_output = "\n".join(output_parts)
    output_file.write_text(final_output)
    click.echo(f"  Final summary saved to: {output_file}")


def summarize_repo(
    repo_name: str,
    config: dict,
    llm: Optional[Any] = None,
    context_only: bool = False,
) -> None:
    """Summarize a single repository using multi-phase analysis.

    Phase 1: File categorization (test/app/infra)
    Phase 2: Structure summarization
    Phase 3: Category-specific analysis (app, test, infra)

    Args:
        repo_name: Name of the repository
        config: Configuration dictionary
        llm: Optional LLM client instance (required if not context_only)
        context_only: If True, only collect context and skip LLM generation
    """
    click.echo(f"Summarizing repository: {repo_name}")

    # Check if repos directory exists
    repos_dir = Path("repos")
    if not repos_dir.exists():
        click.echo(
            "  Error: repos directory not found. Run 'crev pull' first.", err=True
        )
        return

    repo_path = repos_dir / repo_name
    if not repo_path.exists():
        click.echo(
            f"  Error: Repository '{repo_name}' not found in repos directory.", err=True
        )
        return

    # Get git version info for output filename
    commit_count, short_hash = _get_git_version_info(repo_path)

    # Create output directory
    output_dir = Path("pullrequests") / repo_name / "sum"
    ensure_directory_exists(output_dir)

    # Check if output file exists
    output_file = output_dir / f"sum.repo.{commit_count}.{short_hash}.ai.md"
    if not context_only and should_skip_existing(output_file):
        return

    # Load prompts config
    prompts_config = config.get("prompts", {})

    # Phase 1: File Categorization
    file_categories = _phase1_categorize_files(
        repo_path, output_dir, prompts_config, llm, context_only
    )
    if file_categories is None:
        return

    # Phase 2: Structure Summarization
    structure_summary = _phase2_summarize_structure(
        file_categories, output_dir, prompts_config, llm, context_only
    )

    # Phase 3: Category-specific Analysis
    category_summaries = _phase3_analyze_categories(
        repo_path, file_categories, output_dir, prompts_config, llm, context_only
    )

    # Combine Output
    if context_only:
        click.echo("  Context collection complete (--context-only mode)")
        return

    _combine_output(
        repo_name,
        commit_count,
        short_hash,
        structure_summary,
        category_summaries,
        output_file,
    )


def sum_repo(repo_name: Optional[str] = None, context_only: bool = False) -> None:
    """Execute repo summarization.

    Args:
        repo_name: Optional specific repo name. If None, processes all repos.
        context_only: If True, only collect context and skip LLM generation
    """
    # Load config
    config = load_configs()

    # Get repos to process
    repos = get_repos_from_config(config, repo_name)

    # Get LLM client once if not in context_only mode
    llm = None if context_only else get_llm_client()

    # Process each repo
    for repo in repos:
        name = repo.get("name")
        if not name:
            click.echo("Skipping invalid repo entry (missing name)", err=True)
            continue

        summarize_repo(name, config, llm, context_only)

    click.echo("Done.")
