"""Init command for crev CLI."""

import shutil
from pathlib import Path

import click


@click.command()
@click.argument("path", type=click.Path())
def init(path: str) -> None:
    """Initialize a new crev project.

    Creates a folder at PATH with a configs.json configuration file and a sample .env file.
    """
    project_path = Path(path)

    # Create the directory
    try:
        project_path.mkdir(parents=True, exist_ok=False)
        click.echo(f"Created directory: {project_path.absolute()}")
    except FileExistsError:
        click.echo(f"Error: Directory '{path}' already exists", err=True)
        raise click.Abort()

    # Copy template folder contents to project directory
    template_dir = Path(__file__).parent / "template"

    # Copy all files and directories from template
    for item in template_dir.rglob("*"):
        if item.is_file():
            # Calculate relative path from template_dir
            relative_path = item.relative_to(template_dir)
            dest_path = project_path / relative_path

            # Create parent directories if needed
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy the file
            shutil.copy2(item, dest_path)

    click.echo(f"Created prompts directory: {project_path / 'prompts'}")

    # Read success message from file
    msg_file = Path(__file__).parent / "assets" / "init_success.txt"
    with msg_file.open("r") as f:
        message = f.read().format(
            project_path=project_path.absolute(),
            configs_file=project_path / "configs.json"
        )
    click.echo(message)
