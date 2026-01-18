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
            "sum_repo_file_category": "prompts/sum_repo_file_category.txt",
            "sum_repo_structure": "prompts/sum_repo_structure.txt",
            "sum_repo_app": "prompts/sum_repo_app.txt",
            "sum_repo_test": "prompts/sum_repo_test.txt",
            "sum_repo_infra": "prompts/sum_repo_infra.txt",
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
    (prompts_dir / "sum_repo_file_category.txt").write_text("Categorize files prompt")
    (prompts_dir / "sum_repo_structure.txt").write_text("Structure prompt")
    (prompts_dir / "sum_repo_app.txt").write_text("App prompt")
    (prompts_dir / "sum_repo_test.txt").write_text("Test prompt")
    (prompts_dir / "sum_repo_infra.txt").write_text("Infra prompt")

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

    with runner.isolated_filesystem(temp_dir=tmp_path):
        setup_test_project(Path.cwd())

        result = runner.invoke(main, ["sum", "repo"])

        assert "repos directory not found" in result.output or result.exit_code != 0


def test_sum_repo_with_specific_repo_name(tmp_path):
    """Test that sum repo accepts a specific repo name."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Setup test project in the isolated filesystem
        setup_test_project(Path.cwd())

        # Create repos directory with a git repo
        repos_dir = Path("repos")
        repos_dir.mkdir()
        repo_dir = repos_dir / "test-repo"
        repo_dir.mkdir()

        # Create a simple README in the repo
        (repo_dir / "README.md").write_text("# Test Repo")
        (repo_dir / "main.py").write_text("print('hello')")

        # Create pullrequests directory
        Path("pullrequests").mkdir()

        # Mock the git commands and LLM client
        with (
            patch("crev.sum.sum_repo._get_git_version_info") as mock_git,
            patch("crev.sum.sum_repo.get_llm_client") as mock_llm,
            patch(
                "crev.sum.sum_repo.collect_file_category"
            ) as mock_collect_file_category,
            patch(
                "crev.sum.sum_repo.collect_structure_context"
            ) as mock_collect_structure,
            patch("crev.sum.sum_repo.collect_repo_context") as mock_collect_repo,
        ):
            mock_git.return_value = (42, "abc1234567")

            # Set up LLM mock responses
            mock_response = MagicMock()
            mock_llm_instance = MagicMock()
            mock_llm.return_value = mock_llm_instance

            # Configure response for file categorization (returns JSON)
            categorization_response = MagicMock()
            categorization_response.content = json.dumps(
                {"app": ["main.py"], "test": [], "infra": ["README.md"]}
            )

            # Configure responses for other LLM calls
            structure_response = MagicMock()
            structure_response.content = "Structure summary"

            app_response = MagicMock()
            app_response.content = "App analysis"

            infra_response = MagicMock()
            infra_response.content = "Infra analysis"

            mock_llm_instance.invoke.side_effect = [
                categorization_response,
                structure_response,
                app_response,
                infra_response,
            ]

            # Set up context collector mocks
            mock_collect_file_category.return_value = "file listing context"
            mock_collect_structure.return_value = "structure context"
            mock_collect_repo.return_value = "repo context"

            result = runner.invoke(main, ["sum", "repo", "test-repo"])

            assert result.exit_code == 0
            assert "Summarizing repository: test-repo" in result.output

            # Check that output file was created in the new location
            output_dir = Path("pullrequests") / "test-repo" / "sum"
            assert output_dir.exists()

            # Check for output file with versioned name
            output_file = output_dir / "sum.repo.42.abc1234567.ai.md"
            assert output_file.exists()
            content = output_file.read_text()
            assert "Repository Summary: test-repo" in content


def test_sum_repo_skips_existing_final_output(tmp_path):
    """Test that sum repo skips repos with existing final output files."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Setup test project in the isolated filesystem
        setup_test_project(Path.cwd())

        # Create repos directory with git repo
        repos_dir = Path("repos")
        repos_dir.mkdir()
        repo_dir = repos_dir / "test-repo"
        repo_dir.mkdir()
        (repo_dir / "README.md").write_text("# Test Repo")

        # Create pullrequests/test-repo/sum directory and existing output file
        output_dir = Path("pullrequests") / "test-repo" / "sum"
        output_dir.mkdir(parents=True)
        output_file = output_dir / "sum.repo.42.abc1234567.ai.md"
        output_file.write_text("Existing summary")

        # Mock the git commands
        with patch("crev.sum.sum_repo._get_git_version_info") as mock_git:
            mock_git.return_value = (42, "abc1234567")

            result = runner.invoke(main, ["sum", "repo", "test-repo"])

            assert result.exit_code == 0
            # Should skip because final output exists
            assert "Loading cached result from:" in result.output


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
            "sum_repo_file_category": "prompts/sum_repo_file_category.txt",
            "sum_repo_structure": "prompts/sum_repo_structure.txt",
            "sum_repo_app": "prompts/sum_repo_app.txt",
            "sum_repo_test": "prompts/sum_repo_test.txt",
            "sum_repo_infra": "prompts/sum_repo_infra.txt",
        },
    }

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Use Path.cwd() to create files in the isolated filesystem
        configs_file = Path("configs.json")
        with configs_file.open("w") as f:
            json.dump(configs_data, f)

        # Create prompts directory
        prompts_dir = Path("prompts")
        prompts_dir.mkdir()
        (prompts_dir / "sum.repo.txt").write_text("Test repo prompt")
        (prompts_dir / "sum_repo_file_category.txt").write_text("Categorize prompt")
        (prompts_dir / "sum_repo_structure.txt").write_text("Structure prompt")
        (prompts_dir / "sum_repo_app.txt").write_text("App prompt")
        (prompts_dir / "sum_repo_test.txt").write_text("Test prompt")
        (prompts_dir / "sum_repo_infra.txt").write_text("Infra prompt")

        # Create repos directory
        repos_dir = Path("repos")
        repos_dir.mkdir()
        (repos_dir / "repo1").mkdir()
        (repos_dir / "repo1" / "main.py").write_text("# repo1")
        (repos_dir / "repo2").mkdir()
        (repos_dir / "repo2" / "main.py").write_text("# repo2")

        # Create pullrequests directory
        Path("pullrequests").mkdir()

        # Mock the git commands and LLM client
        with (
            patch("crev.sum.sum_repo._get_git_version_info") as mock_git,
            patch("crev.sum.sum_repo.get_llm_client") as mock_llm,
            patch(
                "crev.sum.sum_repo.collect_file_category"
            ) as mock_collect_file_category,
            patch(
                "crev.sum.sum_repo.collect_structure_context"
            ) as mock_collect_structure,
            patch("crev.sum.sum_repo.collect_repo_context") as mock_collect_repo,
        ):
            mock_git.return_value = (10, "def4567890")

            # Set up LLM mock
            mock_llm_instance = MagicMock()
            mock_llm.return_value = mock_llm_instance

            # Configure responses for LLM calls (4 calls per repo: categorization, structure, app, infra)
            categorization_response = MagicMock()
            categorization_response.content = json.dumps(
                {"app": ["main.py"], "test": [], "infra": []}
            )

            structure_response = MagicMock()
            structure_response.content = "Structure summary"

            app_response = MagicMock()
            app_response.content = "App analysis"

            # Each repo needs these responses
            mock_llm_instance.invoke.side_effect = [
                categorization_response,
                structure_response,
                app_response,
                categorization_response,
                structure_response,
                app_response,
            ]

            # Set up context collector mocks
            mock_collect_file_category.return_value = "file listing context"
            mock_collect_structure.return_value = "structure context"
            mock_collect_repo.return_value = "repo context"

            result = runner.invoke(main, ["sum", "repo"])

            assert result.exit_code == 0
            assert "Summarizing repository: repo1" in result.output
            assert "Summarizing repository: repo2" in result.output


