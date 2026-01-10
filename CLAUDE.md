# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**basicreviewer** (package name: `crev`) is an open-source code review, performance review, and CV tool designed to help software engineers market themselves and improve their skills.

The project is in its initial setup phase, currently containing a basic CLI skeleton.

## Development Setup

This project uses **uv** (modern Python package manager) for all dependency management and builds.

### Install for Development
```bash
uv tool install . -e
```

### Uninstall
```bash
uv tool remove crev
```

### Run the CLI
After installation:
```bash
crev                    # Show help
crev init <path>        # Initialize a new project
```

### Run Tests
```bash
uv run --with pytest pytest tests/init/base.py -v  # Run init command tests
```

## Project Structure

```
src/crev/               # Main package source
  __init__.py           # CLI entrypoint with click group
  init/                 # Init command module
    __init__.py         # Init command implementation
    assets/             # Template files for init command
      repos_template.json   # Template for repos.json
      init_success.txt      # Success message template
tests/                  # Test suite
  init/                 # Init command tests
    base.py             # Base test cases for init command
pyproject.toml          # Project configuration and dependencies
```

## Build System

- **Build backend**: `uv_build` (version 0.9.24-0.10.0)
- **Python version**: >=3.12
- **Entry point**: `crev:main` registered as `crev` command

## Key Technical Details

1. **CLI Framework**: Uses `click` for building the CLI with subcommands
   - Main entry point: `src/crev/__init__.py:main()` is a click group
   - Subcommands are registered using `main.add_command()`

2. **Init Command**: Creates a new project directory with a `repos.json` configuration file
   - Template files are stored in `src/crev/init/assets/`
   - Uses `repos_template.json` for the default repository configuration
   - The repos.json format includes repos with pull_requests fields for use with future `crev pull` command

3. **Testing**: Uses pytest for testing
   - Tests use click's `CliRunner` for testing CLI commands
   - Run tests with: `uv run --with pytest pytest tests/ -v`

4. **Dependencies**:
   - Runtime: `click>=8.1.0`
   - Dev: `pytest>=8.0.0`

5. Project setup reference: https://mathspp.com/blog/using-uv-to-build-and-install-python-cli-apps
