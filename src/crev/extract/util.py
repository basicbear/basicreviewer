"""Utility functions for the extract command."""

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass
class PRCommitInfo:
    """Information about commits involved in a PR.

    Attributes:
        merged_commit: The merge commit hash
        parent_commit: The parent/base commit hash
        pr_commit: The PR tip commit hash
    """

    merged_commit: str
    parent_commit: str
    pr_commit: str


def get_pr_commit_info(repo_path: Path, pr_branch: str) -> PRCommitInfo:
    """Get commit information for a PR branch.

    Uses git log to find the merge commit, parent commit, and PR commit.

    Args:
        repo_path: Path to the git repository
        pr_branch: Name of the PR branch (e.g., "crev-pr-123")

    Returns:
        PRCommitInfo with the three commit hashes

    Raises:
        subprocess.CalledProcessError: If git command fails
        ValueError: If unable to parse expected commit hashes
    """
    # Get the merged hash, parent commit, and PR commit using git log
    # Format: <merged_hash> <parent_commit> <pr_commit>
    result = subprocess.run(
        ["git", "log", f"main...{pr_branch}", "--parents"],
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

    return PRCommitInfo(
        merged_commit=merged_commit,
        parent_commit=parent_commit,
        pr_commit=pr_commit,
    )


def extract_files_from_commit(
    repo_path: Path,
    commit_hash: str,
    changed_files: list[tuple[str, str]],
    dest_dir: Path,
    skip_status: str,
    log_message: Callable[[str], None],
) -> None:
    """Extract files from a specific commit.

    Args:
        repo_path: Path to the git repository
        commit_hash: The commit hash to checkout
        changed_files: List of (status, filepath) tuples from git diff --name-status
        dest_dir: Destination directory to copy files to
        skip_status: Git status to skip (e.g., "A" for added files, "D" for deleted files)
        log_message: Function to call for logging messages (e.g., click.echo)
    """
    # Checkout the specific commit
    subprocess.run(
        ["git", "checkout", commit_hash],
        cwd=repo_path,
        capture_output=True,
        check=True,
    )

    # Extract files
    for status, filepath in changed_files:
        # Skip files with the specified status
        if status == skip_status:
            continue

        source_file = repo_path / filepath
        if source_file.exists():
            dest_file = dest_dir / filepath
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_file, dest_file)
        else:
            log_message(f"    Skipping {filepath} (file not found)")


class PRFolderStructure:
    """Represents the folder structure for a PR extraction.

    Attributes:
        pr_dir: Root directory for the PR
        code_dir: Directory containing initial and final code versions
        code_initial_dir: Directory for initial code version
        code_final_dir: Directory for final code version
        sum_dir: Directory for summary files
        diff_file: Path to the diff.txt file
    """

    def __init__(self, repo_output_dir: Path, pr_number: int):
        """Initialize PR folder structure paths.

        Args:
            repo_output_dir: Root output directory for the repository
            pr_number: Pull request number
        """
        self.pr_dir = repo_output_dir / str(pr_number)
        self.code_dir = self.pr_dir / "code"
        self.code_initial_dir = self.code_dir / "initial"
        self.code_final_dir = self.code_dir / "final"
        self.sum_dir = self.pr_dir / "sum"
        self.diff_file = self.sum_dir / "diff.txt"

    def code_exists(self) -> bool:
        """Check if the code directory exists."""
        return self.code_dir.exists()

    def diff_exists(self) -> bool:
        """Check if the diff.txt file exists."""
        return self.diff_file.exists()

    def is_fully_extracted(self) -> bool:
        """Check if PR is fully extracted (both code and diff exist)."""
        return self.code_exists() and self.diff_exists()

    def create_directories(self) -> None:
        """Create all necessary directories for the PR extraction."""
        self.code_initial_dir.mkdir(parents=True, exist_ok=True)
        self.code_final_dir.mkdir(parents=True, exist_ok=True)
        self.sum_dir.mkdir(parents=True, exist_ok=True)
