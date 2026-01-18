"""Import command for crev workspace files."""

import json
import re
import shutil
from pathlib import Path

import click


def parse_txtar(txtar_path: Path) -> dict[str, str]:
    """Parse a txtar file into a dictionary of filename -> content.

    txtar format:
    -- filename --
    file contents
    -- another_filename --
    more contents

    Args:
        txtar_path: Path to the txtar file

    Returns:
        Dictionary mapping file paths to their contents
    """
    content = txtar_path.read_text(encoding="utf-8")
    files: dict[str, str] = {}

    # Pattern to match file headers: -- path/to/file --
    header_pattern = re.compile(r"^-- (.+) --$", re.MULTILINE)

    matches = list(header_pattern.finditer(content))

    for i, match in enumerate(matches):
        filename = match.group(1).strip()
        start = match.end() + 1  # Skip the newline after header

        # Content goes until next header or end of file
        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(content)

        file_content = content[start:end]
        # Remove trailing newline that was added during export
        if file_content.endswith("\n"):
            file_content = file_content[:-1]

        files[filename] = file_content

    return files


def extract_repo_identity(path_str: str) -> tuple[str, str] | None:
    """Extract (org, name) from a repos path.

    Expected format: repos/{org}/{name}/...

    Returns:
        Tuple of (org, name) or None if path doesn't match expected format
    """
    parts = Path(path_str).parts
    if len(parts) >= 3 and parts[0] == "repos":
        return (parts[1], parts[2])
    return None


def extract_pr_identity(path_str: str) -> tuple[str, str, int] | None:
    """Extract (org, repo_name, pr_number) from a pullrequests path.

    Expected format: pullrequests/{org}/{repo_name}/{pr_number}/...

    Returns:
        Tuple of (org, repo_name, pr_number) or None if path doesn't match
    """
    parts = Path(path_str).parts
    if len(parts) >= 4 and parts[0] == "pullrequests":
        try:
            pr_number = int(parts[3])
            return (parts[1], parts[2], pr_number)
        except ValueError:
            return None
    return None


def find_collisions(
    import_files: dict[str, str],
    base_dir: Path,
) -> tuple[set[tuple[str, str]], set[tuple[str, str, int]]]:
    """Find repos and PRs that would collide with existing workspace content.

    Args:
        import_files: Dictionary of file paths to import
        base_dir: Base directory of the workspace

    Returns:
        Tuple of (colliding_repos, colliding_prs) where:
        - colliding_repos: Set of (org, name) tuples
        - colliding_prs: Set of (org, repo_name, pr_number) tuples
    """
    colliding_repos: set[tuple[str, str]] = set()
    colliding_prs: set[tuple[str, str, int]] = set()

    # Get existing repos
    repos_dir = base_dir / "repos"
    existing_repos: set[tuple[str, str]] = set()
    if repos_dir.exists():
        for org_dir in repos_dir.iterdir():
            if org_dir.is_dir():
                for repo_dir in org_dir.iterdir():
                    if repo_dir.is_dir():
                        existing_repos.add((org_dir.name, repo_dir.name))

    # Get existing PRs
    prs_dir = base_dir / "pullrequests"
    existing_prs: set[tuple[str, str, int]] = set()
    if prs_dir.exists():
        for org_dir in prs_dir.iterdir():
            if org_dir.is_dir():
                for repo_dir in org_dir.iterdir():
                    if repo_dir.is_dir():
                        for pr_dir in repo_dir.iterdir():
                            if pr_dir.is_dir():
                                try:
                                    pr_num = int(pr_dir.name)
                                    existing_prs.add((org_dir.name, repo_dir.name, pr_num))
                                except ValueError:
                                    continue

    # Check import files for collisions
    for file_path in import_files:
        repo_id = extract_repo_identity(file_path)
        if repo_id and repo_id in existing_repos:
            colliding_repos.add(repo_id)

        pr_id = extract_pr_identity(file_path)
        if pr_id and pr_id in existing_prs:
            colliding_prs.add(pr_id)

    return colliding_repos, colliding_prs


def should_skip_file(
    file_path: str,
    colliding_repos: set[tuple[str, str]],
    colliding_prs: set[tuple[str, str, int]],
) -> bool:
    """Check if a file should be skipped due to collision.

    Args:
        file_path: Path of the file to check
        colliding_repos: Set of (org, name) tuples that collide
        colliding_prs: Set of (org, repo_name, pr_number) tuples that collide

    Returns:
        True if file should be skipped, False otherwise
    """
    repo_id = extract_repo_identity(file_path)
    if repo_id and repo_id in colliding_repos:
        return True

    pr_id = extract_pr_identity(file_path)
    if pr_id and pr_id in colliding_prs:
        return True

    return False


