"""Utility functions for the extract command."""

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pygit2


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

    Uses pygit2 to find the merge commit, parent commit, and PR commit.

    Args:
        repo_path: Path to the git repository
        pr_branch: Name of the PR branch (e.g., "crev-pr-123")

    Returns:
        PRCommitInfo with the three commit hashes

    Raises:
        pygit2.GitError: If git operations fail
        ValueError: If unable to find expected commits
    """
    repository = pygit2.Repository(str(repo_path))

    main_ref = repository.references.get("refs/heads/main")
    pr_ref = repository.references.get(f"refs/heads/{pr_branch}")

    if main_ref is None:
        raise ValueError("Could not find main branch")
    if pr_ref is None:
        raise ValueError(f"Could not find branch {pr_branch}")

    main_oid = main_ref.peel(pygit2.Commit).id
    pr_oid = pr_ref.peel(pygit2.Commit).id

    # Find the merge commit on main that merged this PR branch
    # Walk main branch looking for a merge commit whose second parent is the PR tip
    merged_commit = None
    for commit in repository.walk(main_oid, pygit2.GIT_SORT_TOPOLOGICAL):
        if len(commit.parents) == 2 and commit.parents[1].id == pr_oid:
            merged_commit = commit
            break

    if merged_commit is None:
        raise ValueError(f"Could not find merge commit for branch {pr_branch} on main")

    parent_commit = merged_commit.parents[0]
    pr_commit = merged_commit.parents[1]

    return PRCommitInfo(
        merged_commit=str(merged_commit.id),
        parent_commit=str(parent_commit.id),
        pr_commit=str(pr_commit.id),
    )


def get_changed_files(
    repo_path: Path, parent_commit: str, pr_commit: str
) -> list[tuple[str, str]]:
    """Get the list of changed files between two commits.

    Args:
        repo_path: Path to the git repository
        parent_commit: The base commit hash
        pr_commit: The PR tip commit hash

    Returns:
        List of (status, filepath) tuples where status is one of "A", "D", "M", etc.
    """
    repository = pygit2.Repository(str(repo_path))

    parent = repository.get(parent_commit)
    pr = repository.get(pr_commit)

    diff = repository.diff(parent, pr)

    changed_files = []
    for delta in diff.deltas:
        if delta.status == pygit2.GIT_DELTA_ADDED:
            status = "A"
        elif delta.status == pygit2.GIT_DELTA_DELETED:
            status = "D"
        elif delta.status == pygit2.GIT_DELTA_MODIFIED:
            status = "M"
        elif delta.status == pygit2.GIT_DELTA_RENAMED:
            status = "R"
        else:
            status = "M"

        filepath = delta.new_file.path if status != "D" else delta.old_file.path
        changed_files.append((status, filepath))

    return changed_files


def get_diff_text(repo_path: Path, parent_commit: str, pr_commit: str) -> str:
    """Get the full diff text between two commits.

    Args:
        repo_path: Path to the git repository
        parent_commit: The base commit hash
        pr_commit: The PR tip commit hash

    Returns:
        The diff as a string
    """
    repository = pygit2.Repository(str(repo_path))

    parent = repository.get(parent_commit)
    pr = repository.get(pr_commit)

    diff = repository.diff(parent, pr)
    return diff.patch or ""


def extract_files_from_commit(
    repo_path: Path,
    commit_hash: str,
    changed_files: list[tuple[str, str]],
    dest_dir: Path,
    skip_status: str,
    log_message: Callable[[str], None],
) -> None:
    """Extract files from a specific commit using pygit2.

    Args:
        repo_path: Path to the git repository
        commit_hash: The commit hash to read files from
        changed_files: List of (status, filepath) tuples from diff
        dest_dir: Destination directory to copy files to
        skip_status: Git status to skip (e.g., "A" for added files, "D" for deleted files)
        log_message: Function to call for logging messages
    """
    repository = pygit2.Repository(str(repo_path))
    commit = repository.get(commit_hash)
    tree = commit.peel(pygit2.Tree)

    for status, filepath in changed_files:
        if status == skip_status:
            continue

        try:
            entry = tree[filepath]
            blob = repository.get(entry.id)
            if blob is None or blob.type != pygit2.enums.ObjectType.BLOB:
                log_message(f"    Skipping {filepath} (not a blob)")
                continue

            dest_file = dest_dir / filepath
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            dest_file.write_bytes(blob.data)
        except KeyError:
            log_message(f"    Skipping {filepath} (file not found in commit)")


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
