"""Tests for the sum command (general tests)."""

from click.testing import CliRunner

from crev import main


def test_sum_command_exists():
    """Test that the sum command is registered."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "sum" in result.output


def test_sum_command_shows_help():
    """Test that the sum command shows help text."""
    runner = CliRunner()
    result = runner.invoke(main, ["sum", "--help"])

    assert result.exit_code == 0
    assert "Summarize repositories and pull requests" in result.output


def test_sum_command_lists_subcommands():
    """Test that the sum command lists its subcommands."""
    runner = CliRunner()
    result = runner.invoke(main, ["sum", "--help"])

    assert result.exit_code == 0
    # Check that both subcommands are listed
    assert "repo" in result.output
    assert "pr" in result.output
