"""Tests for the sum pr command."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from crev import main


def setup_test_project(tmp_path):
    """Set up a test project with configs.json and prompts."""
    # Create configs.json
    configs_data = {
        "llm": {
            "provider": "claude",
            "model": "claude-sonnet-4-5-20250929",
            "temperature": 0.0,
            "max_tokens": 8192,
        },
        "repos": [
            {
                "name": "test-repo",
                "url": "https://github.com/test/repo.git",
                "pull_requests": [1, 2],
            }
        ],
        "prompts": {
            "sum_repo": "prompts/sum.repo.txt",
            "sum_pr": "prompts/sum.pr.txt",
        },
    }

    configs_file = tmp_path / "configs.json"
    with configs_file.open("w") as f:
        json.dump(configs_data, f)

    # Create prompts directory
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()

    # Create prompt files
    (prompts_dir / "sum.repo.txt").write_text("Test repo prompt")
    (prompts_dir / "sum.pr.txt").write_text("Test PR prompt")

    return tmp_path


def test_sum_pr_subcommand_exists():
    """Test that the sum pr subcommand is registered."""
    runner = CliRunner()
    result = runner.invoke(main, ["sum", "--help"])

    assert result.exit_code == 0
    assert "pr" in result.output


def test_sum_pr_requires_configs(tmp_path):
    """Test that sum pr fails without configs.json."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(main, ["sum", "pr", "test-repo"])

        assert result.exit_code != 0
        assert "configs.json not found" in result.output


def test_sum_pr_requires_repo_name(tmp_path):
    """Test that sum pr requires a repo name argument."""
    runner = CliRunner()
    setup_test_project(tmp_path)

    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(main, ["sum", "pr"])

        assert result.exit_code != 0


def test_sum_pr_checks_pr_directory(tmp_path):
    """Test that sum pr checks for PR directory."""
    runner = CliRunner()
    setup_test_project(tmp_path)

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create necessary directories
        (tmp_path / "pullrequests").mkdir()

        result = runner.invoke(main, ["sum", "pr", "test-repo"])

        # Should fail because PR directories don't exist
        assert "PR directory not found" in result.output or result.exit_code != 0


def test_sum_pr_with_specific_pr_number(tmp_path):
    """Test that sum pr accepts a specific PR number."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Setup test project in the isolated filesystem
        setup_test_project(Path.cwd())

        # Create PR directory structure
        pr_dir = Path("pullrequests") / "test-repo" / "1"
        pr_dir.mkdir(parents=True)

        # Create sum directory with diff.txt
        sum_dir = pr_dir / "sum"
        sum_dir.mkdir()
        (sum_dir / "diff.txt").write_text("diff content")

        # Create code directory
        code_dir = pr_dir / "code"
        code_dir.mkdir()

        # Mock the LLM client
        with patch("crev.sum.sum_pr.get_llm_client") as mock_llm:
            mock_response = MagicMock()
            mock_response.content = "Test PR summary"
            mock_llm.return_value.invoke.return_value = mock_response

            result = runner.invoke(main, ["sum", "pr", "test-repo", "1"])

            assert result.exit_code == 0
            assert "Summarizing PR #1" in result.output

            # Check that output file was created
            output_file = pr_dir / "summary.pr.1.ai.txt"
            assert output_file.exists()
            assert output_file.read_text() == "Test PR summary"


def test_sum_pr_skips_existing_files(tmp_path):
    """Test that sum pr skips PRs with existing summary files."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Setup test project in the isolated filesystem
        setup_test_project(Path.cwd())

        # Create PR directory structure
        pr_dir = Path("pullrequests") / "test-repo" / "1"
        pr_dir.mkdir(parents=True)

        # Create existing summary file
        output_file = pr_dir / "summary.pr.1.ai.txt"
        output_file.write_text("Existing PR summary")

        result = runner.invoke(main, ["sum", "pr", "test-repo", "1"])

        assert result.exit_code == 0
        assert "already exists, skipping" in result.output


def test_sum_pr_context_caching(tmp_path):
    """Test that sum pr caches context to sum.context.md."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Setup test project in the isolated filesystem
        setup_test_project(Path.cwd())

        # Create PR directory structure
        pr_dir = Path("pullrequests") / "test-repo" / "1"
        pr_dir.mkdir(parents=True)

        # Create sum directory with diff.txt
        sum_dir = pr_dir / "sum"
        sum_dir.mkdir()
        (sum_dir / "diff.txt").write_text("diff content")

        # Create code directory
        code_dir = pr_dir / "code"
        code_dir.mkdir()

        # Mock the LLM client
        with patch("crev.sum.sum_pr.get_llm_client") as mock_llm:
            mock_response = MagicMock()
            mock_response.content = "Test PR summary"
            mock_llm.return_value.invoke.return_value = mock_response

            result = runner.invoke(main, ["sum", "pr", "test-repo", "1"])

            assert result.exit_code == 0

            # Check that context file was created
            context_file = sum_dir / "sum.context.md"
            assert context_file.exists()
            assert "# Attachments" in context_file.read_text()


def test_sum_pr_loads_cached_context(tmp_path):
    """Test that sum pr loads cached context if available."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Setup test project in the isolated filesystem
        setup_test_project(Path.cwd())

        # Create PR directory structure
        pr_dir = Path("pullrequests") / "test-repo" / "1"
        pr_dir.mkdir(parents=True)

        # Create sum directory with cached context
        sum_dir = pr_dir / "sum"
        sum_dir.mkdir()
        context_file = sum_dir / "sum.context.md"
        context_file.write_text("# Cached context")

        # Create code directory (shouldn't be read since we have cache)
        code_dir = pr_dir / "code"
        code_dir.mkdir()

        # Mock the LLM client
        with patch("crev.sum.sum_pr.get_llm_client") as mock_llm:
            mock_response = MagicMock()
            mock_response.content = "Test PR summary"
            mock_llm.return_value.invoke.return_value = mock_response

            result = runner.invoke(main, ["sum", "pr", "test-repo", "1"])

            assert result.exit_code == 0
            assert "Loading cached PR context" in result.output


def test_sum_pr_context_only_flag(tmp_path):
    """Test that sum pr --context-only only collects context."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Setup test project in the isolated filesystem
        setup_test_project(Path.cwd())

        # Create PR directory structure
        pr_dir = Path("pullrequests") / "test-repo" / "1"
        pr_dir.mkdir(parents=True)

        # Create sum directory with diff.txt
        sum_dir = pr_dir / "sum"
        sum_dir.mkdir()
        (sum_dir / "diff.txt").write_text("diff content")

        # Create code directory
        code_dir = pr_dir / "code"
        code_dir.mkdir()

        result = runner.invoke(main, ["sum", "pr", "test-repo", "1", "--context-only"])

        assert result.exit_code == 0
        assert "Context collection complete" in result.output

        # Check that context file was created
        context_file = sum_dir / "sum.context.md"
        assert context_file.exists()

        # Check that summary file was NOT created
        output_file = pr_dir / "summary.pr.1.ai.txt"
        assert not output_file.exists()
