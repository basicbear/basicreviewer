"""Edge case tests for the pull command."""

import json
from unittest.mock import patch

from click.testing import CliRunner

from crev import main


def test_pull_handles_empty_repos_list(tmp_path):
    """Test that pull handles an empty repos list."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create configs.json with empty repos list
        repos_data = {"repos": []}
        with open("configs.json", "w") as f:
            json.dump(repos_data, f)

        with patch("subprocess.run"):
            result = runner.invoke(main, ["pull"])

        assert result.exit_code == 0
        assert "Done." in result.output


def test_pull_handles_missing_repos_key(tmp_path):
    """Test that pull handles configs.json without a 'repos' key."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create configs.json without repos key
        repos_data = {}
        with open("configs.json", "w") as f:
            json.dump(repos_data, f)

        with patch("subprocess.run"):
            result = runner.invoke(main, ["pull"])

        assert result.exit_code == 0
        assert "Done." in result.output
