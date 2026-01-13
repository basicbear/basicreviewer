"""Pull command for crev CLI."""

import json
import subprocess
from pathlib import Path

import click


def getRepo(repo: dict, repos_dir: Path) -> None:
    """Clone or pull a single repo.

    Args:
        repo: Single repo object from repos.json
        repos_dir: Directory to clone repos into
    """
    name = repo.get("name")
    url = repo.get("url")

    if not name or not url:
        click.echo(f"Skipping invalid repo entry: {repo}", err=True)
        return

    repo_path = repos_dir / name

    if repo_path.exists():
        click.echo(f"Pulling updates for {name}...")
        subprocess.run(["git", "pull"], cwd=repo_path, check=True)
    else:
        click.echo(f"Cloning {name}...")
        subprocess.run(["git", "clone", url, str(repo_path)], check=True)


def getPullRequest(repo: dict, repos_dir: Path) -> None:
    """Fetch pull requests for a single repo.

    Args:
        repo: Single repo object from repos.json
        repos_dir: Directory containing cloned repos
    """
    name = repo.get("name")
    pull_requests = repo.get("pull_requests", [])

    if not name:
        return

    repo_path = repos_dir / name

    if not repo_path.exists():
        click.echo(f"Skipping PRs for {name} (repo not found)", err=True)
        return

    # Get list of existing branches
    result = subprocess.run(
        ["git", "branch", "--list"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    existing_branches = {
        branch.strip().lstrip("* ") for branch in result.stdout.splitlines()
    }

    for pr_number in pull_requests:
        if not isinstance(pr_number, int):
            click.echo(f"Skipping invalid PR number in {name}: {pr_number}", err=True)
            continue

        local_branch = f"crev-pr-{pr_number}"

        if local_branch in existing_branches:
            click.echo(f"Branch {local_branch} already exists for {name}, skipping...")
            continue

        click.echo(f"Fetching PR #{pr_number} for {name} into {local_branch}...")
        try:
            subprocess.run(
                ["git", "fetch", "origin", f"pull/{pr_number}/head:{local_branch}"],
                cwd=repo_path,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            click.echo(f"Failed to fetch PR #{pr_number}: {e}", err=True)


@click.command()
def pull() -> None:
    """Pull all repos defined in configs.json into a repos folder."""
    configs_file = Path("configs.json")

    if not configs_file.exists():
        click.echo("Error: configs.json not found. Run 'crev init' first.", err=True)
        raise SystemExit(1)

    with open(configs_file) as f:
        data = json.load(f)

    repos_dir = Path("repos")
    repos_dir.mkdir(exist_ok=True)

    # Loop through each repo and process it
    for repo in data.get("repos", []):
        # Step 1: Get repo (clone or pull)
        getRepo(repo, repos_dir)

        # Step 2: Get pull requests for this repo
        getPullRequest(repo, repos_dir)

    click.echo("Done.")
