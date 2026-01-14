"""Tests for the sum repo command."""

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


def test_sum_repo_subcommand_exists():
    """Test that the sum repo subcommand is registered."""
    runner = CliRunner()
    result = runner.invoke(main, ["sum", "--help"])

    assert result.exit_code == 0
    assert "repo" in result.output


def test_sum_repo_requires_configs(tmp_path):
    """Test that sum repo fails without configs.json."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(main, ["sum", "repo"])

        assert result.exit_code != 0
        assert "configs.json not found" in result.output


def test_sum_repo_checks_repos_directory(tmp_path):
    """Test that sum repo checks for repos directory."""
    runner = CliRunner()
    setup_test_project(tmp_path)

    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(main, ["sum", "repo"])

        assert "repos directory not found" in result.output or result.exit_code != 0


def test_sum_repo_with_specific_repo_name(tmp_path):
    """Test that sum repo accepts a specific repo name."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Setup test project in the isolated filesystem
        setup_test_project(Path.cwd())

        # Create repos directory
        repos_dir = Path("repos")
        repos_dir.mkdir()
        (repos_dir / "test-repo").mkdir()

        # Create a simple README in the repo
        (repos_dir / "test-repo" / "README.md").write_text("# Test Repo")

        # Create pullrequests directory
        Path("pullrequests").mkdir()

        # Mock the LLM client
        with patch("crev.sum.sum_repo.get_llm_client") as mock_llm:
            mock_response = MagicMock()
            mock_response.content = "Test summary"
            mock_llm.return_value.invoke.return_value = mock_response

            result = runner.invoke(main, ["sum", "repo", "test-repo"])

            assert result.exit_code == 0
            assert "Summarizing repository: test-repo" in result.output

            # Check that output file was created
            output_file = Path("pullrequests") / "test-repo" / "summary.test-repo.ai.txt"
            assert output_file.exists()
            assert output_file.read_text() == "Test summary"


def test_sum_repo_skips_existing_files(tmp_path):
    """Test that sum repo skips repos with existing summary files."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Setup test project in the isolated filesystem
        setup_test_project(Path.cwd())

        # Create repos directory
        repos_dir = Path("repos")
        repos_dir.mkdir()
        (repos_dir / "test-repo").mkdir()

        # Create pullrequests directory and existing summary file
        output_dir = Path("pullrequests") / "test-repo"
        output_dir.mkdir(parents=True)
        output_file = output_dir / "summary.test-repo.ai.txt"
        output_file.write_text("Existing summary")

        result = runner.invoke(main, ["sum", "repo", "test-repo"])

        assert result.exit_code == 0
        assert "already exists, skipping" in result.output


def test_sum_repo_processes_all_repos(tmp_path):
    """Test that sum repo processes all repos when no repo name is specified."""
    runner = CliRunner()

    # Create configs with multiple repos
    configs_data = {
        "llm": {
            "provider": "claude",
            "model": "claude-sonnet-4-5-20250929",
            "temperature": 0.0,
            "max_tokens": 8192,
        },
        "repos": [
            {
                "name": "repo1",
                "url": "https://github.com/test/repo1.git",
                "pull_requests": [],
            },
            {
                "name": "repo2",
                "url": "https://github.com/test/repo2.git",
                "pull_requests": [],
            },
        ],
        "prompts": {
            "sum_repo": "prompts/sum.repo.txt",
            "sum_pr": "prompts/sum.pr.txt",
        },
    }

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Use Path.cwd() instead of tmp_path to create files in the isolated filesystem
        configs_file = Path("configs.json")
        with configs_file.open("w") as f:
            json.dump(configs_data, f)

        # Create prompts directory
        prompts_dir = Path("prompts")
        prompts_dir.mkdir()
        (prompts_dir / "sum.repo.txt").write_text("Test repo prompt")

        # Create repos directory
        repos_dir = Path("repos")
        repos_dir.mkdir()
        (repos_dir / "repo1").mkdir()
        (repos_dir / "repo2").mkdir()

        # Create pullrequests directory
        Path("pullrequests").mkdir()

        # Mock the LLM client
        with patch("crev.sum.sum_repo.get_llm_client") as mock_llm:
            mock_response = MagicMock()
            mock_response.content = "Test summary"
            mock_llm.return_value.invoke.return_value = mock_response

            result = runner.invoke(main, ["sum", "repo"])

            assert result.exit_code == 0
            assert "Summarizing repository: repo1" in result.output
            assert "Summarizing repository: repo2" in result.output
