"""Tests for MCP server endpoints."""

import json

import pytest

from crev.mcp_serv.server import create_server


@pytest.fixture
def mcp_server():
    """Create and return an MCP server instance."""
    return create_server()


@pytest.fixture
def setup_configs(tmp_path, monkeypatch):
    """Set up a configs.json file and change to tmp directory."""
    monkeypatch.chdir(tmp_path)

    config_data = {
        "repos": [
            {"org": "test-org", "name": "repo1", "pull_requests": [1, 2, 3]},
            {"org": "test-org", "name": "repo2", "pull_requests": [10]},
            {"org": "other-org", "name": "repo3", "pull_requests": [100]},
        ]
    }
    (tmp_path / "configs.json").write_text(json.dumps(config_data))
    return tmp_path


@pytest.fixture
def setup_summaries(setup_configs):
    """Set up summary files in data directory."""
    tmp_path = setup_configs

    # Create repo summaries
    for org, repo in [("test-org", "repo1"), ("test-org", "repo2")]:
        sum_dir = tmp_path / "data" / org / repo / "sum"
        sum_dir.mkdir(parents=True)
        (sum_dir / f"sum.repo.{repo}.ai.md").write_text(
            f"# {repo} Summary\nThis is the summary for {org}/{repo}."
        )

    # Create PR summaries
    pr_configs = [
        ("test-org", "repo1", 1),
        ("test-org", "repo1", 2),
        ("test-org", "repo2", 10),
    ]
    for org, repo, pr_num in pr_configs:
        pr_dir = tmp_path / "data" / org / repo / str(pr_num)
        pr_dir.mkdir(parents=True)
        (pr_dir / f"sum.pr.{pr_num}.ai.md").write_text(
            f"# PR #{pr_num} Summary\nChanges for {org}/{repo}#{pr_num}."
        )

    return tmp_path


class TestSumRepoEndpoint:
    """Tests for the sum_repo endpoint."""

    def test_sum_repo_returns_summaries(self, mcp_server, setup_summaries):
        """Test sum_repo returns summaries for requested orgs."""
        # Get the tool from the server
        sum_repo_tool = None
        for tool in mcp_server._tool_manager._tools.values():
            if tool.name == "sum_repo":
                sum_repo_tool = tool
                break

        assert sum_repo_tool is not None

        # Call the tool function directly
        result = sum_repo_tool.fn(orgs=["test-org"])

        assert "test-org/repo1" in result
        assert "test-org/repo2" in result
        assert "other-org/repo3" not in result
        assert "# repo1 Summary" in result["test-org/repo1"]

    def test_sum_repo_empty_orgs(self, mcp_server, setup_summaries):
        """Test sum_repo with empty orgs list."""
        sum_repo_tool = None
        for tool in mcp_server._tool_manager._tools.values():
            if tool.name == "sum_repo":
                sum_repo_tool = tool
                break

        result = sum_repo_tool.fn(orgs=[])
        assert result == {}

    def test_sum_repo_nonexistent_org(self, mcp_server, setup_summaries):
        """Test sum_repo with non-existent org."""
        sum_repo_tool = None
        for tool in mcp_server._tool_manager._tools.values():
            if tool.name == "sum_repo":
                sum_repo_tool = tool
                break

        result = sum_repo_tool.fn(orgs=["nonexistent"])
        assert result == {}

    def test_sum_repo_no_config(self, mcp_server, tmp_path, monkeypatch):
        """Test sum_repo when configs.json doesn't exist."""
        monkeypatch.chdir(tmp_path)

        sum_repo_tool = None
        for tool in mcp_server._tool_manager._tools.values():
            if tool.name == "sum_repo":
                sum_repo_tool = tool
                break

        result = sum_repo_tool.fn(orgs=["any-org"])
        assert "error" in result


