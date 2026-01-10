"""Tests for the init command."""

import json
from pathlib import Path

from click.testing import CliRunner

from crev import main


def test_init_creates_directory(tmp_path):
    """Test that init creates a new directory."""
    runner = CliRunner()
    project_name = "test-project"
    project_path = tmp_path / project_name

    result = runner.invoke(main, ["init", str(project_path)])

    assert result.exit_code == 0
    assert project_path.exists()
    assert project_path.is_dir()
    assert "Created directory:" in result.output
    assert "Project initialized successfully!" in result.output


def test_init_creates_repos_json(tmp_path):
    """Test that init creates a repos.json file with correct structure."""
    runner = CliRunner()
    project_name = "test-project"
    project_path = tmp_path / project_name

    result = runner.invoke(main, ["init", str(project_path)])

    assert result.exit_code == 0

    repos_file = project_path / "repos.json"
    assert repos_file.exists()

    # Verify JSON structure
    with repos_file.open("r") as f:
        repos_data = json.load(f)

    assert "repos" in repos_data
    assert isinstance(repos_data["repos"], list)
    assert len(repos_data["repos"]) > 0

    # Check first repo structure
    first_repo = repos_data["repos"][0]
    assert "name" in first_repo
    assert "url" in first_repo
    assert "pull_requests" in first_repo
    assert isinstance(first_repo["pull_requests"], list)

    # Check pull request structure
    assert len(first_repo["pull_requests"]) == 2
    assert "url" in first_repo["pull_requests"][0]
    assert "url" in first_repo["pull_requests"][1]


def test_init_fails_on_existing_directory(tmp_path):
    """Test that init fails when directory already exists."""
    runner = CliRunner()
    project_name = "existing-project"
    project_path = tmp_path / project_name

    # Create the directory first
    project_path.mkdir()

    result = runner.invoke(main, ["init", str(project_path)])

    assert result.exit_code != 0
    assert "already exists" in result.output


def test_init_creates_nested_directories(tmp_path):
    """Test that init can create nested directories."""
    runner = CliRunner()
    nested_path = tmp_path / "parent" / "child" / "project"

    result = runner.invoke(main, ["init", str(nested_path)])

    assert result.exit_code == 0
    assert nested_path.exists()
    assert (nested_path / "repos.json").exists()


def test_init_output_contains_next_steps(tmp_path):
    """Test that init output provides guidance on next steps."""
    runner = CliRunner()
    project_path = tmp_path / "test-project"

    result = runner.invoke(main, ["init", str(project_path)])

    assert result.exit_code == 0
    assert "Next steps:" in result.output
    assert "repos.json" in result.output
    assert "crev pull" in result.output
