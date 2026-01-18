"""File categorization context collector for repo summarization."""

import fnmatch
from pathlib import Path
from typing import Optional

import click


def _load_gitignore_patterns(repo_path: Path) -> list[str]:
    """Load patterns from .gitignore file.

    Args:
        repo_path: Path to the repository

    Returns:
        List of gitignore patterns
    """
    gitignore_file = repo_path / ".gitignore"
    patterns = []

    if gitignore_file.exists():
        try:
            content = gitignore_file.read_text()
            for line in content.splitlines():
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith("#"):
                    patterns.append(line)
        except Exception as e:
            click.echo(f"  Warning: Could not read .gitignore: {e}", err=True)

    return patterns


def _is_ignored(file_path: str, patterns: list[str]) -> bool:
    """Check if a file path matches any gitignore pattern.

    Args:
        file_path: Relative file path to check
        patterns: List of gitignore patterns

    Returns:
        True if file should be ignored
    """
    # Always ignore common directories
    always_ignore = [
        ".git",
        ".git/*",
        "*/.git/*",
        "__pycache__",
        "__pycache__/*",
        "*/__pycache__/*",
        "node_modules",
        "node_modules/*",
        "*/node_modules/*",
        ".venv",
        ".venv/*",
        "*/.venv/*",
        "venv",
        "venv/*",
        "*/venv/*",
        "*.pyc",
        "*.pyo",
        ".DS_Store",
    ]

    all_patterns = always_ignore + patterns

    for pattern in all_patterns:
        # Handle directory patterns
        if pattern.endswith("/"):
            pattern = pattern[:-1]
            if fnmatch.fnmatch(file_path, pattern) or fnmatch.fnmatch(
                file_path, f"{pattern}/*"
            ):
                return True
            if f"/{pattern}/" in f"/{file_path}/" or file_path.startswith(f"{pattern}/"):
                return True
        else:
            if fnmatch.fnmatch(file_path, pattern):
                return True
            # Check if pattern matches any part of the path
            if fnmatch.fnmatch(file_path, f"*/{pattern}"):
                return True
            if fnmatch.fnmatch(file_path, f"{pattern}/*"):
                return True

    return False


def file_category(repo_path: Path, gitignore_content: Optional[str] = None) -> str:
    """Collect file listing context for LLM-based categorization.

    This function collects all files in a repository (excluding those matched
    by .gitignore patterns) and formats them for the LLM to categorize as
    'test', 'app', or 'infra'.

    Args:
        repo_path: Path to the repository
        gitignore_content: Optional pre-loaded gitignore content

    Returns:
        Markdown-formatted string with file listing for categorization
    """
    context_parts = []
    context_parts.append("# Repository Files for Categorization\n")

    # Load gitignore patterns
    patterns = _load_gitignore_patterns(repo_path)

    # Collect all files
    all_files = []
    try:
        for file_path in repo_path.rglob("*"):
            if file_path.is_file():
                rel_path = str(file_path.relative_to(repo_path))
                if not _is_ignored(rel_path, patterns):
                    all_files.append(rel_path)
    except Exception as e:
        click.echo(f"  Warning: Error scanning repository: {e}", err=True)

    # Sort files for consistent output
    all_files.sort()

    # Add gitignore info
    if patterns:
        context_parts.append("## .gitignore Patterns Applied\n")
        context_parts.append("```")
        context_parts.append("\n".join(patterns[:20]))  # Limit to first 20 patterns
        if len(patterns) > 20:
            context_parts.append(f"... and {len(patterns) - 20} more patterns")
        context_parts.append("```\n")

    # Add file listing
    context_parts.append("## Files to Categorize\n")
    context_parts.append(
        "Please categorize each file as `test`, `app`, or `infra`.\n"
    )
    context_parts.append("```")
    for file_path in all_files:
        context_parts.append(file_path)
    context_parts.append("```\n")

    context_parts.append(f"\nTotal files: {len(all_files)}")

    return "\n".join(context_parts)
