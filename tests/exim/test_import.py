"""Tests for the import command."""

import copy
import json
from pathlib import Path

from click.testing import CliRunner

from crev import main

TEST_CONFIGS_PATH = Path(__file__).parent / "test.configs.json"


def load_test_configs() -> dict:
    """Load the shared test configs."""
    return json.loads(TEST_CONFIGS_PATH.read_text())


def create_empty_workspace(base_path: Path) -> Path:
    """Create an empty workspace with just configs.json."""
    configs = copy.deepcopy(load_test_configs())
    configs["repos"] = []
    configs_file = base_path / "configs.json"
    configs_file.write_text(json.dumps(configs, indent=2))
    return base_path


def create_txtar_file(path: Path, files: dict[str, str]) -> Path:
    """Create a txtar file with the given files."""
    content = ""
    for filename, file_content in files.items():
        content += f"-- {filename} --\n{file_content}\n"
    path.write_text(content)
    return path


def create_import_folder(base_path: Path) -> Path:
    """Create a folder with repos and pullrequests structure for import."""
    # Create repos structure
    repos_dir = base_path / "repos" / "importorg" / "importrepo"
    repos_dir.mkdir(parents=True)
    (repos_dir / "summary.ai.md").write_text("# Imported Summary")

    # Create pullrequests structure
    pr_dir = base_path / "pullrequests" / "importorg" / "importrepo" / "456" / "sum"
    pr_dir.mkdir(parents=True)
    (pr_dir / "summary.ai.md").write_text("# Imported PR Summary")

    return base_path


def test_import_requires_configs_json(tmp_path):
    """Test that import fails without configs.json."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create a dummy txtar file
        Path("test.txtar").write_text("-- file.txt --\ncontent\n")

        result = runner.invoke(main, ["import", "test.txtar"])

        assert result.exit_code == 1
        assert "configs.json not found" in result.output


def test_import_requires_txtar_extension(tmp_path):
    """Test that import requires .txtar extension for files."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        create_empty_workspace(Path.cwd())
        Path("test.txt").write_text("content")

        result = runner.invoke(main, ["import", "test.txt"])

        assert result.exit_code == 1
        assert "must be a .txtar file" in result.output


def test_import_from_txtar(tmp_path):
    """Test basic import from txtar file."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        create_empty_workspace(Path.cwd())

        # Create txtar with files to import
        txtar_content = {
            "configs.json": '{"repos": []}',
            "repos/neworg/newrepo/summary.ai.md": "# New Summary",
            "pullrequests/neworg/newrepo/789/sum/pr.ai.md": "# PR Content",
        }
        create_txtar_file(Path("import.txtar"), txtar_content)

        result = runner.invoke(main, ["import", "import.txtar"])

        assert result.exit_code == 0
        assert "Imported 2 file(s)" in result.output

        # Verify files were created
        assert Path("repos/neworg/newrepo/summary.ai.md").exists()
        assert Path("pullrequests/neworg/newrepo/789/sum/pr.ai.md").exists()


def test_import_from_folder(tmp_path):
    """Test basic import from folder."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        create_empty_workspace(Path.cwd())

        # Create import folder
        import_dir = Path("import_folder")
        import_dir.mkdir()
        create_import_folder(import_dir)

        result = runner.invoke(main, ["import", "import_folder"])

        assert result.exit_code == 0
        assert "Imported 2 file(s)" in result.output

        # Verify files were created
        assert Path("repos/importorg/importrepo/summary.ai.md").exists()
        assert Path("pullrequests/importorg/importrepo/456/sum/summary.ai.md").exists()


def test_import_folder_requires_structure(tmp_path):
    """Test that folder import requires repos or pullrequests subdirectories."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        create_empty_workspace(Path.cwd())

        # Create folder without proper structure
        import_dir = Path("bad_folder")
        import_dir.mkdir()
        (import_dir / "file.txt").write_text("content")

        result = runner.invoke(main, ["import", "bad_folder"])

        assert result.exit_code == 1
        assert "must contain 'repos' and/or 'pullrequests'" in result.output


def test_import_skips_configs_json(tmp_path):
    """Test that import does not overwrite workspace configs.json."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        create_empty_workspace(Path.cwd())
        original_config = Path("configs.json").read_text()

        # Create txtar with different configs.json
        txtar_content = {
            "configs.json": '{"repos": [{"name": "imported"}]}',
            "repos/org/repo/file.ai.md": "content",
        }
        create_txtar_file(Path("import.txtar"), txtar_content)

        result = runner.invoke(main, ["import", "import.txtar"])

        assert result.exit_code == 0
        # configs.json should be unchanged
        assert Path("configs.json").read_text() == original_config


