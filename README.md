# basicreviewer

## Description

Open source code review, performance review, and CV tool. Designed to help software engineers market themselves and improve their skills.

## Installation/Removal

### Pre-Requisites
- git CLI
- Python >=3.12
- [uv](https://docs.astral.sh/uv/) (Python package manager)

### Install
```bash
uv tool install . -e
```

### Uninstall
```bash
uv tool remove crev
```

## Usage

```
crev [OPTIONS] COMMAND [ARGS]...
```

### Commands

#### `crev init <path>`
Initialize a new crev project. Creates a folder at PATH with a `configs.json` configuration file and a sample `.env` file.

After initialization, add your LLM API key to the `.env` file. Only Claude is supported at the moment:
```
ANTHROPIC_API_KEY=your_api_key_here
```

#### `crev pull`
Pull all repos defined in `configs.json` into a repos folder.

#### `crev extract`
Extract PR files and diffs from pulled repositories.

#### `crev sum [--context-only]`
Summarize repositories and pull requests. If no subcommand is given, runs both `repo` and `pr` subcommands for all orgs/repos/prs.

Use `--context-only` to collect context without generating summaries.

**Subcommands:**

- `crev sum repo [ORG] [REPO_NAME]` - Summarize repository business purpose, tech stack, and architecture.
  - Use `.` as a wildcard (e.g., `crev sum repo . myrepo` for myrepo in all orgs)
  - Skips repositories that already have summary files

- `crev sum pr [ORG] [REPO_NAME] [PR_NUMBER]` - Summarize pull request business purpose and architecture.
  - Use `.` as a wildcard (e.g., `crev sum pr myorg . .` for all PRs in myorg)
  - Skips PRs that already have summary files

#### `crev export [EXPORT_NAME]`
Export workspace files to a folder or txtar file.

| Option | Description |
|--------|-------------|
| `--output [txtar\|folder]` | Output format (default: txtar) |
| `--scope-folders TEXT` | Root-level folders to export from (default: repos, pullrequests) |
| `--scope [ai\|context\|all]` | Which files to export: `ai` (*.ai.*), `context` (*.context.*), or `all` |

#### `crev import <input_path>`
Import workspace files from a txtar file or folder. INPUT_PATH must be either a `.txtar` file created by `crev export` or a folder containing `repos` and/or `pullrequests` subdirectories.

Files are merged into the current workspace. Collisions (matching org/repo or org/repo/pr_number) are skipped.

#### `crev mcp-serv`
Start the MCP (Model Context Protocol) server to expose crev data through standardized endpoints.

**Endpoints:**
- Summary: `sum_repo`, `sum_pr`, `sum_list`
- CV: `stack`, `accomplishments`, `org_list`

