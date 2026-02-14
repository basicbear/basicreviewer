"""Error handling tests for the pull command."""

import json
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock, patch

import pygit2
from click.testing import CliRunner

from crev import main

# Load base configs data from JSON file
_TEST_CONFIGS_PATH = Path(__file__).parent / "test.configs.json"
with _TEST_CONFIGS_PATH.open() as _f:
    BASE_CONFIGS = json.load(_f)


def _make_mock_repository(local_branches=None):
    """Create a mock pygit2.Repository with standard structure."""
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


def test_pull_fails_without_repos_json(tmp_path):
    """Test that pull fails when configs.json is not found."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(main, ["pull"])

        assert result.exit_code == 1
        assert "configs.json not found" in result.output
        assert "Run 'crev init' first" in result.output


@patch("crev.pull.pygit2.clone_repository")
def test_pull_skips_invalid_repo_entry(mock_clone, tmp_path):
    """Test that pull skips repos with missing name, url, or org."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create configs.json with invalid entries
        configs = deepcopy(BASE_CONFIGS)
        configs["repos"] = [
            {
                "org": "valid-org",
                "name": "valid-repo",
                "url": "https://github.com/user/valid.git",
            },
            {"name": "no-url", "org": "some-org"},
            {"url": "https://github.com/user/no-name.git", "org": "some-org"},
            {"name": "no-org", "url": "https://github.com/user/no-org.git"},
            {},
        ]
        with open("configs.json", "w") as f:
            json.dump(configs, f)

        result = runner.invoke(main, ["pull"])

        assert result.exit_code == 0
        assert "Skipping invalid repo entry" in result.output


@patch("crev.pull.pygit2.clone_repository")
def test_pull_skips_prs_when_repo_not_found(mock_clone, tmp_path):
    """Test that pull skips PRs when the repo directory doesn't exist."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create configs.json
        configs = deepcopy(BASE_CONFIGS)
        configs["repos"][0]["pull_requests"] = [123]
        with open("configs.json", "w") as f:
            json.dump(configs, f)

        # clone_repository doesn't actually create the directory in mock
        result = runner.invoke(main, ["pull"])

        assert result.exit_code == 0
        assert "Skipping PRs for test-repo (repo not found)" in result.output


@patch("crev.pull.pygit2.Repository")
def test_pull_handles_pr_fetch_failure(mock_repo_cls, tmp_path):
    """Test that pull handles failures when fetching a PR."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create configs.json
        configs = deepcopy(BASE_CONFIGS)
        configs["repos"][0]["pull_requests"] = [999]
        with open("configs.json", "w") as f:
            json.dump(configs, f)

        # Create existing repo directory with org level
        Path("repos/test-org/test-repo").mkdir(parents=True)

        mock_repo, mock_remote = _make_mock_repository()
        mock_repo_cls.return_value = mock_repo

        # Make PR fetch raise a GitError
        def fetch_side_effect(refspecs=None):
            if refspecs is not None:
                raise pygit2.GitError("fetch failed")

        mock_remote.fetch.side_effect = fetch_side_effect

        result = runner.invoke(main, ["pull"])

        assert result.exit_code == 0
        assert "Failed to fetch PR #999" in result.output
        assert "Done." in result.output


@patch("crev.pull.pygit2.Repository")
def test_pull_skips_invalid_pr_numbers(mock_repo_cls, tmp_path):
    """Test that pull skips invalid PR numbers (non-integers)."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create configs.json with invalid PR numbers
        configs = deepcopy(BASE_CONFIGS)
        configs["repos"][0]["pull_requests"] = [123, "invalid", None, 456]
        with open("configs.json", "w") as f:
            json.dump(configs, f)

        # Create existing repo directory with org level
        Path("repos/test-org/test-repo").mkdir(parents=True)

        mock_repo, mock_remote = _make_mock_repository()
        mock_repo_cls.return_value = mock_repo

        result = runner.invoke(main, ["pull"])

        assert result.exit_code == 0
        assert "Fetching PR #123" in result.output
        assert "Fetching PR #456" in result.output
        assert "Skipping invalid PR number" in result.output

        # Verify: 1 pull fetch + 2 PR fetches (123, 456)
        assert mock_remote.fetch.call_count == 3