def test_import_detects_repo_collision(tmp_path):
    """Test that import detects and skips colliding repos."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        create_empty_workspace(Path.cwd())

        # Create existing repo
        existing_repo = Path("repos/existingorg/existingrepo")
        existing_repo.mkdir(parents=True)
        (existing_repo / "existing.ai.md").write_text("# Existing")

        # Try to import same org/repo
        txtar_content = {
            "configs.json": "{}",
            "repos/existingorg/existingrepo/new.ai.md": "# New",
        }
        create_txtar_file(Path("import.txtar"), txtar_content)

        result = runner.invoke(main, ["import", "import.txtar"])

        assert result.exit_code == 0
        assert "Imported 0 file(s)" in result.output
        assert "Skipped due to collisions:" in result.output
        assert "repos/existingorg/existingrepo (repo already exists)" in result.output

        # Original file should still exist, new file should not
        assert (existing_repo / "existing.ai.md").exists()
        assert not (existing_repo / "new.ai.md").exists()


def test_import_detects_pr_collision(tmp_path):
    """Test that import detects and skips colliding PRs."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        create_empty_workspace(Path.cwd())

        # Create existing PR
        existing_pr = Path("pullrequests/org/repo/123/sum")
        existing_pr.mkdir(parents=True)
        (existing_pr / "existing.ai.md").write_text("# Existing PR")

        # Try to import same org/repo/pr
        txtar_content = {
            "configs.json": "{}",
            "pullrequests/org/repo/123/sum/new.ai.md": "# New PR",
        }
        create_txtar_file(Path("import.txtar"), txtar_content)

        result = runner.invoke(main, ["import", "import.txtar"])

        assert result.exit_code == 0
        assert "Imported 0 file(s)" in result.output
        assert "Skipped due to collisions:" in result.output
        assert "pullrequests/org/repo/123 (PR already exists)" in result.output


def test_import_allows_different_pr_numbers(tmp_path):
    """Test that import allows PRs with different numbers for same repo."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        create_empty_workspace(Path.cwd())

        # Create existing PR 123
        existing_pr = Path("pullrequests/org/repo/123/sum")
        existing_pr.mkdir(parents=True)
        (existing_pr / "existing.ai.md").write_text("# PR 123")

        # Import PR 456 for same repo
        txtar_content = {
            "configs.json": "{}",
            "pullrequests/org/repo/456/sum/new.ai.md": "# PR 456",
        }
        create_txtar_file(Path("import.txtar"), txtar_content)

        result = runner.invoke(main, ["import", "import.txtar"])

        assert result.exit_code == 0
        assert "Imported 1 file(s)" in result.output
        assert "Skipped" not in result.output

        # Both PRs should exist
        assert (existing_pr / "existing.ai.md").exists()
        assert Path("pullrequests/org/repo/456/sum/new.ai.md").exists()


def test_import_allows_different_repos(tmp_path):
    """Test that import allows repos with different org or name."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        create_empty_workspace(Path.cwd())

        # Create existing repo
        existing_repo = Path("repos/org1/repo1")
        existing_repo.mkdir(parents=True)
        (existing_repo / "file.ai.md").write_text("# Org1/Repo1")

        # Import different org/repo combinations
        txtar_content = {
            "configs.json": "{}",
            "repos/org1/repo2/file.ai.md": "# Org1/Repo2",
            "repos/org2/repo1/file.ai.md": "# Org2/Repo1",
        }
        create_txtar_file(Path("import.txtar"), txtar_content)

        result = runner.invoke(main, ["import", "import.txtar"])

        assert result.exit_code == 0
        assert "Imported 2 file(s)" in result.output

        # All repos should exist
        assert Path("repos/org1/repo1/file.ai.md").exists()
        assert Path("repos/org1/repo2/file.ai.md").exists()
        assert Path("repos/org2/repo1/file.ai.md").exists()


