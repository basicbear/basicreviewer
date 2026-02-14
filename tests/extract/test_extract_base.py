"""Base tests for the extract command - core functionality."""

import json
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from crev import main
from crev.extract.util import PRCommitInfo

# Reusable commit info for mocking
MOCK_COMMIT_INFO = PRCommitInfo(
    merged_commit="abc123merged",
    parent_commit="parent123456",
    pr_commit="pr789abc",
)


def test_extract_requires_repos_json(tmp_path):
    """Test that extract fails when configs.json doesn't exist."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(main, ["extract"])

        assert result.exit_code == 1
        assert "configs.json not found" in result.output


def test_extract_requires_repos_directory(tmp_path):
    """Test that extract fails when repos directory doesn't exist."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create configs.json but not repos directory
        repos_data = {"repos": []}
        with open("configs.json", "w") as f:
            json.dump(repos_data, f)

        result = runner.invoke(main, ["extract"])

        assert result.exit_code == 1
        assert "repos directory not found" in result.output


def test_extract_creates_pullrequests_directory(tmp_path):
    """Test that extract creates the pullrequests directory."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create minimal configs.json
        repos_data = {"repos": []}
        with open("configs.json", "w") as f:
            json.dump(repos_data, f)

        # Create empty repos directory
        Path("repos").mkdir()

        result = runner.invoke(main, ["extract"])

        assert result.exit_code == 0
        assert Path("pullrequests").exists()
        assert Path("pullrequests").is_dir()


@patch("crev.extract.extract_pr.extract_files_from_commit")
@patch("crev.extract.extract_pr.get_diff_text")
@patch("crev.extract.extract_pr.get_changed_files")
@patch("crev.extract.extract_pr.get_pr_commit_info")
def test_extract_processes_pr(
    mock_commit_info, mock_changed_files, mock_diff_text, mock_extract_files, tmp_path
):
    """Test that extract processes a PR and creates expected structure."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create configs.json with a PR
        repos_data = {
            "repos": [
                {
                    "org": "test-org",
                    "name": "test-repo",
                    "url": "https://github.com/user/test-repo.git",
                    "pull_requests": [123],
                }
            ]
        }
        with open("configs.json", "w") as f:
            json.dump(repos_data, f)

        # Create repo directory with org level
        repo_path = Path("repos/test-org/test-repo")
        repo_path.mkdir(parents=True)

        # Mock pygit2-based util functions
        mock_commit_info.return_value = MOCK_COMMIT_INFO
        mock_changed_files.return_value = [
            ("M", "src/file1.py"),
            ("A", "src/file2.py"),
            ("D", "src/old_file.py"),
        ]
        mock_diff_text.return_value = (
            "diff --git a/src/file1.py b/src/file1.py\n"
            "--- a/src/file1.py\n+++ b/src/file1.py\n"
        )

        result = runner.invoke(main, ["extract"])

        assert result.exit_code == 0
        assert "Extracting PR #123 for test-repo..." in result.output
        assert "Found 3 changed file(s)" in result.output
        assert "Done." in result.output

        # Verify directory structure was created with org level
        pr_dir = Path("pullrequests/test-org/test-repo/123")
        assert pr_dir.exists()
        assert (pr_dir / "code" / "initial").exists()
        assert (pr_dir / "code" / "final").exists()
        assert (pr_dir / "sum").exists()
        assert (pr_dir / "sum" / "diff.txt").exists()

        # Verify extract_files_from_commit was called twice (initial + final)
        assert mock_extract_files.call_count == 2


@patch("crev.extract.extract_pr.extract_files_from_commit")
@patch("crev.extract.extract_pr.get_diff_text")
@patch("crev.extract.extract_pr.get_changed_files")
@patch("crev.extract.extract_pr.get_pr_commit_info")
def test_extract_handles_multiple_repos_and_prs(
    mock_commit_info, mock_changed_files, mock_diff_text, mock_extract_files, tmp_path
):
    """Test that extract handles multiple repos with multiple PRs."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create configs.json with multiple repos and PRs
        repos_data = {
            "repos": [
                {
                    "org": "org1",
                    "name": "repo1",
                    "url": "https://github.com/user/repo1.git",
                    "pull_requests": [100, 101],
                },
                {
                    "org": "org2",
                    "name": "repo2",
                    "url": "https://github.com/user/repo2.git",
                    "pull_requests": [200],
                },
            ]
        }
        with open("configs.json", "w") as f:
            json.dump(repos_data, f)

        # Create repo directories with org level
        Path("repos/org1/repo1").mkdir(parents=True)
        Path("repos/org2/repo2").mkdir(parents=True)

        # Mock pygit2-based util functions
        mock_commit_info.return_value = MOCK_COMMIT_INFO
        mock_changed_files.return_value = [("M", "file.py")]
        mock_diff_text.return_value = "diff content"

        result = runner.invoke(main, ["extract"])

        assert result.exit_code == 0
        assert "Extracting PR #100 for repo1..." in result.output
        assert "Extracting PR #101 for repo1..." in result.output
        assert "Extracting PR #200 for repo2..." in result.output

        # Verify directory structures were created with org level
        assert Path("pullrequests/org1/repo1/100").exists()
        assert Path("pullrequests/org1/repo1/101").exists()
        assert Path("pullrequests/org2/repo2/200").exists()


@patch("crev.extract.extract_pr.get_pr_commit_info")
def test_extract_skips_missing_pr_branch(mock_commit_info, tmp_path):
    """Test that extract handles missing PR branches gracefully."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create configs.json with a PR
        repos_data = {
            "repos": [
                {
                    "org": "test-org",
                    "name": "test-repo",
                    "url": "https://github.com/user/test-repo.git",
                    "pull_requests": [999],
                }
            ]
        }
        with open("configs.json", "w") as f:
            json.dump(repos_data, f)

        # Create repo directory with org level
        Path("repos/test-org/test-repo").mkdir(parents=True)

        # Mock get_pr_commit_info to raise ValueError (branch not found)
        mock_commit_info.side_effect = ValueError("Could not find branch crev-pr-999")

        result = runner.invoke(main, ["extract"])

        assert result.exit_code == 0
        assert "Failed to extract PR #999" in result.output


