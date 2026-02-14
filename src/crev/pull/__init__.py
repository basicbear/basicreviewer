"""Pull command for crev CLI."""

import json
from pathlib import Path

import click
import pygit2


def getRepo(repo: dict, repos_dir: Path) -> None:
    """Clone or pull a single repo.

    Args:
        repo: Single repo object from repos.json
        repos_dir: Directory to clone repos into
    """
    name = repo.get("name")
    url = repo.get("url")
    org = repo.get("org")

    if not name or not url or not org:
        click.echo(f"Skipping invalid repo entry: {repo}", err=True)
        return

    org_dir = repos_dir / org
    org_dir.mkdir(parents=True, exist_ok=True)
    repo_path = org_dir / name

    if repo_path.exists():
        click.echo(f"Pulling updates for {name}...")
        repository = pygit2.Repository(str(repo_path))
        remote = repository.remotes["origin"]
        remote.fetch()
        # Fast-forward the current branch to the remote tracking branch
        branch_name = repository.head.shorthand
        remote_ref = repository.references.get(
            f"refs/remotes/origin/{branch_name}"
        )
        if remote_ref is not None:
            repository.checkout_tree(repository.get(remote_ref.target))
            ref = repository.references.get(f"refs/heads/{branch_name}")
            if ref is not None:
                ref.set_target(remote_ref.target)
            repository.head.set_target(remote_ref.target)
    else:
        click.echo(f"Cloning {name}...")
        pygit2.clone_repository(url, str(repo_path))


def getPullRequest(repo: dict, repos_dir: Path) -> None:
    """Fetch pull requests for a single repo.

    Args:
        repo: Single repo object from repos.json
        repos_dir: Directory containing cloned repos
    """
    name = repo.get("name")
    org = repo.get("org")
    pull_requests = repo.get("pull_requests", [])

    if not name or not org:
        return

    repo_path = repos_dir / org / name

    if not repo_path.exists():
        click.echo(f"Skipping PRs for {name} (repo not found)", err=True)
        return

    repository = pygit2.Repository(str(repo_path))
    existing_branches = set(repository.branches.local)

    remote = repository.remotes["origin"]

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
            remote.fetch(
                [f"+refs/pull/{pr_number}/head:refs/heads/{local_branch}"]
            )
        except pygit2.GitError as e:
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