def test_import_partial_collision(tmp_path):
    """Test import with some collisions and some successful imports."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        create_empty_workspace(Path.cwd())

        # Create existing repo
        existing_repo = Path("repos/existing/repo")
        existing_repo.mkdir(parents=True)
        (existing_repo / "file.ai.md").write_text("# Existing")

        # Import mix of colliding and new files
        txtar_content = {
            "configs.json": "{}",
            "repos/existing/repo/collision.ai.md": "# Should be skipped",
            "repos/neworg/newrepo/new.ai.md": "# Should be imported",
        }
        create_txtar_file(Path("import.txtar"), txtar_content)

        result = runner.invoke(main, ["import", "import.txtar"])

        assert result.exit_code == 0
        assert "Imported 1 file(s)" in result.output
        assert "Skipped due to collisions:" in result.output

        # New file should exist, collision should not
        assert Path("repos/neworg/newrepo/new.ai.md").exists()
        assert not Path("repos/existing/repo/collision.ai.md").exists()


def test_import_from_folder_collision(tmp_path):
    """Test folder import with collision detection."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        create_empty_workspace(Path.cwd())

        # Create existing repo
        existing_repo = Path("repos/importorg/importrepo")
        existing_repo.mkdir(parents=True)
        (existing_repo / "existing.ai.md").write_text("# Existing")

        # Create import folder with same org/repo
        import_dir = Path("import_folder")
        import_dir.mkdir()
        create_import_folder(import_dir)

        result = runner.invoke(main, ["import", "import_folder"])

        assert result.exit_code == 0
        assert "Skipped due to collisions:" in result.output
        assert "repos/importorg/importrepo (repo already exists)" in result.output


def test_import_creates_nested_directories(tmp_path):
    """Test that import creates necessary parent directories."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        create_empty_workspace(Path.cwd())

        txtar_content = {
            "configs.json": "{}",
            "repos/deep/nested/path/file.ai.md": "# Deep file",
            "pullrequests/org/repo/999/sum/nested/file.ai.md": "# Nested PR",
        }
        create_txtar_file(Path("import.txtar"), txtar_content)

        result = runner.invoke(main, ["import", "import.txtar"])

        assert result.exit_code == 0
        assert "Imported 2 file(s)" in result.output

        assert Path("repos/deep/nested/path/file.ai.md").exists()
        assert Path("pullrequests/org/repo/999/sum/nested/file.ai.md").exists()


def test_import_preserves_file_content(tmp_path):
    """Test that import preserves file content correctly."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        create_empty_workspace(Path.cwd())

        expected_content = "# Test Content\n\nWith multiple lines\nAnd special chars: @#$%"
        txtar_content = {
            "configs.json": "{}",
            "repos/org/repo/file.ai.md": expected_content,
        }
        create_txtar_file(Path("import.txtar"), txtar_content)

        result = runner.invoke(main, ["import", "import.txtar"])

        assert result.exit_code == 0

        actual_content = Path("repos/org/repo/file.ai.md").read_text()
        assert actual_content == expected_content


def test_import_reports_collision_once_per_entity(tmp_path):
    """Test that collision is reported once per repo/PR, not per file."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        create_empty_workspace(Path.cwd())

        # Create existing repo
        existing_repo = Path("repos/org/repo")
        existing_repo.mkdir(parents=True)
        (existing_repo / "existing.ai.md").write_text("# Existing")

        # Import multiple files for same colliding repo
        txtar_content = {
            "configs.json": "{}",
            "repos/org/repo/file1.ai.md": "# File 1",
            "repos/org/repo/file2.ai.md": "# File 2",
            "repos/org/repo/subdir/file3.ai.md": "# File 3",
        }
        create_txtar_file(Path("import.txtar"), txtar_content)

        result = runner.invoke(main, ["import", "import.txtar"])

        assert result.exit_code == 0
        # Should only report the collision once
        assert result.output.count("repos/org/repo (repo already exists)") == 1


def test_import_nonexistent_path(tmp_path):
    """Test import with nonexistent path."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        create_empty_workspace(Path.cwd())

        result = runner.invoke(main, ["import", "nonexistent.txtar"])

        assert result.exit_code != 0
