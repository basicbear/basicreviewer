"""Repo summarization subcommand for the sum command."""

import subprocess
from pathlib import Path
from typing import Any, Optional

import click

from crev.utils.ai.llm import get_llm_client

from .util import (
    ensure_directory_exists,
    generate_summary_with_llm,
    get_repos_from_config,
    load_configs,
    load_prompt_file,
    should_skip_existing,
)


def collect_repo_context(repo_path: Path) -> str:
    """Collect context about a repository for summarization.

    Args:
        repo_path: Path to the repository

    Returns:
        String containing repository context (file structure, key files, etc.)
    """
    context_parts = []

    # Get directory structure
    try:
        result = subprocess.run(
            [
                "find",
                ".",
                "-type",
                "f",
                "-not",
                "-path",
                "*/.*",
                "-not",
                "-path",
                "*/node_modules/*",
                "-not",
                "-path",
                "*/venv/*",
                "-not",
                "-path",
                "*/__pycache__/*",
            ],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        context_parts.append("=== Repository Structure ===\n")
        context_parts.append(result.stdout)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        click.echo(f"  Warning: Could not get full repository structure: {e}", err=True)

    # Look for key files (README, package.json, pyproject.toml, etc.)
    key_files = [
        "README.md",
        "README.rst",
        "package.json",
        "pyproject.toml",
        "setup.py",
        "Cargo.toml",
        "go.mod",
        "pom.xml",
        "build.gradle",
    ]

    for filename in key_files:
        file_path = repo_path / filename
        if file_path.exists():
            try:
                content = file_path.read_text()
                context_parts.append(f"\n=== {filename} ===\n")
                context_parts.append(content)
            except Exception as e:
                click.echo(f"  Warning: Could not read {filename}: {e}", err=True)

    return "\n".join(context_parts)


def summarize_repo(repo_name: str, prompt_template: str, llm: Any) -> None:
    """Summarize a single repository.

    Args:
        repo_name: Name of the repository
        prompt_template: The prompt template string
        llm: LLM client instance
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

    # Create output directory
    output_dir = Path("pullrequests") / repo_name
    ensure_directory_exists(output_dir)

    # Check if output file exists
    output_file = output_dir / f"summary.{repo_name}.ai.txt"
    if should_skip_existing(output_file):
        return

    # Collect repository context
    click.echo("  Collecting repository context...")
    repo_context = collect_repo_context(repo_path)

    # Combine prompt and context
    full_prompt = f"{prompt_template}\n\n=== REPOSITORY CONTEXT ===\n{repo_context}"

    # Generate summary using the injected LLM client
    generate_summary_with_llm(llm, full_prompt, output_file)


def sum_repo(repo_name: Optional[str] = None) -> None:
    """Execute repo summarization.

    Args:
        repo_name: Optional specific repo name. If None, processes all repos.
    """
    # Load config
    config = load_configs()

    # Get repos to process
    repos = get_repos_from_config(config, repo_name)

    # Load prompt once before processing repos
    prompt_path = config.get("prompts", {}).get("sum_repo", "prompts/sum.repo.txt")
    prompt_template = load_prompt_file(prompt_path)

    # Get LLM client once before processing repos
    llm = get_llm_client()

    # Process each repo
    for repo in repos:
        name = repo.get("name")
        if not name:
            click.echo("Skipping invalid repo entry (missing name)", err=True)
            continue

        summarize_repo(name, prompt_template, llm)

    click.echo("Done.")
