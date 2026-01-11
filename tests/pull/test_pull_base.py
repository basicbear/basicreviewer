"""Base tests for the pull command - core functionality."""

import json
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from crev import main


def test_pull_creates_repos_directory(tmp_path):
    """Test that pull creates the repos directory if it doesn't exist."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create minimal repos.json
        repos_data = {"repos": []}
        with open("repos.json", "w") as f:
            json.dump(repos_data, f)

        with patch("subprocess.run"):
            result = runner.invoke(main, ["pull"])

        assert result.exit_code == 0
        assert Path("repos").exists()
        assert Path("repos").is_dir()


@patch("subprocess.run")
def test_pull_clones_new_repo(mock_run, tmp_path):
    """Test that pull clones a new repository."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create repos.json with one repo
        repos_data = {
            "repos": [
                {
                    "name": "test-repo",
                    "url": "https://github.com/user/test-repo.git",
                    "pull_requests": []
                }
            ]
        }
        with open("repos.json", "w") as f:
            json.dump(repos_data, f)

        result = runner.invoke(main, ["pull"])

        assert result.exit_code == 0
        assert "Cloning test-repo..." in result.output
        assert "Done." in result.output

        # Verify git clone was called
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "git"
        assert call_args[1] == "clone"
        assert call_args[2] == "https://github.com/user/test-repo.git"


@patch("subprocess.run")
def test_pull_updates_existing_repo(mock_run, tmp_path):
    """Test that pull updates an existing repository."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create repos.json
        repos_data = {
            "repos": [
                {
                    "name": "test-repo",
                    "url": "https://github.com/user/test-repo.git",
                    "pull_requests": []
                }
            ]
        }
        with open("repos.json", "w") as f:
            json.dump(repos_data, f)

        # Create existing repo directory
        Path("repos/test-repo").mkdir(parents=True)

        result = runner.invoke(main, ["pull"])

        assert result.exit_code == 0
        assert "Pulling updates for test-repo..." in result.output
        assert "Done." in result.output

        # Verify git pull was called
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args == ["git", "pull"]
        assert mock_run.call_args[1]["cwd"] == Path("repos/test-repo")


@patch("subprocess.run")
def test_pull_fetches_pull_requests(mock_run, tmp_path):
    """Test that pull fetches pull requests for a repo."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create repos.json with PRs
        repos_data = {
            "repos": [
                {
                    "name": "test-repo",
                    "url": "https://github.com/user/test-repo.git",
                    "pull_requests": [123, 456]
                }
            ]
        }
        with open("repos.json", "w") as f:
            json.dump(repos_data, f)

        # Create existing repo directory
        Path("repos/test-repo").mkdir(parents=True)

        result = runner.invoke(main, ["pull"])

        assert result.exit_code == 0
        assert "Pulling updates for test-repo..." in result.output
        assert "Fetching PR #123 for test-repo into crev-pr-123..." in result.output
        assert "Fetching PR #456 for test-repo into crev-pr-456..." in result.output
        assert "Done." in result.output

        # Verify git commands were called
        assert mock_run.call_count == 3  # 1 pull + 2 fetch PRs

        # Check PR fetch calls
        pr_calls = [c for c in mock_run.call_args_list if "fetch" in c[0][0]]
        assert len(pr_calls) == 2
        assert pr_calls[0][0][0] == ["git", "fetch", "origin", "pull/123/head:crev-pr-123"]
        assert pr_calls[1][0][0] == ["git", "fetch", "origin", "pull/456/head:crev-pr-456"]


@patch("subprocess.run")
def test_pull_handles_multiple_repos(mock_run, tmp_path):
    """Test that pull handles multiple repositories."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create repos.json with multiple repos
        repos_data = {
            "repos": [
                {
                    "name": "repo1",
                    "url": "https://github.com/user/repo1.git",
                    "pull_requests": []
                },
                {
                    "name": "repo2",
                    "url": "https://github.com/user/repo2.git",
                    "pull_requests": [789]
                }
            ]
        }
        with open("repos.json", "w") as f:
            json.dump(repos_data, f)

        # Create existing repo directory for repo2
        Path("repos/repo2").mkdir(parents=True)

        result = runner.invoke(main, ["pull"])

        assert result.exit_code == 0
        assert "Cloning repo1..." in result.output
        assert "Pulling updates for repo2..." in result.output
        assert "Fetching PR #789 for repo2 into crev-pr-789..." in result.output

        # Verify git commands: 1 clone (repo1) + 1 pull (repo2) + 1 fetch PR
        assert mock_run.call_count == 3
