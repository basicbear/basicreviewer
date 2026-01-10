"""Init command for crev CLI."""

import json
from pathlib import Path

import click


@click.command()
@click.argument("path", type=click.Path())
def init(path: str) -> None:
    """Initialize a new crev project.

    Creates a folder at PATH with a repos.json configuration file.
    """
    project_path = Path(path)

    # Create the directory
    try:
        project_path.mkdir(parents=True, exist_ok=False)
        click.echo(f"Created directory: {project_path.absolute()}")
    except FileExistsError:
        click.echo(f"Error: Directory '{path}' already exists", err=True)
        raise click.Abort()

    # Load repos template from assets
    template_file = Path(__file__).parent / "assets" / "repos_template.json"
    with template_file.open("r") as f:
        repos_config = json.load(f)

    # Write repos.json to project directory
    repos_file = project_path / "repos.json"
    with repos_file.open("w") as f:
        json.dump(repos_config, f, indent=2)

    # Read success message from file
    msg_file = Path(__file__).parent / "assets" / "init_success.txt"
    with msg_file.open("r") as f:
        message = f.read().format(
            project_path=project_path.absolute(), repos_file=repos_file
        )
    click.echo(message)
