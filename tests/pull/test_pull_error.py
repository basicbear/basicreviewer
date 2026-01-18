"""Error handling tests for the pull command."""

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from crev import main


def test_pull_fails_without_repos_json(tmp_path):
    """Test that pull fails when configs.json is not found."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(main, ["pull"])

        assert result.exit_code == 1
        assert "configs.json not found" in result.output
        assert "Run 'crev init' first" in result.output


def test_pull_skips_invalid_repo_entry(tmp_path):
    """Test that pull skips repos with missing name or url."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create configs.json with invalid entries
        repos_data = {
            "repos": [
                {"name": "valid-repo", "url": "https://github.com/user/valid.git"},
                {"name": "no-url"},
                {"url": "https://github.com/user/no-name.git"},
                {}
            ]
        }
        with open("configs.json", "w") as f:
            json.dump(repos_data, f)

        with patch("subprocess.run"):
            result = runner.invoke(main, ["pull"])

        assert result.exit_code == 0
        assert "Skipping invalid repo entry" in result.output


@patch("subprocess.run")
def test_pull_skips_prs_when_repo_not_found(mock_run, tmp_path):
    """Test that pull skips PRs when the repo directory doesn't exist."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create configs.json
        repos_data = {
            "repos": [
                {
                    "name": "test-repo",
                    "url": "https://github.com/user/test-repo.git",
                    "pull_requests": [123]
                }
            ]
        }
        with open("configs.json", "w") as f:
            json.dump(repos_data, f)

        # Simulate clone failure by not creating the directory
        mock_run.side_effect = lambda *args, **kwargs: None

        result = runner.invoke(main, ["pull"])

        assert result.exit_code == 0
        assert "Skipping PRs for test-repo (repo not found)" in result.output


@patch("subprocess.run")
def test_pull_handles_pr_fetch_failure(mock_run, tmp_path):
    """Test that pull handles failures when fetching a PR."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create configs.json
        repos_data = {
            "repos": [
                {
                    "name": "test-repo",
                    "url": "https://github.com/user/test-repo.git",
                    "pull_requests": [999]
                }
            ]
        }
        with open("configs.json", "w") as f:
            json.dump(repos_data, f)

        # Create existing repo directory
        Path("repos/test-repo").mkdir(parents=True)

        # Simulate PR fetch failure
        def mock_subprocess_run(cmd, **kwargs):
            from unittest.mock import Mock
            result = Mock()
            # Mock git pull
            if cmd == ["git", "pull"]:
                return result
            # Mock git branch --list
            if cmd == ["git", "branch", "--list"]:
                result.stdout = ""
                return result
            # Mock git fetch to fail
            if "fetch" in cmd:
                raise subprocess.CalledProcessError(1, ["git", "fetch"])
            return result

        mock_run.side_effect = mock_subprocess_run

        result = runner.invoke(main, ["pull"])

        assert result.exit_code == 0
        assert "Failed to fetch PR #999" in result.output
        assert "Done." in result.output


@patch("subprocess.run")
def test_pull_skips_invalid_pr_numbers(mock_run, tmp_path):
    """Test that pull skips invalid PR numbers (non-integers)."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create configs.json with invalid PR numbers
        repos_data = {
            "repos": [
                {
                    "name": "test-repo",
                    "url": "https://github.com/user/test-repo.git",
                    "pull_requests": [123, "invalid", None, 456]
                }
            ]
        }
        with open("configs.json", "w") as f:
            json.dump(repos_data, f)

        # Create existing repo directory
        Path("repos/test-repo").mkdir(parents=True)

        result = runner.invoke(main, ["pull"])

        assert result.exit_code == 0
        assert "Fetching PR #123" in result.output
        assert "Fetching PR #456" in result.output
        assert "Skipping invalid PR number" in result.output

        # Verify only valid PRs were fetched: 1 pull + 1 branch check + 2 fetch (123, 456)
        assert mock_run.call_count == 4
