"""Cache utilities for crev."""

from pathlib import Path
from typing import Callable, Optional, TypeVar

import click

T = TypeVar("T")


def cache_file_check(
    output_dir: Path,
    cache_files_config: dict,
    cache_key: str,
    task: Callable[[], T],
    default_filename: str,
    bypass_keys: Optional[list[str]] = None,
    parser: Optional[Callable[[str], T]] = None,
    format_args: Optional[dict] = None,
) -> T:
    """Check for cached results or run a task to generate them.

    This function provides a standardized way to check for existing results.
    It will:
    1. Return cached content if cache file exists
    2. Skip and return None if any bypass file exists
    3. Otherwise, run the task function and save the result to cache file

    Args:
        output_dir: Directory where cache files are stored.
        cache_files_config: Dictionary mapping cache keys to filenames.
        cache_key: Key to look up in cache_files_config for the cache filename.
        task: Function to run to generate the cached value. The return value
              will be written to cache file.
        default_filename: Default filename if cache_key not in config.
        bypass_keys: Optional list of cache keys that, if their files exist,
                     will cause the task to be skipped (returns None).
        parser: Optional function to parse the file content into the desired type.
                Defaults to returning the raw string content.
        format_args: Optional dict of args to format filename templates.

    Returns:
        The content from cache file (if it exists), None (if bypass files exist),
        or the result from running the task function.
    """
    # Build cache file path
    filename = cache_files_config.get(cache_key, default_filename)
    if format_args:
        filename = filename.format(**format_args)
    cache_file = output_dir / filename

    # Check if cache file already exists
    if cache_file.exists():
        click.echo(f"  Loading cached result from: {cache_file}")
        content = cache_file.read_text()
        return parser(content) if parser else content

    # Check if any bypass files exist
    if bypass_keys:
        for bypass_key in bypass_keys:
            bypass_filename = cache_files_config.get(bypass_key)
            if bypass_filename:
                if format_args:
                    bypass_filename = bypass_filename.format(**format_args)
                bypass_file = output_dir / bypass_filename
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

    return parser(result) if parser else result
