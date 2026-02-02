"""Tests for the init command."""

import filecmp
from pathlib import Path

from click.testing import CliRunner

from crev import main

TEMPLATE_DIR = (
    Path(__file__).parent.parent.parent / "src" / "crev" / "init" / "template"
)


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


def test_init_output_contains_next_steps(tmp_path):
    """Test that init output provides guidance on next steps."""
    runner = CliRunner()
    project_path = tmp_path / "test-project"

    result = runner.invoke(main, ["init", str(project_path)])

    assert result.exit_code == 0
    assert "Next steps:" in result.output
    assert "configs.json" in result.output
    assert "crev pull" in result.output


def test_init_matches_template_exactly(tmp_path):
    """Test that init creates content matching the template directory exactly."""
    runner = CliRunner()
    project_path = tmp_path / "test-project"

    result = runner.invoke(main, ["init", str(project_path)])

    assert result.exit_code == 0

    # Get all files from template directory
    template_files = set()
    for file_path in TEMPLATE_DIR.rglob("*"):
        if file_path.is_file():
            template_files.add(file_path.relative_to(TEMPLATE_DIR))

    # Get all files from created directory
    created_files = set()
    for file_path in project_path.rglob("*"):
        if file_path.is_file():
            created_files.add(file_path.relative_to(project_path))

    # Check that file sets match
    assert template_files == created_files, (
        f"File mismatch.\n"
        f"Missing files: {template_files - created_files}\n"
        f"Extra files: {created_files - template_files}"
    )

    # Check that file contents match exactly
    for rel_path in template_files:
        template_file = TEMPLATE_DIR / rel_path
        created_file = project_path / rel_path

        assert filecmp.cmp(template_file, created_file, shallow=False), (
            f"Content mismatch in {rel_path}"
        )
