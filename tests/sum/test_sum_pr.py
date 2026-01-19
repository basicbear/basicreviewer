"""Tests for the sum pr command."""

import json
from copy import deepcopy
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from crev import main

# Load base configs data from JSON file
_TEST_CONFIGS_PATH = Path(__file__).parent / "test.configs.json"
with _TEST_CONFIGS_PATH.open() as _f:
    BASE_CONFIGS_DATA = json.load(_f)


def setup_test_project(tmp_path):
    """Set up a test project with configs.json and prompts."""
    # Create configs.json from base data
    configs = deepcopy(BASE_CONFIGS_DATA)

    configs_file = tmp_path / "configs.json"
    with configs_file.open("w") as f:
        json.dump(configs, f)

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


def test_sum_pr_no_args_processes_all(tmp_path):
    """Test that sum pr with no args processes all repos."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Setup test project in the isolated filesystem
        setup_test_project(Path.cwd())

        # Create PR directory structure
        pr_dir = Path("data") / "test-org" / "test-repo" / "1"
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

            result = runner.invoke(main, ["sum", "pr"])

            assert result.exit_code == 0
            assert "Summarizing PR #1" in result.output


def test_sum_pr_checks_pr_directory(tmp_path):
    """Test that sum pr checks for PR directory."""
    runner = CliRunner()
    setup_test_project(tmp_path)

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create necessary directories
        (tmp_path / "data").mkdir()

        result = runner.invoke(main, ["sum", "pr", "test-org", "test-repo"])

        # Should fail because PR directories don't exist
        assert "PR directory not found" in result.output or result.exit_code != 0


def test_sum_pr_with_specific_pr_number(tmp_path):
    """Test that sum pr accepts a specific PR number."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Setup test project in the isolated filesystem
        setup_test_project(Path.cwd())

        # Create PR directory structure
        pr_dir = Path("pullrequests") / "test-org" / "test-repo" / "1"
        pr_dir.mkdir(parents=True)

        # Create output directory
        output_dir = Path("data") / "test-org" / "test-repo" / "1"
        output_dir.mkdir(parents=True)

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

            result = runner.invoke(main, ["sum", "pr", "test-org", "test-repo", "1"])

            assert result.exit_code == 0
            assert "Summarizing PR #1" in result.output

            # Check that output file was created (uses config filename)
            output_file = output_dir / "sum.pr.1.ai.md"
            assert output_file.exists()
            assert output_file.read_text() == "Test PR summary"


def test_sum_pr_skips_existing_files(tmp_path):
    """Test that sum pr skips PRs with existing summary files."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Setup test project in the isolated filesystem
        setup_test_project(Path.cwd())

        # Create PR directory structure (input)
        pr_dir = Path("pullrequests") / "test-org" / "test-repo" / "1"
        pr_dir.mkdir(parents=True)

        # Create output directory
        output_dir = Path("data") / "test-org" / "test-repo" / "1"
        output_dir.mkdir(parents=True)

        # Create existing context file - will be loaded from cache (uses config filename)
        context_file = output_dir / "sum.pr.1.context.md"
        context_file.write_text("# Cached context")

        # Create existing summary file - triggers skip via bypass_keys (uses config filename)
        output_file = pr_dir / "sum.pr.1.ai.md"
        output_file.write_text("Existing PR summary")

        result = runner.invoke(main, ["sum", "pr", "test-org", "test-repo", "1"])

        assert result.exit_code == 0
        # The context is loaded from cache, then summary generation is skipped
        assert "Loading cached result from:" in result.output


def test_sum_pr_context_caching(tmp_path):
    """Test that sum pr caches context to sum.context.md."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Setup test project in the isolated filesystem
        setup_test_project(Path.cwd())

        # Create PR directory structure (input)
        pr_dir = Path("pullrequests") / "test-org" / "test-repo" / "1"
        pr_dir.mkdir(parents=True)

        # Create output directory
        output_dir = Path("data") / "test-org" / "test-repo" / "1"
        output_dir.mkdir(parents=True)

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

            result = runner.invoke(main, ["sum", "pr", "test-org", "test-repo", "1"])

            assert result.exit_code == 0

            # Check that context file was created (uses config filename)
            context_file = output_dir / "sum.pr.1.context.md"
            assert context_file.exists()
            # The context collector returns attachments format
            assert context_file.read_text()  # Just verify it has content


