"""Repository context collector for summarization."""

from pathlib import Path
from typing import Optional


def _get_file_extension(file_path: str) -> str:
    """Get the file extension for syntax highlighting."""
    ext = Path(file_path).suffix.lstrip(".")
    extension_map = {
        "py": "python",
        "js": "javascript",
        "ts": "typescript",
        "tsx": "tsx",
        "jsx": "jsx",
        "rb": "ruby",
        "rs": "rust",
        "go": "go",
        "java": "java",
        "kt": "kotlin",
        "swift": "swift",
        "cs": "csharp",
        "cpp": "cpp",
        "c": "c",
        "h": "c",
        "hpp": "cpp",
        "json": "json",
        "yaml": "yaml",
        "yml": "yaml",
        "toml": "toml",
        "md": "markdown",
        "sh": "bash",
        "bash": "bash",
        "zsh": "bash",
        "sql": "sql",
        "html": "html",
        "css": "css",
        "scss": "scss",
        "xml": "xml",
    }
    return extension_map.get(ext, ext or "")


def repo(
    repo_path: Path,
    file_paths: list[str],
    category: Optional[str] = None,
) -> str:
    """Collect context for a set of repository files.

    Builds a markdown-formatted context containing file contents
    following the standard context format.

    Args:
        repo_path: Path to the repository root
        file_paths: List of relative file paths to include
        category: Optional category label (e.g., 'app', 'test', 'infra')

    Returns:
        Markdown-formatted string with file contents
    """
    context_parts = []

    # Add heading
    if category:
        context_parts.append(f"# {category.title()} Files\n")
    else:
        context_parts.append("# Repository Files\n")

    # Process each file
    for rel_path in sorted(file_paths):
        file_path = repo_path / rel_path
        context_parts.append(f"## {rel_path}\n")

        if file_path.exists():
            ext = _get_file_extension(rel_path)
            context_parts.append(f"```{ext}")
            try:
                content = file_path.read_text()
                # Truncate very large files
                max_lines = 500
                lines = content.splitlines()
                if len(lines) > max_lines:
                    content = "\n".join(lines[:max_lines])
                    content += (
                        f"\n\n... [truncated, {len(lines) - max_lines} more lines]"
                    )
                context_parts.append(content)
            except Exception as e:
                context_parts.append(f"[Error reading file: {e}]")
            context_parts.append("```\n")
        else:
            context_parts.append("*File not found*\n")

    context_parts.append(f"\nTotal files: {len(file_paths)}")

    return "\n".join(context_parts)


def structure(file_categories: dict[str, list[str]]) -> str:
    """Build context for repository structure summarization.

    Args:
        file_categories: Dictionary mapping categories to file lists
            e.g., {'app': ['src/main.py'], 'test': ['tests/test_main.py'], 'infra': ['Dockerfile']}

    Returns:
        Markdown-formatted string describing the file organization
    """
    context_parts = []
    context_parts.append("# Repository File Organization\n")

    total_files = 0

    for category in ["app", "test", "infra"]:
        files = file_categories.get(category, [])
        total_files += len(files)

        context_parts.append(f"## {category.title()} Files ({len(files)} files)\n")

        if files:
            # Group by directory
            dirs: dict[str, list[str]] = {}
            for f in sorted(files):
                dir_path = str(Path(f).parent)
                if dir_path == ".":
                    dir_path = "(root)"
                if dir_path not in dirs:
                    dirs[dir_path] = []
                dirs[dir_path].append(Path(f).name)

            for dir_path in sorted(dirs.keys()):
                context_parts.append(f"### {dir_path}/")
                for filename in sorted(dirs[dir_path]):
                    context_parts.append(f"- {filename}")
                context_parts.append("")
        else:
            context_parts.append("*No files in this category*\n")

    context_parts.append(f"\n**Total files:** {total_files}")

    return "\n".join(context_parts)
