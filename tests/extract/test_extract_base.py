"""Base tests for the extract command - core functionality."""

import json
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

from click.testing import CliRunner

from crev import main


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


@patch("subprocess.run")
def test_extract_processes_pr(mock_run, tmp_path):
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

        # Create repo directory and files with org level
        repo_path = Path("repos/test-org/test-repo")
        repo_path.mkdir(parents=True)
        (repo_path / "src").mkdir(parents=True)
        (repo_path / "src" / "file1.py").write_text("content")
        (repo_path / "src" / "file2.py").write_text("content")
        (repo_path / "src" / "old_file.py").write_text("content")

        # Mock git commands
        def mock_subprocess_run(cmd, **kwargs):
            result = Mock()

            # Mock git log --parents to get commit hashes
            if cmd[0] == "git" and cmd[1] == "log" and "--parents" in cmd:
                # Format: commit merged_hash parent_hash pr_hash
                result.stdout = "commit abc123merged parent123456 pr789abc\n"
                result.returncode = 0
                return result

            # Mock git rev-parse for getting current branch
            if cmd[0] == "git" and cmd[1] == "rev-parse":
                if cmd[2] == "--abbrev-ref" and cmd[3] == "HEAD":
                    result.stdout = "main\n"
                result.returncode = 0
                return result

            # Mock git diff --name-status
            if "diff" in cmd and "--name-status" in cmd:
                result.stdout = "M\tsrc/file1.py\nA\tsrc/file2.py\nD\tsrc/old_file.py\n"
                result.returncode = 0
                return result

            # Mock git checkout
            if cmd[0] == "git" and cmd[1] == "checkout":
                result.returncode = 0
                return result

            # Mock git diff for full diff
            if "diff" in cmd and "--name-status" not in cmd:
                result.stdout = "diff --git a/src/file1.py b/src/file1.py\n--- a/src/file1.py\n+++ b/src/file1.py\n"
                result.returncode = 0
                return result

            result.returncode = 0
            return result

        mock_run.side_effect = mock_subprocess_run

        result = runner.invoke(main, ["extract"])

        assert result.exit_code == 0
        assert "Extracting PR #123 for test-repo..." in result.output
        assert "Done." in result.output

        # Verify directory structure was created with org level
        pr_dir = Path("pullrequests/test-org/test-repo/123")
        assert pr_dir.exists()
        assert (pr_dir / "code" / "initial").exists()
        assert (pr_dir / "code" / "final").exists()
        assert (pr_dir / "sum").exists()
        assert (pr_dir / "sum" / "diff.txt").exists()


@patch("subprocess.run")
def test_extract_handles_multiple_repos_and_prs(mock_run, tmp_path):
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

        # Create repo directories and files with org level
        repo1_path = Path("repos/org1/repo1")
        repo1_path.mkdir(parents=True)
        (repo1_path / "file.py").write_text("content")

        repo2_path = Path("repos/org2/repo2")
        repo2_path.mkdir(parents=True)
        (repo2_path / "file.py").write_text("content")

        # Mock git commands
        def mock_subprocess_run(cmd, **kwargs):
            result = Mock()
            result.returncode = 0
            result.stdout = "abc123\n"

            if cmd[0] == "git" and cmd[1] == "log" and "--parents" in cmd:
                # Format: commit merged_hash parent_hash pr_hash
                result.stdout = "commit abc123merged parent123456 pr789abc\n"
            elif cmd[1] == "rev-parse" and cmd[2] == "--abbrev-ref":
                result.stdout = "main\n"
            elif "diff" in cmd and "--name-status" in cmd:
                result.stdout = "M\tfile.py\n"
            elif "diff" in cmd:
                result.stdout = "diff content"

            return result

        mock_run.side_effect = mock_subprocess_run

        result = runner.invoke(main, ["extract"])

        assert result.exit_code == 0
        assert "Extracting PR #100 for repo1..." in result.output
        assert "Extracting PR #101 for repo1..." in result.output
        assert "Extracting PR #200 for repo2..." in result.output

        # Verify directory structures were created with org level
        assert Path("pullrequests/org1/repo1/100").exists()
        assert Path("pullrequests/org1/repo1/101").exists()
        assert Path("pullrequests/org2/repo2/200").exists()