class TestSumPrEndpoint:
    """Tests for the sum_pr endpoint."""

    def test_sum_pr_returns_summaries(self, mcp_server, setup_summaries):
        """Test sum_pr returns summaries for requested PRs."""
        sum_pr_tool = None
        for tool in mcp_server._tool_manager._tools.values():
            if tool.name == "sum_pr":
                sum_pr_tool = tool
                break

        assert sum_pr_tool is not None

        repos = [{"org": "test-org", "name": "repo1", "pull_requests": [1, 2]}]
        result = sum_pr_tool.fn(repos=repos)

        assert "test-org/repo1/1" in result
        assert "test-org/repo1/2" in result
        assert "# PR #1 Summary" in result["test-org/repo1/1"]

    def test_sum_pr_nonexistent_pr(self, mcp_server, setup_summaries):
        """Test sum_pr with non-existent PR."""
        sum_pr_tool = None
        for tool in mcp_server._tool_manager._tools.values():
            if tool.name == "sum_pr":
                sum_pr_tool = tool
                break

        repos = [{"org": "test-org", "name": "repo1", "pull_requests": [999]}]
        result = sum_pr_tool.fn(repos=repos)

        assert "test-org/repo1/999" in result
        assert result["test-org/repo1/999"] is None

    def test_sum_pr_empty_repos(self, mcp_server, setup_summaries):
        """Test sum_pr with empty repos list."""
        sum_pr_tool = None
        for tool in mcp_server._tool_manager._tools.values():
            if tool.name == "sum_pr":
                sum_pr_tool = tool
                break

        result = sum_pr_tool.fn(repos=[])
        assert result == {}

    def test_sum_pr_filters_non_int_pr_numbers(self, mcp_server, setup_summaries):
        """Test sum_pr filters out non-integer PR numbers."""
        sum_pr_tool = None
        for tool in mcp_server._tool_manager._tools.values():
            if tool.name == "sum_pr":
                sum_pr_tool = tool
                break

        repos = [{"org": "test-org", "name": "repo1", "pull_requests": [1, "invalid"]}]
        result = sum_pr_tool.fn(repos=repos)

        assert "test-org/repo1/1" in result
        assert len(result) == 1  # Only the valid int PR


class TestSumListEndpoint:
    """Tests for the sum_list endpoint."""

    def test_sum_list_returns_available(self, mcp_server, setup_summaries):
        """Test sum_list returns available summaries."""
        sum_list_tool = None
        for tool in mcp_server._tool_manager._tools.values():
            if tool.name == "sum_list":
                sum_list_tool = tool
                break

        assert sum_list_tool is not None

        result = sum_list_tool.fn()

        assert "repo_summaries" in result
        assert "pr_summaries" in result
        assert "repos" in result

        # Check repo summaries
        assert len(result["repo_summaries"]) == 2

        # Check PR summaries
        assert len(result["pr_summaries"]) == 3

        # Check repos from config
        assert len(result["repos"]) == 3

    def test_sum_list_empty_data(self, mcp_server, setup_configs):
        """Test sum_list when no data directory exists."""
        sum_list_tool = None
        for tool in mcp_server._tool_manager._tools.values():
            if tool.name == "sum_list":
                sum_list_tool = tool
                break

        result = sum_list_tool.fn()

        assert result["repo_summaries"] == []
        assert result["pr_summaries"] == []
        assert len(result["repos"]) == 3  # From configs

    def test_sum_list_no_config(self, mcp_server, tmp_path, monkeypatch):
        """Test sum_list when configs.json doesn't exist."""
        monkeypatch.chdir(tmp_path)

        sum_list_tool = None
        for tool in mcp_server._tool_manager._tools.values():
            if tool.name == "sum_list":
                sum_list_tool = tool
                break

        result = sum_list_tool.fn()

        assert result["repo_summaries"] == []
        assert result["pr_summaries"] == []
        assert result["repos"] == []


