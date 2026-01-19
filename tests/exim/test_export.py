"""Tests for the export command."""

import copy
import json
from pathlib import Path

from click.testing import CliRunner

from crev import main

TEST_CONFIGS_PATH = Path(__file__).parent / "test.configs.json"


def load_test_configs() -> dict:
    """Load the shared test configs."""
    return json.loads(TEST_CONFIGS_PATH.read_text())


def create_test_workspace(base_path: Path) -> Path:
    """Create a test workspace with configs.json and sample files."""
    # Create configs.json
    configs = load_test_configs()
    configs_file = base_path / "configs.json"
    configs_file.write_text(json.dumps(configs, indent=2))

    # Create sample files in repos folder
    repos_dir = base_path / "repos" / "testorg" / "testrepo"
    repos_dir.mkdir(parents=True)
    (repos_dir / "README.md").write_text("# Test Repo")
    (repos_dir / "summary.ai.md").write_text("# AI Summary")
    (repos_dir / "data.context.md").write_text("# Context Data")

    # Create sample files in pullrequests folder
    pr_dir = base_path / "pullrequests" / "testorg" / "testrepo" / "123" / "sum"
    pr_dir.mkdir(parents=True)
    (pr_dir / "summary.ai.md").write_text("# PR Summary")
    (pr_dir / "context.context.md").write_text("# PR Context")
    (pr_dir / "diff.txt").write_text("diff content")

    return base_path


def test_export_requires_configs_json(tmp_path):
    """Test that export fails without configs.json."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(main, ["export"])

        assert result.exit_code == 1
        assert "configs.json not found" in result.output


def test_export_default_txtar_ai_scope(tmp_path):
    """Test default export creates txtar with ai scope."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        create_test_workspace(Path.cwd())

        result = runner.invoke(main, ["export"])

        assert result.exit_code == 0
        assert "Found 2 file(s) to export" in result.output
        assert "Exported to:" in result.output

        txtar_file = Path("export.txtar")
        assert txtar_file.exists()

        content = txtar_file.read_text()
        # configs.json should be first
        assert content.startswith("-- configs.json --")
        # Should contain ai files
        assert "summary.ai.md" in content
        # Should NOT contain context or other files
        assert "context.context.md" not in content
        assert "README.md" not in content


def test_export_custom_name(tmp_path):
    """Test export with custom name."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        create_test_workspace(Path.cwd())

        result = runner.invoke(main, ["export", "mybackup"])

        assert result.exit_code == 0
        assert Path("mybackup.txtar").exists()
        assert not Path("export.txtar").exists()


def test_export_folder_output(tmp_path):
    """Test export to folder format."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        create_test_workspace(Path.cwd())

        result = runner.invoke(main, ["export", "--output", "folder"])

        assert result.exit_code == 0
        assert "Exported to folder:" in result.output

        export_dir = Path("export")
        assert export_dir.exists()
        assert export_dir.is_dir()
        assert (export_dir / "configs.json").exists()
        assert (export_dir / "repos" / "testorg" / "testrepo" / "summary.ai.md").exists()
        assert (export_dir / "pullrequests" / "testorg" / "testrepo" / "123" / "sum" / "summary.ai.md").exists()


def test_export_scope_context(tmp_path):
    """Test export with context scope."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        create_test_workspace(Path.cwd())

        result = runner.invoke(main, ["export", "--scope", "context"])

        assert result.exit_code == 0
        assert "Found 2 file(s) to export" in result.output

        content = Path("export.txtar").read_text()
        assert "context.context.md" in content
        assert "summary.ai.md" not in content


def test_export_scope_all(tmp_path):
    """Test export with all scope."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        create_test_workspace(Path.cwd())

        result = runner.invoke(main, ["export", "--scope", "all"])

        assert result.exit_code == 0
        assert "Found 6 file(s) to export" in result.output

        content = Path("export.txtar").read_text()
        assert "summary.ai.md" in content
        assert "context.context.md" in content
        assert "README.md" in content
        assert "diff.txt" in content


def test_export_scope_folders_repos_only(tmp_path):
    """Test export with scope-folders limited to repos."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        create_test_workspace(Path.cwd())

        result = runner.invoke(main, ["export", "--scope", "all", "--scope-folders", "repos"])

        assert result.exit_code == 0
        assert "Found 3 file(s) to export" in result.output

        content = Path("export.txtar").read_text()
        assert "repos/testorg/testrepo" in content
        assert "pullrequests" not in content


def test_export_scope_folders_pullrequests_only(tmp_path):
    """Test export with scope-folders limited to pullrequests."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        create_test_workspace(Path.cwd())

        result = runner.invoke(main, ["export", "--scope", "all", "--scope-folders", "pullrequests"])

        assert result.exit_code == 0
        assert "Found 3 file(s) to export" in result.output

        content = Path("export.txtar").read_text()
        assert "pullrequests/testorg/testrepo" in content
        assert "repos/testorg" not in content


def test_export_no_matching_files(tmp_path):
    """Test export when no files match the scope."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create workspace without any ai files
        configs = copy.deepcopy(load_test_configs())
        configs["repos"] = []
        Path("configs.json").write_text(json.dumps(configs))
        repos_dir = Path("repos/org/repo")
        repos_dir.mkdir(parents=True)
        (repos_dir / "README.md").write_text("# Test")

        result = runner.invoke(main, ["export", "--scope", "ai"])

        assert result.exit_code == 0
        assert "No files found matching scope" in result.output


def test_export_txtar_format_structure(tmp_path):
    """Test that txtar format is correct."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        create_test_workspace(Path.cwd())

        result = runner.invoke(main, ["export", "--scope", "ai"])

        assert result.exit_code == 0

        content = Path("export.txtar").read_text()
        lines = content.split("\n")

        # First line should be configs.json header
        assert lines[0] == "-- configs.json --"

        # Check that file headers follow the pattern
        headers = [line for line in lines if line.startswith("-- ") and line.endswith(" --")]
        assert len(headers) >= 2  # configs.json + at least one ai file


def test_export_folder_preserves_structure(tmp_path):
    """Test that folder export preserves directory structure."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        create_test_workspace(Path.cwd())

        result = runner.invoke(main, ["export", "--output", "folder", "--scope", "all"])

        assert result.exit_code == 0

        export_dir = Path("export")

        # Check full path structure is preserved
        assert (export_dir / "repos" / "testorg" / "testrepo" / "README.md").exists()
        assert (export_dir / "repos" / "testorg" / "testrepo" / "summary.ai.md").exists()
        assert (export_dir / "pullrequests" / "testorg" / "testrepo" / "123" / "sum" / "diff.txt").exists()


def test_export_overwrites_existing_folder(tmp_path):
    """Test that folder export overwrites existing export folder."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        create_test_workspace(Path.cwd())

        # Create an existing export folder with a file
        export_dir = Path("export")
        export_dir.mkdir()
        (export_dir / "old_file.txt").write_text("old content")

        result = runner.invoke(main, ["export", "--output", "folder"])

        assert result.exit_code == 0
        assert not (export_dir / "old_file.txt").exists()
        assert (export_dir / "configs.json").exists()


def test_export_multiple_scope_folders(tmp_path):
    """Test export with multiple scope-folders specified."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        create_test_workspace(Path.cwd())

        result = runner.invoke(
            main, ["export", "--scope", "all", "--scope-folders", "repos", "--scope-folders", "pullrequests"]
        )

        assert result.exit_code == 0
        assert "Found 6 file(s) to export" in result.output