def test_sum_pr_loads_cached_context(tmp_path):
    """Test that sum pr loads cached context if available."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Setup test project in the isolated filesystem
        setup_test_project(Path.cwd())

        # Create PR directory structure (input)
        pr_dir = Path("pullrequests") / "test-org" / "test-repo" / "1"
        pr_dir.mkdir(parents=True)

        # Create output directory
        output_dir = Path("data") / "test-org" / "test-repo" / "1"
        output_dir.mkdir(parents=True)

        # Create cached context file (uses config filename)
        context_file = output_dir / "sum.pr.1.context.md"
        context_file.write_text("# Cached context")

        # Create code directory (shouldn't be read since we have cache)
        code_dir = pr_dir / "code"
        code_dir.mkdir()

        # Mock the LLM client
        with patch("crev.sum.sum_pr.get_llm_client") as mock_llm:
            mock_response = MagicMock()
            mock_response.content = "Test PR summary"
            mock_llm.return_value.invoke.return_value = mock_response

            result = runner.invoke(main, ["sum", "pr", "test-org", "test-repo", "1"])

            assert result.exit_code == 0
            assert "Loading cached result from:" in result.output


def test_sum_pr_context_only_flag(tmp_path):
    """Test that sum pr --context-only only collects context."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Setup test project in the isolated filesystem
        setup_test_project(Path.cwd())

        # Create PR directory structure (input)
        pr_dir = Path("pullrequests") / "test-org" / "test-repo" / "1"
        pr_dir.mkdir(parents=True)

        # Create output directory
        output_dir = Path("data") / "test-org" / "test-repo" / "1"
        output_dir.mkdir(parents=True)

        # Create sum directory with diff.txt
        sum_dir = pr_dir / "sum"
        sum_dir.mkdir()
        (sum_dir / "diff.txt").write_text("diff content")

        # Create code directory
        code_dir = pr_dir / "code"
        code_dir.mkdir()

        result = runner.invoke(
            main, ["sum", "pr", "test-org", "test-repo", "1", "--context-only"]
        )

        assert result.exit_code == 0
        assert "Context collection complete" in result.output

        # Check that context file was created (uses config filename)
        context_file = output_dir / "sum.pr.1.context.md"
        assert context_file.exists()

        # Check that summary file was NOT created (uses config filename)
        output_file = pr_dir / "sum.pr.1.ai.md"
        assert not output_file.exists()


def test_sum_pr_with_dot_wildcard(tmp_path):
    """Test that sum pr accepts '.' as wildcard for all PRs."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Setup test project in the isolated filesystem
        setup_test_project(Path.cwd())

        # Create PR directory structure for PRs 1 and 2
        for pr_num in [1, 2]:
            pr_dir = Path("data") / "test-org" / "test-repo" / str(pr_num)
            pr_dir.mkdir(parents=True)

            # Create sum directory with diff.txt
            sum_dir = pr_dir / "sum"
            sum_dir.mkdir()
            (sum_dir / "diff.txt").write_text(f"diff content for PR {pr_num}")

            # Create code directory
            code_dir = pr_dir / "code"
            code_dir.mkdir()

        # Mock the LLM client
        with patch("crev.sum.sum_pr.get_llm_client") as mock_llm:
            mock_response = MagicMock()
            mock_response.content = "Test PR summary"
            mock_llm.return_value.invoke.return_value = mock_response

            # Use "." to process all PRs
            result = runner.invoke(main, ["sum", "pr", "test-org", "test-repo", "."])

            assert result.exit_code == 0
            assert "Summarizing PR #1" in result.output
            assert "Summarizing PR #2" in result.output


def test_sum_pr_with_org_only(tmp_path):
    """Test that sum pr with only org processes all repos in that org."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Setup test project in the isolated filesystem
        setup_test_project(Path.cwd())

        # Create PR directory structure
        pr_dir = Path("data") / "test-org" / "test-repo" / "1"
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

            result = runner.invoke(main, ["sum", "pr", "test-org"])

            assert result.exit_code == 0
            assert "Summarizing PR #1" in result.output