def test_extract_skips_already_extracted_pr(tmp_path):
    """Test that extract skips PRs that are already extracted."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create configs.json with a PR
        repos_data = {
            "repos": [
                {
                    "org": "test-org",
                    "name": "test-repo",
                    "url": "https://github.com/user/test-repo.git",
                    "pull_requests": [123],
                }
            ]
        }
        with open("configs.json", "w") as f:
            json.dump(repos_data, f)

        # Create repo directory with org level
        Path("repos/test-org/test-repo").mkdir(parents=True)

        # Create existing PR extraction (both code and diff.txt exist) with org level
        pr_dir = Path("pullrequests/test-org/test-repo/123")
        code_dir = pr_dir / "code"
        code_dir.mkdir(parents=True)
        sum_dir = pr_dir / "sum"
        sum_dir.mkdir(parents=True)
        (sum_dir / "diff.txt").write_text("existing diff")

        result = runner.invoke(main, ["extract"])

        assert result.exit_code == 0
        assert "PR #123 for test-repo already extracted, skipping..." in result.output
        assert "Done." in result.output


@patch("crev.extract.extract_pr.extract_files_from_commit")
@patch("crev.extract.extract_pr.get_diff_text")
@patch("crev.extract.extract_pr.get_changed_files")
@patch("crev.extract.extract_pr.get_pr_commit_info")
def test_extract_partial_extraction_code_exists(
    mock_commit_info, mock_changed_files, mock_diff_text, mock_extract_files, tmp_path
):
    """Test that extract only generates diff.txt if code folder exists."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create configs.json with a PR
        repos_data = {
            "repos": [
                {
                    "org": "test-org",
                    "name": "test-repo",
                    "url": "https://github.com/user/test-repo.git",
                    "pull_requests": [123],
                }
            ]
        }
        with open("configs.json", "w") as f:
            json.dump(repos_data, f)

        # Create repo directory with org level
        Path("repos/test-org/test-repo").mkdir(parents=True)

        # Create existing code folder but no diff.txt with org level
        pr_dir = Path("pullrequests/test-org/test-repo/123")
        code_dir = pr_dir / "code"
        code_dir.mkdir(parents=True)

        # Mock pygit2-based util functions
        mock_commit_info.return_value = MOCK_COMMIT_INFO
        mock_changed_files.return_value = [("M", "src/file1.py")]
        mock_diff_text.return_value = "diff content"

        result = runner.invoke(main, ["extract"])

        assert result.exit_code == 0
        assert "Extracting PR #123 for test-repo..." in result.output
        assert "Code folder already exists, skipping file extraction" in result.output
        assert "Done." in result.output

        # Verify diff.txt was created
        assert (pr_dir / "sum" / "diff.txt").exists()
        assert (pr_dir / "sum" / "diff.txt").read_text() == "diff content"

        # Verify extract_files_from_commit was NOT called (code already exists)
        mock_extract_files.assert_not_called()


@patch("crev.extract.extract_pr.extract_files_from_commit")
@patch("crev.extract.extract_pr.get_diff_text")
@patch("crev.extract.extract_pr.get_changed_files")
@patch("crev.extract.extract_pr.get_pr_commit_info")
def test_extract_partial_extraction_diff_exists(
    mock_commit_info, mock_changed_files, mock_diff_text, mock_extract_files, tmp_path
):
    """Test that extract only extracts files if diff.txt exists."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create configs.json with a PR
        repos_data = {
            "repos": [
                {
                    "org": "test-org",
                    "name": "test-repo",
                    "url": "https://github.com/user/test-repo.git",
                    "pull_requests": [123],
                }
            ]
        }
        with open("configs.json", "w") as f:
            json.dump(repos_data, f)

        # Create repo directory with org level
        Path("repos/test-org/test-repo").mkdir(parents=True)

        # Create existing diff.txt but no code folder with org level
        pr_dir = Path("pullrequests/test-org/test-repo/123")
        sum_dir = pr_dir / "sum"
        sum_dir.mkdir(parents=True)
        (sum_dir / "diff.txt").write_text("existing diff")

        # Mock pygit2-based util functions
        mock_commit_info.return_value = MOCK_COMMIT_INFO
        mock_changed_files.return_value = [("M", "src/file1.py")]

        result = runner.invoke(main, ["extract"])

        assert result.exit_code == 0
        assert "Extracting PR #123 for test-repo..." in result.output
        assert "diff.txt already exists, skipping diff generation" in result.output
        assert "Done." in result.output

        # Verify files were extracted (extract_files_from_commit called twice)
        assert mock_extract_files.call_count == 2

        # Verify diff was NOT regenerated (should still have original content)
        assert (sum_dir / "diff.txt").read_text() == "existing diff"
        mock_diff_text.assert_not_called()
