"""PR context collector for summarization."""

from pathlib import Path

import click


def pr(pr_dir: Path) -> str:
    """Collect context about a PR for summarization.

    Args:
        pr_dir: Path to the PR directory

    Returns:
        String containing PR context (diff, changed files, etc.)
    """
    context_parts = []

    # Add main heading
    context_parts.append("# Attachments\n")

    # Read diff file
    diff_file = pr_dir / "sum" / "diff.txt"
    if diff_file.exists():
        context_parts.append("## Git Diff\n")
        context_parts.append("```diff")
        context_parts.append(diff_file.read_text())
        context_parts.append("```\n")
    else:
        click.echo(f"  Warning: diff.txt not found in {pr_dir}", err=True)

    # Get changed files and their contents
    code_dir = pr_dir / "code"
    if code_dir.exists():
        context_parts.append("## File Changes\n")

        initial_dir = code_dir / "initial"
        final_dir = code_dir / "final"

        # Get files from both initial and final
        all_files = set()
        if initial_dir.exists():
            all_files.update(
                [
                    str(f.relative_to(initial_dir))
                    for f in initial_dir.rglob("*")
                    if f.is_file()
                ]
            )
        if final_dir.exists():
            all_files.update(
                [
                    str(f.relative_to(final_dir))
                    for f in final_dir.rglob("*")
                    if f.is_file()
                ]
            )

        # Process each changed file
        for file_path in sorted(all_files):
            context_parts.append(f"### {file_path}\n")

            # Add initial version if it exists
            initial_file = initial_dir / file_path
            if initial_file.exists():
                context_parts.append("#### Initial\n")
                context_parts.append("```")
                try:
                    context_parts.append(initial_file.read_text())
                except Exception as e:
                    context_parts.append(f"[Error reading file: {e}]")
                context_parts.append("```\n")
            else:
                context_parts.append("#### Initial\n")
                context_parts.append("*File did not exist (newly added)*\n")

            # Add final version if it exists
            final_file = final_dir / file_path
            if final_file.exists():
                context_parts.append("#### Final\n")
                context_parts.append("```")
                try:
                    context_parts.append(final_file.read_text())
                except Exception as e:
                    context_parts.append(f"[Error reading file: {e}]")
                context_parts.append("```\n")
            else:
                context_parts.append("#### Final\n")
                context_parts.append("*File was deleted*\n")

    return "\n".join(context_parts)
