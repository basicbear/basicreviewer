"""Tests for the mcp-serv command."""

import json
from pathlib import Path

import pytest

from crev.mcp_serv.server import create_server
from crev.mcp_serv.utils import (
    find_pr_summary,
    find_repo_summary,
    get_data_dir,
    get_distinct_orgs,
    get_repos_for_org,
    list_available_summaries,
    load_configs,
)


class TestCreateServer:
    """Tests for the create_server function."""

    def test_create_server_returns_fastmcp_instance(self):
        """Test that create_server returns a FastMCP instance."""
        from fastmcp import FastMCP

        server = create_server()
        assert isinstance(server, FastMCP)

    def test_create_server_has_name(self):
        """Test that the server is named 'crev'."""
        server = create_server()
        assert server.name == "crev"


class TestLoadConfigs:
    """Tests for the load_configs utility function."""

    def test_load_configs_success(self, tmp_path, monkeypatch):
        """Test loading configs.json successfully."""
        monkeypatch.chdir(tmp_path)

        config_data = {
            "repos": [{"org": "test-org", "name": "test-repo", "pull_requests": [1, 2]}]
        }
        (tmp_path / "configs.json").write_text(json.dumps(config_data))

        result = load_configs()
        assert result == config_data

    def test_load_configs_file_not_found(self, tmp_path, monkeypatch):
        """Test that load_configs raises FileNotFoundError when file doesn't exist."""
        monkeypatch.chdir(tmp_path)

        with pytest.raises(FileNotFoundError) as exc_info:
            load_configs()

        assert "configs.json not found" in str(exc_info.value)
        assert "crev init" in str(exc_info.value)


class TestGetDataDir:
    """Tests for the get_data_dir utility function."""

    def test_get_data_dir_returns_path(self):
        """Test that get_data_dir returns the data directory path."""
        result = get_data_dir()
        assert result == Path("data")


class TestFindRepoSummary:
    """Tests for the find_repo_summary utility function."""

    def test_find_repo_summary_with_md_file(self, tmp_path, monkeypatch):
        """Test finding a repo summary with .md file."""
        monkeypatch.chdir(tmp_path)

        # Create directory structure
        sum_dir = tmp_path / "data" / "test-org" / "test-repo" / "sum"
        sum_dir.mkdir(parents=True)
        summary_content = "# Repository Summary\nThis is a test summary."
        (sum_dir / "sum.repo.test-repo.ai.md").write_text(summary_content)

        result = find_repo_summary("test-org", "test-repo")
        assert result == summary_content

    def test_find_repo_summary_with_json_file(self, tmp_path, monkeypatch):
        """Test finding a repo summary with .json file (fallback)."""
        monkeypatch.chdir(tmp_path)

        # Create directory structure
        sum_dir = tmp_path / "data" / "test-org" / "test-repo" / "sum"
        sum_dir.mkdir(parents=True)
        summary_content = '{"summary": "test"}'
        (sum_dir / "sum.repo.test-repo.ai.json").write_text(summary_content)

        result = find_repo_summary("test-org", "test-repo")
        assert result == summary_content

    def test_find_repo_summary_not_found(self, tmp_path, monkeypatch):
        """Test finding a repo summary when directory doesn't exist."""
        monkeypatch.chdir(tmp_path)

        result = find_repo_summary("nonexistent-org", "nonexistent-repo")
        assert result is None

    def test_find_repo_summary_no_summary_file(self, tmp_path, monkeypatch):
        """Test finding a repo summary when sum dir exists but no file."""
        monkeypatch.chdir(tmp_path)

        sum_dir = tmp_path / "data" / "test-org" / "test-repo" / "sum"
        sum_dir.mkdir(parents=True)

        result = find_repo_summary("test-org", "test-repo")
        assert result is None


