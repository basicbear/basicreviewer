"""Base tests for the pull command - core functionality."""

import json
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock, patch, PropertyMock

from click.testing import CliRunner

from crev import main

# Load base configs data from JSON file
_TEST_CONFIGS_PATH = Path(__file__).parent / "test.configs.json"
with _TEST_CONFIGS_PATH.open() as _f:
    BASE_configs = json.load(_f)


def _make_mock_repository(local_branches=None):
    """Create a mock pygit2.Repository with standard structure.

    Args:
        local_branches: Set of local branch names to report as existing.
    """
    if local_branches is None:
        local_branches = set()

    mock_repo = Mock()
    mock_repo.branches.local = local_branches

    mock_remote = Mock()
    mock_repo.remotes.__getitem__ = Mock(return_value=mock_remote)

    mock_head = Mock()
    mock_head.shorthand = "main"
    mock_repo.head = mock_head

    mock_remote_ref = Mock()
    mock_remote_ref.target = "abc123"
    mock_repo.references.get = Mock(return_value=mock_remote_ref)
    mock_repo.get = Mock(return_value=Mock())

    return mock_repo, mock_remote


def test_pull_creates_repos_directory(tmp_path):
    """Test that pull creates the repos directory if it doesn't exist."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create minimal configs.json
        configs = deepcopy(BASE_configs)
        configs["repos"] = []
        with open("configs.json", "w") as f:
            json.dump(configs, f)

        result = runner.invoke(main, ["pull"])

        assert result.exit_code == 0
        assert Path("repos").exists()
        assert Path("repos").is_dir()


@patch("crev.pull.pygit2.clone_repository")
def test_pull_clones_new_repo(mock_clone, tmp_path):
    """Test that pull clones a new repository."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create configs.json with one repo
        configs = deepcopy(BASE_configs)
        configs["repos"][0]["pull_requests"] = []
        with open("configs.json", "w") as f:
            json.dump(configs, f)

        result = runner.invoke(main, ["pull"])

        assert result.exit_code == 0
        assert "Cloning test-repo..." in result.output
        assert "Done." in result.output

        # Verify clone was called with correct url and path
        mock_clone.assert_called_once()
        call_args = mock_clone.call_args[0]
        assert call_args[0] == "https://github.com/user/test-repo.git"
        assert call_args[1].endswith("repos/test-org/test-repo")


@patch("crev.pull.pygit2.Repository")
def test_pull_updates_existing_repo(mock_repo_cls, tmp_path):
    """Test that pull updates an existing repository."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create configs.json
        configs = deepcopy(BASE_configs)
        configs["repos"][0]["pull_requests"] = []
        with open("configs.json", "w") as f:
            json.dump(configs, f)

        # Create existing repo directory with org level
        Path("repos/test-org/test-repo").mkdir(parents=True)

        mock_repo, mock_remote = _make_mock_repository()
        mock_repo_cls.return_value = mock_repo

        result = runner.invoke(main, ["pull"])

        assert result.exit_code == 0
        assert "Pulling updates for test-repo..." in result.output
        assert "Done." in result.output

        # Verify repository was opened (once for pull, once for PR check)
        assert mock_repo_cls.call_count == 2
        mock_remote.fetch.assert_called_once_with()


@patch("crev.pull.pygit2.Repository")
def test_pull_fetches_pull_requests(mock_repo_cls, tmp_path):
    """Test that pull fetches pull requests for a repo."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create configs.json with PRs (uses base which has [123, 456])
        configs = deepcopy(BASE_configs)
        with open("configs.json", "w") as f:
            json.dump(configs, f)

        # Create existing repo directory with org level
        Path("repos/test-org/test-repo").mkdir(parents=True)

        mock_repo, mock_remote = _make_mock_repository()
        mock_repo_cls.return_value = mock_repo

        result = runner.invoke(main, ["pull"])

        assert result.exit_code == 0
        assert "Pulling updates for test-repo..." in result.output
        assert "Fetching PR #123 for test-repo into crev-pr-123..." in result.output
        assert "Fetching PR #456 for test-repo into crev-pr-456..." in result.output
        assert "Done." in result.output

        # Verify fetch was called for each PR
        # 1 fetch() for pull + 2 fetch() for PRs
        assert mock_remote.fetch.call_count == 3
        pr_fetch_calls = mock_remote.fetch.call_args_list[1:]
        assert pr_fetch_calls[0][0][0] == ["+refs/pull/123/head:refs/heads/crev-pr-123"]
        assert pr_fetch_calls[1][0][0] == ["+refs/pull/456/head:refs/heads/crev-pr-456"]


@patch("crev.pull.pygit2.clone_repository")
@patch("crev.pull.pygit2.Repository")
def test_pull_handles_multiple_repos(mock_repo_cls, mock_clone, tmp_path):
    """Test that pull handles multiple repositories."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create configs.json with multiple repos
        configs = deepcopy(BASE_configs)
        configs["repos"] = [
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
        with open("configs.json", "w") as f:
            json.dump(configs, f)

        # Create existing repo directory for repo2 with org level
        Path("repos/org2/repo2").mkdir(parents=True)

        mock_repo, mock_remote = _make_mock_repository()
        mock_repo_cls.return_value = mock_repo

        result = runner.invoke(main, ["pull"])

        assert result.exit_code == 0
        assert "Cloning repo1..." in result.output
        assert "Pulling updates for repo2..." in result.output
        assert "Fetching PR #789 for repo2 into crev-pr-789..." in result.output

        # Verify clone was called for repo1
        mock_clone.assert_called_once()
        # Verify fetch was called: 1 pull fetch + 1 PR fetch
        assert mock_remote.fetch.call_count == 2


@patch("crev.pull.pygit2.Repository")
def test_pull_skips_existing_pr_branches(mock_repo_cls, tmp_path):
    """Test that pull skips fetching PRs when their branches already exist."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create configs.json with PRs (uses base which has [123, 456])
        configs = deepcopy(BASE_configs)
        with open("configs.json", "w") as f:
            json.dump(configs, f)

        # Create existing repo directory with org level
        Path("repos/test-org/test-repo").mkdir(parents=True)

        # Mock repository with crev-pr-123 already existing
        mock_repo, mock_remote = _make_mock_repository(
            local_branches={"main", "crev-pr-123"}
        )
        mock_repo_cls.return_value = mock_repo

        result = runner.invoke(main, ["pull"])

        assert result.exit_code == 0
        assert "Pulling updates for test-repo..." in result.output
        assert (
            "Branch crev-pr-123 already exists for test-repo, skipping..."
            in result.output
        )
        assert "Fetching PR #456 for test-repo into crev-pr-456..." in result.output
        assert "Done." in result.output

        # Verify fetch: 1 pull fetch + 1 PR fetch (only #456, not #123)
        assert mock_remote.fetch.call_count == 2
        pr_fetch_calls = [
            c for c in mock_remote.fetch.call_args_list
            if c[0]  # has positional args (PR fetches do, pull fetch doesn't)
        ]
        assert len(pr_fetch_calls) == 1
        assert pr_fetch_calls[0][0][0] == ["+refs/pull/456/head:refs/heads/crev-pr-456"]
