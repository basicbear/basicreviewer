"""Extract command for crev CLI - extracts PR files and diffs."""

import json
from pathlib import Path

import click

from .extract_pr import extract_pr_files


@click.command()
def extract() -> None:
    """Extract PR files and diffs from pulled repositories."""
    repos_file = Path("repos.json")

    if not repos_file.exists():
        click.echo("Error: repos.json not found. Run 'crev init' first.", err=True)
        raise SystemExit(1)

    with open(repos_file) as f:
        data = json.load(f)

    repos_dir = Path("repos")
    if not repos_dir.exists():
        click.echo("Error: repos directory not found. Run 'crev pull' first.", err=True)
        raise SystemExit(1)

    # Create pullrequests directory
    output_dir = Path("pullrequests")
    output_dir.mkdir(exist_ok=True)

    # Loop through each repo and extract PRs
    for repo in data.get("repos", []):
        extract_pr_files(repo, repos_dir, output_dir)

    click.echo("Done.")