@patch("subprocess.run")
def test_extract_skips_missing_pr_branch(mock_run, tmp_path):
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

        # Mock git log to fail (branch doesn't exist)
        def mock_subprocess_run(cmd, **kwargs):
            if cmd[0] == "git" and cmd[1] == "log":
                raise subprocess.CalledProcessError(1, cmd, stderr="fatal: bad revision")
            result = Mock()
            result.returncode = 0
            return result

        mock_run.side_effect = mock_subprocess_run

        result = runner.invoke(main, ["extract"])

        assert result.exit_code == 0
        assert "Failed to extract PR #999" in result.output


@patch("subprocess.run")
def test_extract_skips_already_extracted_pr(mock_run, tmp_path):
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

        # Verify no git commands were called (since we skipped extraction)
        mock_run.assert_not_called()


@patch("subprocess.run")
def test_extract_partial_extraction_code_exists(mock_run, tmp_path):
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

        # Mock git commands
        def mock_subprocess_run(cmd, **kwargs):
            result = Mock()

            # Mock git log --parents to get commit hashes
            if cmd[0] == "git" and cmd[1] == "log" and "--parents" in cmd:
                # Format: commit merged_hash parent_hash pr_hash
                result.stdout = "commit abc123merged parent123456 pr789abc\n"
                result.returncode = 0
                return result

            # Mock git diff --name-status
            if "diff" in cmd and "--name-status" in cmd:
                result.stdout = "M\tsrc/file1.py\n"
                result.returncode = 0
                return result

            # Mock git diff for full diff
            if "diff" in cmd and "--name-status" not in cmd:
                result.stdout = "diff content"
                result.returncode = 0
                return result

            result.returncode = 0
            return result

        mock_run.side_effect = mock_subprocess_run

        result = runner.invoke(main, ["extract"])

        assert result.exit_code == 0
        assert "Extracting PR #123 for test-repo..." in result.output
        assert "Code folder already exists, skipping file extraction" in result.output
        assert "Done." in result.output

        # Verify diff.txt was created
        assert (pr_dir / "sum" / "diff.txt").exists()
        assert (pr_dir / "sum" / "diff.txt").read_text() == "diff content"

        # Verify git checkout was NOT called (no file extraction)
        checkout_calls = [
            c for c in mock_run.call_args_list if len(c[0]) > 0 and c[0][0][1] == "checkout"
        ]
        assert len(checkout_calls) == 0


@patch("subprocess.run")
def test_extract_partial_extraction_diff_exists(mock_run, tmp_path):
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

        # Create repo directory and files with org level
        repo_path = Path("repos/test-org/test-repo")
        repo_path.mkdir(parents=True)
        (repo_path / "src").mkdir(parents=True)
        (repo_path / "src" / "file1.py").write_text("file content")

        # Create existing diff.txt but no code folder with org level
        pr_dir = Path("pullrequests/test-org/test-repo/123")
        sum_dir = pr_dir / "sum"
        sum_dir.mkdir(parents=True)
        (sum_dir / "diff.txt").write_text("existing diff")

        # Mock git commands
        def mock_subprocess_run(cmd, **kwargs):
            result = Mock()

            # Mock git log --parents to get commit hashes
            if cmd[0] == "git" and cmd[1] == "log" and "--parents" in cmd:
                # Format: commit merged_hash parent_hash pr_hash
                result.stdout = "commit abc123merged parent123456 pr789abc\n"
                result.returncode = 0
                return result

            # Mock git rev-parse for getting current branch
            if cmd[0] == "git" and cmd[1] == "rev-parse":
                if cmd[2] == "--abbrev-ref" and cmd[3] == "HEAD":
                    result.stdout = "main\n"
                result.returncode = 0
                return result

            # Mock git diff --name-status
            if "diff" in cmd and "--name-status" in cmd:
                result.stdout = "M\tsrc/file1.py\n"
                result.returncode = 0
                return result

            # Mock git checkout
            if cmd[0] == "git" and cmd[1] == "checkout":
                result.returncode = 0
                return result

            result.returncode = 0
            return result

        mock_run.side_effect = mock_subprocess_run

        result = runner.invoke(main, ["extract"])

        assert result.exit_code == 0
        assert "Extracting PR #123 for test-repo..." in result.output
        assert "diff.txt already exists, skipping diff generation" in result.output
        assert "Done." in result.output

        # Verify files were extracted
        assert (pr_dir / "code" / "initial" / "src" / "file1.py").exists()
        assert (pr_dir / "code" / "final" / "src" / "file1.py").exists()

        # Verify diff was NOT generated (should still have original content)
        assert (sum_dir / "diff.txt").read_text() == "existing diff"