class TestStackEndpoint:
    """Tests for the stack endpoint."""

    def test_stack_returns_repo_summaries(self, mcp_server, setup_summaries):
        """Test stack returns repo summaries for an org."""
        stack_tool = None
        for tool in mcp_server._tool_manager._tools.values():
            if tool.name == "stack":
                stack_tool = tool
                break

        assert stack_tool is not None

        result = stack_tool.fn(org="test-org")

        assert result["org"] == "test-org"
        assert "repos" in result
        assert "repo1" in result["repos"]
        assert "repo2" in result["repos"]
        assert "# repo1 Summary" in result["repos"]["repo1"]

    def test_stack_nonexistent_org(self, mcp_server, setup_summaries):
        """Test stack with non-existent org."""
        stack_tool = None
        for tool in mcp_server._tool_manager._tools.values():
            if tool.name == "stack":
                stack_tool = tool
                break

        result = stack_tool.fn(org="nonexistent")

        assert result["org"] == "nonexistent"
        assert result["repos"] == {}

    def test_stack_no_summaries(self, mcp_server, setup_configs):
        """Test stack when repos exist but no summaries."""
        stack_tool = None
        for tool in mcp_server._tool_manager._tools.values():
            if tool.name == "stack":
                stack_tool = tool
                break

        result = stack_tool.fn(org="test-org")

        assert result["org"] == "test-org"
        assert result["repos"] == {}


class TestAccomplishmentsEndpoint:
    """Tests for the accomplishments endpoint."""

    def test_accomplishments_returns_pr_summaries(self, mcp_server, setup_summaries):
        """Test accomplishments returns PR summaries for an org."""
        accomplishments_tool = None
        for tool in mcp_server._tool_manager._tools.values():
            if tool.name == "accomplishments":
                accomplishments_tool = tool
                break

        assert accomplishments_tool is not None

        result = accomplishments_tool.fn(org="test-org")

        assert result["org"] == "test-org"
        assert "repos" in result
        assert "repo1" in result["repos"]
        assert "pull_requests" in result["repos"]["repo1"]
        assert 1 in result["repos"]["repo1"]["pull_requests"]
        assert 2 in result["repos"]["repo1"]["pull_requests"]

    def test_accomplishments_nonexistent_org(self, mcp_server, setup_summaries):
        """Test accomplishments with non-existent org."""
        accomplishments_tool = None
        for tool in mcp_server._tool_manager._tools.values():
            if tool.name == "accomplishments":
                accomplishments_tool = tool
                break

        result = accomplishments_tool.fn(org="nonexistent")

        assert result["org"] == "nonexistent"
        assert result["repos"] == {}

    def test_accomplishments_no_summaries(self, mcp_server, setup_configs):
        """Test accomplishments when repos exist but no PR summaries."""
        accomplishments_tool = None
        for tool in mcp_server._tool_manager._tools.values():
            if tool.name == "accomplishments":
                accomplishments_tool = tool
                break

        result = accomplishments_tool.fn(org="test-org")

        assert result["org"] == "test-org"
        # Repos should be present but with empty pull_requests
        assert "repo1" in result["repos"]
        assert result["repos"]["repo1"]["pull_requests"] == {}


class TestOrgListEndpoint:
    """Tests for the org_list endpoint."""

    def test_org_list_returns_orgs(self, mcp_server, setup_configs):
        """Test org_list returns distinct organizations."""
        org_list_tool = None
        for tool in mcp_server._tool_manager._tools.values():
            if tool.name == "org_list":
                org_list_tool = tool
                break

        assert org_list_tool is not None

        result = org_list_tool.fn()

        assert "orgs" in result
        assert "test-org" in result["orgs"]
        assert "other-org" in result["orgs"]
        assert len(result["orgs"]) == 2

    def test_org_list_no_config(self, mcp_server, tmp_path, monkeypatch):
        """Test org_list when configs.json doesn't exist."""
        monkeypatch.chdir(tmp_path)

        org_list_tool = None
        for tool in mcp_server._tool_manager._tools.values():
            if tool.name == "org_list":
                org_list_tool = tool
                break

        result = org_list_tool.fn()

        assert result["orgs"] == []