def test_sum_repo_context_only_flag(tmp_path):
    """Test that sum repo --context-only only collects context without LLM calls."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Setup test project in the isolated filesystem
        setup_test_project(Path.cwd())

        # Create repos directory with a git repo
        repos_dir = Path("repos")
        repos_dir.mkdir()
        repo_dir = repos_dir / "test-repo"
        repo_dir.mkdir()
        (repo_dir / "README.md").write_text("# Test Repo")
        (repo_dir / "main.py").write_text("print('hello')")

        # Create pullrequests directory
        Path("pullrequests").mkdir()

        # Mock the git commands and context collector
        with (
            patch("crev.sum.sum_repo._get_git_version_info") as mock_git,
            patch(
                "crev.sum.sum_repo.collect_file_category"
            ) as mock_collect_file_category,
        ):
            mock_git.return_value = (42, "abc1234567")
            mock_collect_file_category.return_value = "file listing context"

            result = runner.invoke(
                main, ["sum", "repo", "test-repo", "--context-only"]
            )

            assert result.exit_code == 0
            assert "Context collection complete" in result.output

            # Check that context file was created
            output_dir = Path("pullrequests") / "test-repo" / "sum"
            context_file = output_dir / "sum_repo.categorization.context.md"
            assert context_file.exists()


def test_sum_repo_caches_intermediate_results(tmp_path):
    """Test that sum repo caches intermediate results and loads from cache."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Setup test project in the isolated filesystem
        setup_test_project(Path.cwd())

        # Create repos directory with a git repo
        repos_dir = Path("repos")
        repos_dir.mkdir()
        repo_dir = repos_dir / "test-repo"
        repo_dir.mkdir()
        (repo_dir / "README.md").write_text("# Test Repo")

        # Create pullrequests directory with cached categorization result
        output_dir = Path("pullrequests") / "test-repo" / "sum"
        output_dir.mkdir(parents=True)

        # Create cached categorization context
        categorization_context = output_dir / "sum_repo.categorization.context.md"
        categorization_context.write_text("# Cached file listing")

        # Create cached categorization result
        categorization_result = output_dir / "sum_repo.categorization.json"
        categorization_result.write_text(
            json.dumps({"app": ["main.py"], "test": [], "infra": []})
        )

        # Mock the git commands and LLM client
        with (
            patch("crev.sum.sum_repo._get_git_version_info") as mock_git,
            patch("crev.sum.sum_repo.get_llm_client") as mock_llm,
            patch(
                "crev.sum.sum_repo.collect_structure_context"
            ) as mock_collect_structure,
            patch("crev.sum.sum_repo.collect_repo_context") as mock_collect_repo,
        ):
            mock_git.return_value = (42, "abc1234567")

            # Set up LLM mock
            mock_llm_instance = MagicMock()
            mock_llm.return_value = mock_llm_instance

            # Only structure and app responses needed (categorization is cached)
            structure_response = MagicMock()
            structure_response.content = "Structure summary"

            app_response = MagicMock()
            app_response.content = "App analysis"

            mock_llm_instance.invoke.side_effect = [
                structure_response,
                app_response,
            ]

            mock_collect_structure.return_value = "structure context"
            mock_collect_repo.return_value = "repo context"

            result = runner.invoke(main, ["sum", "repo", "test-repo"])

            assert result.exit_code == 0
            # Should load cached categorization
            assert "Loading cached result from:" in result.output


def test_sum_repo_repo_not_found(tmp_path):
    """Test that sum repo handles missing repo directory."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        setup_test_project(Path.cwd())

        # Create repos directory but not the specific repo
        repos_dir = Path("repos")
        repos_dir.mkdir()

        # Mock the git commands
        with patch("crev.sum.sum_repo._get_git_version_info") as mock_git:
            mock_git.return_value = (42, "abc1234567")

            result = runner.invoke(main, ["sum", "repo", "test-repo"])

            assert "not found in repos directory" in result.output
