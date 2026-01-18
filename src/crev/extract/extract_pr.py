"""Functions for extracting PR files and diffs."""

import subprocess
from pathlib import Path

import click

from .util import PRFolderStructure, extract_files_from_commit, get_pr_commit_info


def extract_pr_files(repo: dict, repos_dir: Path, output_dir: Path) -> None:
    """Extract files and diffs for PRs in a single repo.

    Args:
        repo: Single repo object from repos.json
        repos_dir: Directory containing cloned repos
        output_dir: Root pullrequests directory
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

    # Create org/repo subfolder in pullrequests
    repo_output_dir = output_dir / org / name
    repo_output_dir.mkdir(parents=True, exist_ok=True)

    for pr_number in pull_requests:
        if not isinstance(pr_number, int):
            click.echo(f"Skipping invalid PR number in {name}: {pr_number}", err=True)
            continue

        # Create PR folder structure
        pr_structure = PRFolderStructure(repo_output_dir, pr_number)

        if pr_structure.is_fully_extracted():
            click.echo(f"PR #{pr_number} for {name} already extracted, skipping...")
            continue

        click.echo(f"Extracting PR #{pr_number} for {name}...")

        # Check existence before creating directories
        code_existed = pr_structure.code_exists()
        diff_existed = pr_structure.diff_exists()

        pr_structure.create_directories()

        # Get the branch name for this PR
        local_branch = f"crev-pr-{pr_number}"

        try:
            # Get commit information for the PR
            commit_info = get_pr_commit_info(repo_path, local_branch)

            click.echo(f"  Merged commit: {commit_info.merged_commit[:8]}")
            click.echo(f"  Base commit: {commit_info.parent_commit[:8]}")
            click.echo(f"  PR commit: {commit_info.pr_commit[:8]}")

            # Get list of changed files
            result = subprocess.run(
                [
                    "git",
                    "diff",
                    f"{commit_info.parent_commit}...{commit_info.pr_commit}",
                    "--name-status",
                ],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )

            changed_files = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("\t", 1)
                if len(parts) == 2:
                    status, filepath = parts
                    changed_files.append((status, filepath))

            click.echo(f"  Found {len(changed_files)} changed file(s)")

            # Extract initial and final versions of changed files if code folder doesn't exist
            if not code_existed:
                # Save the current branch/commit to restore later
                result = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                original_branch = result.stdout.strip()

                try:
                    # Extract initial versions (skip new files, include deleted files)
                    extract_files_from_commit(
                        repo_path=repo_path,
                        commit_hash=commit_info.parent_commit,
                        changed_files=changed_files,
                        dest_dir=pr_structure.code_initial_dir,
                        skip_status="A",
                        log_message=lambda msg: click.echo(msg, err=True),
                    )

                    # Extract final versions (skip deleted files, include new files)
                    extract_files_from_commit(
                        repo_path=repo_path,
                        commit_hash=commit_info.pr_commit,
                        changed_files=changed_files,
                        dest_dir=pr_structure.code_final_dir,
                        skip_status="D",
                        log_message=lambda msg: click.echo(msg, err=True),
                    )

                finally:
                    # Always restore the original branch
                    subprocess.run(
                        ["git", "checkout", original_branch],
                        cwd=repo_path,
                        capture_output=True,
                        check=True,
                    )
            else:
                click.echo("  Code folder already exists, skipping file extraction")

            # Generate and save diff if it doesn't exist
            if not diff_existed:
                result = subprocess.run(
                    [
                        "git",
                        "diff",
                        f"{commit_info.parent_commit}...{commit_info.pr_commit}",
                    ],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                pr_structure.diff_file.write_text(result.stdout)
            else:
                click.echo("  diff.txt already exists, skipping diff generation")

            click.echo(f"  Extracted PR #{pr_number} successfully")

        except subprocess.CalledProcessError as e:
            click.echo(f"Failed to extract PR #{pr_number}: {e}", err=True)
        except Exception as e:
            click.echo(f"Error extracting PR #{pr_number}: {e}", err=True)
