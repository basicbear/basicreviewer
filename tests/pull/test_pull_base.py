"""Base tests for the pull command - core functionality."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

from click.testing import CliRunner

from crev import main


def test_pull_creates_repos_directory(tmp_path):
    """Test that pull creates the repos directory if it doesn't exist."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create minimal configs.json
        repos_data = {"repos": []}
        with open("configs.json", "w") as f:
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
        # Create configs.json with one repo
        repos_data = {
            "repos": [
                {
                    "org": "test-org",
                    "name": "test-repo",
                    "url": "https://github.com/user/test-repo.git",
                    "pull_requests": [],
                }
            ]
        }
        with open("configs.json", "w") as f:
            json.dump(repos_data, f)

        result = runner.invoke(main, ["pull"])

        assert result.exit_code == 0
        assert "Cloning test-repo..." in result.output
        assert "Done." in result.output

        # Verify git clone was called with correct path including org
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "git"
        assert call_args[1] == "clone"
        assert call_args[2] == "https://github.com/user/test-repo.git"
        assert str(call_args[3]).endswith("repos/test-org/test-repo")


@patch("subprocess.run")
def test_pull_updates_existing_repo(mock_run, tmp_path):
    """Test that pull updates an existing repository."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create configs.json
        repos_data = {
            "repos": [
                {
                    "org": "test-org",
                    "name": "test-repo",
                    "url": "https://github.com/user/test-repo.git",
                    "pull_requests": [],
                }
            ]
        }
        with open("configs.json", "w") as f:
            json.dump(repos_data, f)

        # Create existing repo directory with org level
        Path("repos/test-org/test-repo").mkdir(parents=True)

        result = runner.invoke(main, ["pull"])

        assert result.exit_code == 0
        assert "Pulling updates for test-repo..." in result.output
        assert "Done." in result.output

        # Verify git commands were called: 1 pull + 1 branch check
        assert mock_run.call_count == 2
        # First call should be git pull
        assert mock_run.call_args_list[0][0][0] == ["git", "pull"]
        assert mock_run.call_args_list[0][1]["cwd"] == Path("repos/test-org/test-repo")
        # Second call should be git branch --list
        assert mock_run.call_args_list[1][0][0] == ["git", "branch", "--list"]


@patch("subprocess.run")
def test_pull_fetches_pull_requests(mock_run, tmp_path):
    """Test that pull fetches pull requests for a repo."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create configs.json with PRs
        repos_data = {
            "repos": [
                {
                    "org": "test-org",
                    "name": "test-repo",
                    "url": "https://github.com/user/test-repo.git",
                    "pull_requests": [123, 456],
                }
            ]
        }
        with open("configs.json", "w") as f:
            json.dump(repos_data, f)

        # Create existing repo directory with org level
        Path("repos/test-org/test-repo").mkdir(parents=True)

        result = runner.invoke(main, ["pull"])

        assert result.exit_code == 0
        assert "Pulling updates for test-repo..." in result.output
        assert "Fetching PR #123 for test-repo into crev-pr-123..." in result.output
        assert "Fetching PR #456 for test-repo into crev-pr-456..." in result.output
        assert "Done." in result.output

        # Verify git commands were called: 1 pull + 1 branch check + 2 fetch PRs
        assert mock_run.call_count == 4

        # Check PR fetch calls
        pr_calls = [c for c in mock_run.call_args_list if "fetch" in c[0][0]]
        assert len(pr_calls) == 2
        assert pr_calls[0][0][0] == [
            "git",
            "fetch",
            "origin",
            "pull/123/head:crev-pr-123",
        ]
        assert pr_calls[1][0][0] == [
            "git",
            "fetch",
            "origin",
            "pull/456/head:crev-pr-456",
        ]


@patch("subprocess.run")
def test_pull_handles_multiple_repos(mock_run, tmp_path):
    """Test that pull handles multiple repositories."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create configs.json with multiple repos
        repos_data = {
            "repos": [
                {
                    "org": "org1",
                    "name": "repo1",
                    "url": "https://github.com/user/repo1.git",
                    "pull_requests": [],
                },
                {
                    "org": "org2",
                    "name": "repo2",
                    "url": "https://github.com/user/repo2.git",
                    "pull_requests": [789],
                },
            ]
        }
        with open("configs.json", "w") as f:
            json.dump(repos_data, f)

        # Create existing repo directory for repo2 with org level
        Path("repos/org2/repo2").mkdir(parents=True)

        result = runner.invoke(main, ["pull"])

        assert result.exit_code == 0
        assert "Cloning repo1..." in result.output
        assert "Pulling updates for repo2..." in result.output
        assert "Fetching PR #789 for repo2 into crev-pr-789..." in result.output

        # Verify git commands: 1 clone (repo1) + 1 pull (repo2) + 1 branch check + 1 fetch PR
        assert mock_run.call_count == 4


@patch("subprocess.run")
def test_pull_skips_existing_pr_branches(mock_run, tmp_path):
    """Test that pull skips fetching PRs when their branches already exist."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create configs.json with PRs
        repos_data = {
            "repos": [
                {
                    "org": "test-org",
                    "name": "test-repo",
                    "url": "https://github.com/user/test-repo.git",
                    "pull_requests": [123, 456],
                }
            ]
        }
        with open("configs.json", "w") as f:
            json.dump(repos_data, f)

        # Create existing repo directory with org level
        Path("repos/test-org/test-repo").mkdir(parents=True)

        # Mock subprocess.run to simulate branch check and git pull
        def mock_subprocess_run(cmd, **kwargs):
            result = Mock()
            # Mock git branch --list to return existing branch crev-pr-123
            if cmd == ["git", "branch", "--list"]:
                result.stdout = "  crev-pr-123\n  main\n* master\n"
                return result
            # Mock git pull
            if cmd == ["git", "pull"]:
                return result
            # Mock git fetch (should only be called for PR #456, not #123)
            if "fetch" in cmd:
                return result
            return result

        mock_run.side_effect = mock_subprocess_run

        result = runner.invoke(main, ["pull"])

        assert result.exit_code == 0
        assert "Pulling updates for test-repo..." in result.output
        assert (
            "Branch crev-pr-123 already exists for test-repo, skipping..."
            in result.output
        )
        assert "Fetching PR #456 for test-repo into crev-pr-456..." in result.output
        assert "Done." in result.output

        # Verify git commands: 1 pull + 1 branch check + 1 fetch (only for PR #456)
        assert mock_run.call_count == 3

        # Verify that fetch was only called for PR #456, not #123
        fetch_calls = [
            c for c in mock_run.call_args_list if len(c[0]) > 0 and "fetch" in c[0][0]
        ]
        assert len(fetch_calls) == 1
        assert fetch_calls[0][0][0] == [
            "git",
            "fetch",
            "origin",
            "pull/456/head:crev-pr-456",
        ]
