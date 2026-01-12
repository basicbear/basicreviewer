"""Extract command for crev CLI - extracts PR files and diffs."""

import json
import shutil
import subprocess
from pathlib import Path

import click


def extract_pr_files(repo: dict, repos_dir: Path, output_dir: Path) -> None:
    """Extract files and diffs for PRs in a single repo.

    Args:
        repo: Single repo object from repos.json
        repos_dir: Directory containing cloned repos
        output_dir: Root pullrequests directory
    """
    name = repo.get("name")
    pull_requests = repo.get("pull_requests", [])

    if not name:
        return

    repo_path = repos_dir / name

    if not repo_path.exists():
        click.echo(f"Skipping PRs for {name} (repo not found)", err=True)
        return

    # Create repo subfolder in pullrequests
    repo_output_dir = output_dir / name
    repo_output_dir.mkdir(parents=True, exist_ok=True)

    for pr_number in pull_requests:
        if not isinstance(pr_number, int):
            click.echo(f"Skipping invalid PR number in {name}: {pr_number}", err=True)
            continue

        # Create PR folder structure
        pr_dir = repo_output_dir / str(pr_number)
        code_dir = pr_dir / "code"
        code_initial_dir = code_dir / "initial"
        code_final_dir = code_dir / "final"
        sum_dir = pr_dir / "sum"
        diff_file = sum_dir / "diff.txt"

        # Check if code folder exists
        code_exists = code_dir.exists()
        # Check if diff.txt exists
        diff_exists = diff_file.exists()

        if code_exists and diff_exists:
            click.echo(f"PR #{pr_number} for {name} already extracted, skipping...")
            continue

        click.echo(f"Extracting PR #{pr_number} for {name}...")

        code_initial_dir.mkdir(parents=True, exist_ok=True)
        code_final_dir.mkdir(parents=True, exist_ok=True)
        sum_dir.mkdir(parents=True, exist_ok=True)

        # Get the branch name for this PR
        local_branch = f"crev-pr-{pr_number}"

        try:
            # Get the merged hash, parent commit, and PR commit using git log
            # Format: <merged_hash> <parent_commit> <pr_commit>
            result = subprocess.run(
                ["git", "log", "main..." + local_branch, "--parents"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            log_output = result.stdout.strip()

            # Parse the output: first hash is merged, second is parent, third is PR
            parts = log_output.split()
            if len(parts) < 3:
                raise ValueError(f"Expected 3 commit hashes, got {len(parts)}")

            merged_commit = parts[1]
            parent_commit = parts[2]
            pr_commit = parts[3]

            click.echo(f"  Merged commit: {merged_commit[:8]}")
            click.echo(f"  Base commit: {parent_commit[:8]}")
            click.echo(f"  PR commit: {pr_commit[:8]}")

            # Get list of changed files
            result = subprocess.run(
                ["git", "diff", f"{parent_commit}...{pr_commit}", "--name-status"],
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
            if not code_exists:
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
                    # Extract initial versions (from parent commit)
                    subprocess.run(
                        ["git", "checkout", parent_commit],
                        cwd=repo_path,
                        capture_output=True,
                        check=True,
                    )

                    for status, filepath in changed_files:
                        # Extract initial version (skip new files, include deleted files)
                        if status != "A":
                            source_file = repo_path / filepath
                            if source_file.exists():
                                dest_file = code_initial_dir / filepath
                                dest_file.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(source_file, dest_file)
                            else:
                                click.echo(
                                    f"    Skipping initial version of {filepath} (file not found)",
                                    err=True,
                                )

                    # Extract final versions (from PR commit)
                    subprocess.run(
                        ["git", "checkout", pr_commit],
                        cwd=repo_path,
                        capture_output=True,
                        check=True,
                    )

                    for status, filepath in changed_files:
                        # Extract final version (skip deleted files, include new files)
                        if status != "D":
                            source_file = repo_path / filepath
                            if source_file.exists():
                                dest_file = code_final_dir / filepath
                                dest_file.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(source_file, dest_file)
                            else:
                                click.echo(
                                    f"    Skipping final version of {filepath} (file not found)",
                                    err=True,
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
            if not diff_exists:
                result = subprocess.run(
                    ["git", "diff", f"{parent_commit}...{pr_commit}"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                diff_file.write_text(result.stdout)
            else:
                click.echo("  diff.txt already exists, skipping diff generation")

            click.echo(f"  Extracted PR #{pr_number} successfully")

        except subprocess.CalledProcessError as e:
            click.echo(f"Failed to extract PR #{pr_number}: {e}", err=True)
        except Exception as e:
            click.echo(f"Error extracting PR #{pr_number}: {e}", err=True)


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
