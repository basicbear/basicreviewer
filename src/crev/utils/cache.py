"""Cache utilities for crev."""

from pathlib import Path
from typing import Callable, Optional, TypeVar

import click

T = TypeVar("T")


def cache_file_check(
    cache_file: Path,
    task: Callable[[], T],
    other_bypass_files: Optional[list[Path]] = None,
    parser: Optional[Callable[[str], T]] = None,
) -> T:
    """Check for cached results or run a task to generate them.

    This function provides a standardized way to check for existing results.
    It will:
    1. Return cached content if cache_file exists
    2. Skip and return None if any file in other_bypass_files exists
    3. Otherwise, run the task function and save the result to cache_file

    Args:
        cache_file: Path to the output file. If it exists, its content is returned.
        task: Function to run to generate the cached value. The return value
              will be written to cache_file.
        other_bypass_files: Optional list of files that, if any exist, will cause
                           the task to be skipped (returns None without running task).
        parser: Optional function to parse the file content into the desired type.
                Defaults to returning the raw string content.

    Returns:
        The content from cache_file (if it exists), None (if bypass files exist),
        or the result from running the task function.
    """
    # Check if cache file already exists
    if cache_file.exists():
        click.echo(f"  Loading cached result from: {cache_file}")
        content = cache_file.read_text()
        return parser(content) if parser else content

    # Check if any bypass files exist
    if other_bypass_files:
        for bypass_file in other_bypass_files:
            if bypass_file.exists():
                click.echo(f"  Skipping task, bypass file exists: {bypass_file}")
                return None

    # Run the task and cache the result
    click.echo(f"  Running task, will cache to: {cache_file}")
    result = task()

    # Write result to cache file
    if result is not None:
        # Ensure parent directory exists
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(str(result))
        click.echo(f"  Cached result saved to: {cache_file}")

    return result
