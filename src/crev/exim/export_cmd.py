"""Export command for crev workspace files."""

import shutil
from pathlib import Path

import click


def get_secondary_extension(filename: str) -> str | None:
    """Get the secondary extension of a filename.

    The secondary extension is the second-to-last element when splitting by '.'.
    For example: 'file.ai.md' -> 'ai', 'file.context.md' -> 'context'
    """
    parts = filename.split(".")
    if len(parts) >= 3:
        return parts[-2]
    return None


def should_include_file(file_path: Path, scope: str) -> bool:
    """Determine if a file should be included based on scope.

    Args:
        file_path: Path to the file
        scope: One of 'ai', 'context', or 'all'

    Returns:
        True if file should be included, False otherwise
    """
    if scope == "all":
        return True

    secondary_ext = get_secondary_extension(file_path.name)
    if scope == "ai":
        return secondary_ext == "ai"
    elif scope == "context":
        return secondary_ext == "context"

    return False


def collect_files_to_export(
    scope_folders: list[str],
    scope: str,
    base_dir: Path,
) -> list[Path]:
    """Collect all files that match the export criteria.

    Args:
        scope_folders: List of root-level folders to search in
        scope: File scope filter ('ai', 'context', or 'all')
        base_dir: Base directory to search from

    Returns:
        List of file paths relative to base_dir
    """
    files_to_export = []

    for folder_name in scope_folders:
        folder_path = base_dir / folder_name
        if not folder_path.exists():
            continue

        for file_path in folder_path.rglob("*"):
            if file_path.is_file() and should_include_file(file_path, scope):
                files_to_export.append(file_path.relative_to(base_dir))

    return sorted(files_to_export)


def export_to_folder(
    export_name: str,
    files: list[Path],
    base_dir: Path,
) -> Path:
    """Export files to a folder, retaining directory structure.

    Args:
        export_name: Name of the export folder
        files: List of file paths relative to base_dir
        base_dir: Base directory containing the source files

    Returns:
        Path to the created export folder
    """
    export_dir = base_dir / export_name

    # Remove existing export folder if it exists
    if export_dir.exists():
        shutil.rmtree(export_dir)

    export_dir.mkdir(parents=True, exist_ok=True)

    # Copy configs.json first
    configs_src = base_dir / "configs.json"
    if configs_src.exists():
        shutil.copy2(configs_src, export_dir / "configs.json")

    # Copy each file, preserving directory structure
    for file_path in files:
        src = base_dir / file_path
        dst = export_dir / file_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    return export_dir


def export_to_txtar(
    export_name: str,
    files: list[Path],
    base_dir: Path,
) -> Path:
    """Export files to a txtar format file.

    txtar format:
    -- filename --
    file contents
    -- another_filename --
    more contents

    Args:
        export_name: Name for the txtar file (without extension)
        files: List of file paths relative to base_dir
        base_dir: Base directory containing the source files

    Returns:
        Path to the created txtar file
    """
    txtar_path = base_dir / f"{export_name}.txtar"

    with open(txtar_path, "w", encoding="utf-8") as txtar_file:
        # configs.json must be first
        configs_src = base_dir / "configs.json"
        if configs_src.exists():
            txtar_file.write("-- configs.json --\n")
            txtar_file.write(configs_src.read_text(encoding="utf-8"))
            if not configs_src.read_text(encoding="utf-8").endswith("\n"):
                txtar_file.write("\n")

        # Write each file
        for file_path in files:
            src = base_dir / file_path
            try:
                content = src.read_text(encoding="utf-8")
                txtar_file.write(f"-- {file_path} --\n")
                txtar_file.write(content)
                if not content.endswith("\n"):
                    txtar_file.write("\n")
            except UnicodeDecodeError:
                # Skip binary files
                click.echo(f"Warning: Skipping binary file: {file_path}", err=True)

    return txtar_path


@click.command()
@click.argument("export_name", default="export")
@click.option(
    "--output",
    type=click.Choice(["txtar", "folder"]),
    default="txtar",
    help="Output format: 'txtar' (default) or 'folder'",
)
@click.option(
    "--scope-folders",
    multiple=True,
    default=None,
    help="Root-level folders to export from (default: repos, pullrequests). Can be specified multiple times.",
)
@click.option(
    "--scope",
    type=click.Choice(["ai", "context", "all"]),
    default="ai",
    help="Which files to export: 'ai' (*.ai.*), 'context' (*.context.*), or 'all'",
)
def export(
    export_name: str,
    output: str,
    scope_folders: tuple[str, ...],
    scope: str,
) -> None:
    """Export workspace files to a folder or txtar file.

    EXPORT_NAME is the name for the export (default: 'export').

    Examples:

        crev export                     # Export *.ai.* files as export.txtar

        crev export myexport            # Export as myexport.txtar

        crev export --output folder     # Export to 'export' folder

        crev export --scope all         # Export all files in scope folders

        crev export --scope-folders repos  # Only export from repos folder
    """
    base_dir = Path.cwd()

    # Check for configs.json
    configs_file = base_dir / "configs.json"
    if not configs_file.exists():
        click.echo("Error: configs.json not found. Run 'crev init' first.", err=True)
        raise SystemExit(1)

    # Default scope folders
    if not scope_folders:
        scope_folders = ("repos", "pullrequests")

    # Collect files to export
    files = collect_files_to_export(list(scope_folders), scope, base_dir)

    if not files:
        click.echo(f"No files found matching scope '{scope}' in folders: {', '.join(scope_folders)}")
        return

    click.echo(f"Found {len(files)} file(s) to export")

    # Export based on output format
    if output == "folder":
        result_path = export_to_folder(export_name, files, base_dir)
        click.echo(f"Exported to folder: {result_path}")
    else:  # txtar
        result_path = export_to_txtar(export_name, files, base_dir)
        click.echo(f"Exported to: {result_path}")