def import_from_txtar(
    txtar_path: Path,
    base_dir: Path,
) -> tuple[int, list[str]]:
    """Import files from a txtar archive.

    Args:
        txtar_path: Path to the txtar file
        base_dir: Base directory of the workspace

    Returns:
        Tuple of (imported_count, skipped_items)
    """
    files = parse_txtar(txtar_path)

    # Find collisions
    colliding_repos, colliding_prs = find_collisions(files, base_dir)

    imported_count = 0
    skipped_items: list[str] = []

    # Track what we've already reported as skipped
    reported_repos: set[tuple[str, str]] = set()
    reported_prs: set[tuple[str, str, int]] = set()

    for file_path, content in files.items():
        # Skip configs.json - we don't overwrite the workspace config
        if file_path == "configs.json":
            continue

        if should_skip_file(file_path, colliding_repos, colliding_prs):
            # Report collision once per repo/PR
            repo_id = extract_repo_identity(file_path)
            if repo_id and repo_id in colliding_repos and repo_id not in reported_repos:
                skipped_items.append(f"repos/{repo_id[0]}/{repo_id[1]} (repo already exists)")
                reported_repos.add(repo_id)

            pr_id = extract_pr_identity(file_path)
            if pr_id and pr_id in colliding_prs and pr_id not in reported_prs:
                skipped_items.append(f"pullrequests/{pr_id[0]}/{pr_id[1]}/{pr_id[2]} (PR already exists)")
                reported_prs.add(pr_id)
            continue

        # Write the file
        dst = base_dir / file_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(content, encoding="utf-8")
        imported_count += 1

    return imported_count, skipped_items


def import_from_folder(
    folder_path: Path,
    base_dir: Path,
) -> tuple[int, list[str]]:
    """Import files from a folder.

    Args:
        folder_path: Path to the folder to import
        base_dir: Base directory of the workspace

    Returns:
        Tuple of (imported_count, skipped_items)
    """
    # Build a dict of relative paths to absolute paths
    files: dict[str, str] = {}

    # Look for repos and pullrequests folders
    for scope_folder in ["repos", "pullrequests"]:
        scope_path = folder_path / scope_folder
        if scope_path.exists():
            for file_path in scope_path.rglob("*"):
                if file_path.is_file():
                    rel_path = file_path.relative_to(folder_path)
                    files[str(rel_path)] = str(file_path)

    # Find collisions
    file_contents = {k: "" for k in files}  # We only need paths for collision check
    colliding_repos, colliding_prs = find_collisions(file_contents, base_dir)

    imported_count = 0
    skipped_items: list[str] = []

    # Track what we've already reported as skipped
    reported_repos: set[tuple[str, str]] = set()
    reported_prs: set[tuple[str, str, int]] = set()

    for rel_path, abs_path in files.items():
        if should_skip_file(rel_path, colliding_repos, colliding_prs):
            # Report collision once per repo/PR
            repo_id = extract_repo_identity(rel_path)
            if repo_id and repo_id in colliding_repos and repo_id not in reported_repos:
                skipped_items.append(f"repos/{repo_id[0]}/{repo_id[1]} (repo already exists)")
                reported_repos.add(repo_id)

            pr_id = extract_pr_identity(rel_path)
            if pr_id and pr_id in colliding_prs and pr_id not in reported_prs:
                skipped_items.append(f"pullrequests/{pr_id[0]}/{pr_id[1]}/{pr_id[2]} (PR already exists)")
                reported_prs.add(pr_id)
            continue

        # Copy the file
        dst = base_dir / rel_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(abs_path, dst)
        imported_count += 1

    return imported_count, skipped_items


def validate_folder_structure(folder_path: Path) -> bool:
    """Validate that a folder has the expected repos/pullrequests structure.

    Args:
        folder_path: Path to validate

    Returns:
        True if folder has valid structure, False otherwise
    """
    repos_dir = folder_path / "repos"
    prs_dir = folder_path / "pullrequests"

    return repos_dir.exists() or prs_dir.exists()


@click.command("import")
@click.argument("input_path", type=click.Path(exists=True))
def import_cmd(input_path: str) -> None:
    """Import workspace files from a txtar file or folder.

    INPUT_PATH must be either:

    - A .txtar file created by 'crev export'

    - A folder containing 'repos' and/or 'pullrequests' subdirectories

    Files are merged into the current workspace. Collisions are skipped:

    - A repo collision occurs when org and name match an existing repo

    - A PR collision occurs when org, repo name, and PR number match
    """
    base_dir = Path.cwd()
    input_path_obj = Path(input_path)

    # Check for configs.json
    configs_file = base_dir / "configs.json"
    if not configs_file.exists():
        click.echo("Error: configs.json not found. Run 'crev init' first.", err=True)
        raise SystemExit(1)

    # Determine if input is a txtar file or folder
    if input_path_obj.is_file():
        if not input_path_obj.suffix == ".txtar":
            click.echo("Error: File must be a .txtar file", err=True)
            raise SystemExit(1)

        click.echo(f"Importing from txtar: {input_path_obj}")
        imported_count, skipped_items = import_from_txtar(input_path_obj, base_dir)

    elif input_path_obj.is_dir():
        if not validate_folder_structure(input_path_obj):
            click.echo(
                "Error: Folder must contain 'repos' and/or 'pullrequests' subdirectories",
                err=True,
            )
            raise SystemExit(1)

        click.echo(f"Importing from folder: {input_path_obj}")
        imported_count, skipped_items = import_from_folder(input_path_obj, base_dir)

    else:
        click.echo(f"Error: Invalid input path: {input_path}", err=True)
        raise SystemExit(1)

    # Report results
    click.echo(f"Imported {imported_count} file(s)")

    if skipped_items:
        click.echo("\nSkipped due to collisions:")
        for item in skipped_items:
            click.echo(f"  - {item}")