class TestFindPrSummary:
    """Tests for the find_pr_summary utility function."""

    def test_find_pr_summary_success(self, tmp_path, monkeypatch):
        """Test finding a PR summary successfully."""
        monkeypatch.chdir(tmp_path)

        # Create directory structure
        pr_dir = tmp_path / "data" / "test-org" / "test-repo" / "123"
        pr_dir.mkdir(parents=True)
        summary_content = "# PR Summary\nThis PR adds a feature."
        (pr_dir / "sum.pr.123.ai.md").write_text(summary_content)

        result = find_pr_summary("test-org", "test-repo", 123)
        assert result == summary_content

    def test_find_pr_summary_not_found(self, tmp_path, monkeypatch):
        """Test finding a PR summary when directory doesn't exist."""
        monkeypatch.chdir(tmp_path)

        result = find_pr_summary("nonexistent-org", "nonexistent-repo", 999)
        assert result is None

    def test_find_pr_summary_no_file(self, tmp_path, monkeypatch):
        """Test finding a PR summary when directory exists but no file."""
        monkeypatch.chdir(tmp_path)

        pr_dir = tmp_path / "data" / "test-org" / "test-repo" / "123"
        pr_dir.mkdir(parents=True)

        result = find_pr_summary("test-org", "test-repo", 123)
        assert result is None


class TestListAvailableSummaries:
    """Tests for the list_available_summaries utility function."""

    def test_list_available_summaries_empty(self, tmp_path, monkeypatch):
        """Test listing summaries when data dir doesn't exist."""
        monkeypatch.chdir(tmp_path)

        result = list_available_summaries()
        assert result == {"repo_summaries": [], "pr_summaries": []}

    def test_list_available_summaries_with_data(self, tmp_path, monkeypatch):
        """Test listing summaries with existing data."""
        monkeypatch.chdir(tmp_path)

        # Create repo summary
        sum_dir = tmp_path / "data" / "org1" / "repo1" / "sum"
        sum_dir.mkdir(parents=True)
        (sum_dir / "sum.repo.repo1.ai.md").write_text("# Repo summary")

        # Create PR summary
        pr_dir = tmp_path / "data" / "org1" / "repo1" / "42"
        pr_dir.mkdir(parents=True)
        (pr_dir / "sum.pr.42.ai.md").write_text("# PR summary")

        result = list_available_summaries()

        assert len(result["repo_summaries"]) == 1
        assert result["repo_summaries"][0]["org"] == "org1"
        assert result["repo_summaries"][0]["repo"] == "repo1"

        assert len(result["pr_summaries"]) == 1
        assert result["pr_summaries"][0]["org"] == "org1"
        assert result["pr_summaries"][0]["repo"] == "repo1"
        assert result["pr_summaries"][0]["pr_number"] == 42


class TestGetDistinctOrgs:
    """Tests for the get_distinct_orgs utility function."""

    def test_get_distinct_orgs_success(self, tmp_path, monkeypatch):
        """Test getting distinct orgs from configs."""
        monkeypatch.chdir(tmp_path)

        config_data = {
            "repos": [
                {"org": "org-b", "name": "repo1"},
                {"org": "org-a", "name": "repo2"},
                {"org": "org-b", "name": "repo3"},
            ]
        }
        (tmp_path / "configs.json").write_text(json.dumps(config_data))

        result = get_distinct_orgs()
        assert result == ["org-a", "org-b"]  # Sorted and deduplicated

    def test_get_distinct_orgs_no_config(self, tmp_path, monkeypatch):
        """Test getting orgs when configs.json doesn't exist."""
        monkeypatch.chdir(tmp_path)

        result = get_distinct_orgs()
        assert result == []


class TestGetReposForOrg:
    """Tests for the get_repos_for_org utility function."""

    def test_get_repos_for_org_success(self, tmp_path, monkeypatch):
        """Test getting repos for a specific org."""
        monkeypatch.chdir(tmp_path)

        config_data = {
            "repos": [
                {"org": "org1", "name": "repo1", "pull_requests": [1]},
                {"org": "org2", "name": "repo2", "pull_requests": [2]},
                {"org": "org1", "name": "repo3", "pull_requests": [3]},
            ]
        }
        (tmp_path / "configs.json").write_text(json.dumps(config_data))

        result = get_repos_for_org("org1")
        assert len(result) == 2
        assert result[0]["name"] == "repo1"
        assert result[1]["name"] == "repo3"

    def test_get_repos_for_org_not_found(self, tmp_path, monkeypatch):
        """Test getting repos for a non-existent org."""
        monkeypatch.chdir(tmp_path)

        config_data = {"repos": [{"org": "org1", "name": "repo1"}]}
        (tmp_path / "configs.json").write_text(json.dumps(config_data))

        result = get_repos_for_org("nonexistent")
        assert result == []

    def test_get_repos_for_org_no_config(self, tmp_path, monkeypatch):
        """Test getting repos when configs.json doesn't exist."""
        monkeypatch.chdir(tmp_path)

        result = get_repos_for_org("any-org")
        assert result == []
